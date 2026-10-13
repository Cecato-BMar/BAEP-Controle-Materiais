"""Serviço de PULL da planilha nova para o Django (Bloco 3).

REGRAS:
- Leitura exclusivamente em NEW_SPREADSHEET_ID via read_all.
- Guard SHEETS_SYNC_ENABLED no serviço.
- Anti-loop com set_syncing(True) durante escrita no Django.
- select_for_update na abertura do transaction.atomic().
- Backup automático do banco de dados (se not dry_run) antes de iniciar.
- Last Write Wins: compara obj.data_atualizacao vs atualizado_em da planilha.
- read_only_columns filtradas antes do cálculo do content_hash e não sobrescritas no Django.
- row_id vazio: cria novo registro no Django e escreve o ID gerado imediatamente na célula A{row_number}.
- Nunca fabrica dados em _cast_field_value: campos obrigatórios vazios disparam ValueError e viram ERROR.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from integracoes.backup import create_db_backup, serialize_instance
from integracoes.exceptions import SheetsSyncDisabledError
from integracoes.google_client import read_all, update_row
from integracoes.mapping import NEW_SHEET_MAP, SYNC_ORDER, get_model_class
from integracoes.models import (
    SheetRowSnapshot,
    SheetSyncState,
    SyncOperation,
    SyncOperationRecord,
)
from integracoes.services.sync_full import compute_content_hash
from materiais.sync_to_belico import set_syncing

logger = logging.getLogger(__name__)


def _assert_sheets_sync_enabled() -> None:
    if not getattr(settings, "SHEETS_SYNC_ENABLED", False):
        raise SheetsSyncDisabledError(
            "SHEETS_SYNC_ENABLED está desabilitado em settings. "
            "Ligue a flag antes de executar pull."
        )


def _cast_field_value(field: Any, raw_val: Any) -> Any:
    """Converte valor string/célula para o tipo esperado pelo campo do model Django.

    Nunca fabrica dados. Se o campo for obrigatório e o valor for vazio ou inválido,
    levanta ValueError para que a linha seja registrada como status='ERROR'.
    """
    is_empty = raw_val is None or (isinstance(raw_val, str) and not raw_val.strip())

    if is_empty:
        if getattr(field, "null", False):
            return None
        if isinstance(field, (models.CharField, models.TextField)) and getattr(field, "blank", False):
            return ""
        raise ValueError(f"Campo '{field.name}' é obrigatório mas veio vazio na planilha.")

    val_str = str(raw_val).strip()

    if isinstance(field, (models.IntegerField, models.SmallIntegerField)):
        try:
            return int(float(val_str))
        except (ValueError, TypeError):
            if getattr(field, "null", False):
                return None
            raise ValueError(f"Campo '{field.name}' esperava número inteiro, recebeu '{val_str}'.")

    if isinstance(field, (models.FloatField, models.DecimalField)):
        try:
            return Decimal(val_str) if isinstance(field, models.DecimalField) else float(val_str)
        except Exception:
            if getattr(field, "null", False):
                return None
            raise ValueError(f"Campo '{field.name}' esperava número decimal, recebeu '{val_str}'.")

    if isinstance(field, models.DateField):
        dt = parse_date(val_str[:10])
        if dt:
            return dt
        parts = val_str.split("/")
        if len(parts) == 3:
            try:
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
            except Exception:
                pass
        if getattr(field, "null", False):
            return None
        raise ValueError(f"Campo '{field.name}' esperava data válida, recebeu '{val_str}'.")

    if isinstance(field, models.BooleanField):
        return val_str.lower() in ("true", "1", "sim", "yes", "s")

    return val_str


def _finalize_operation(op: SyncOperation, summary: dict[str, Any]) -> dict[str, Any]:
    op.finished_at = timezone.now()
    op.total_records = summary.get("total", 0)
    op.created_count = summary.get("created", 0)
    op.updated_count = summary.get("updated", 0)
    op.error_count = summary.get("errors", 0)
    op.skipped_count = summary.get("skipped", 0)
    if op.error_count == 0:
        op.status = "SUCCESS"
    elif op.created_count > 0 or op.updated_count > 0 or op.skipped_count > 0:
        op.status = "PARTIAL_SUCCESS"
    else:
        op.status = "FAILED"
    op.metadata = summary
    op.save()
    summary["status"] = op.status
    summary["operation_id"] = op.pk
    return summary


def pull_from_sheets(
    model_name: str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Sincroniza alterações da planilha nova (Google Sheets) para o Django.

    1. Verifica guard SHEETS_SYNC_ENABLED.
    2. Cria SyncOperation(operation_type="PULL").
    3. Gera backup físico do banco de dados (se not dry_run).
    4. Abre transaction.atomic() com select_for_update em SheetSyncState.
    5. Ativa set_syncing(True) para evitar reverberação de signals.
    6. Processa cada modelo em SYNC_ORDER (ou model_name específico).
    7. Atualiza SheetSyncState e finaliza SyncOperation com status padronizado.
    """
    _assert_sheets_sync_enabled()

    backup_path = None
    if not dry_run:
        try:
            backup_path = create_db_backup(tag="pull")
        except Exception as exc:
            logger.error("Falha ao criar backup antes do pull: %s", exc)

    op = SyncOperation.objects.create(
        operation_type="PULL",
        status="IN_PROGRESS",
        backup_file_path=backup_path,
        metadata={"dry_run": dry_run, "force": force, "model_name": model_name},
    )

    summary: dict[str, Any] = {
        "operation_id": op.pk,
        "dry_run": dry_run,
        "force": force,
        "model_name": model_name,
        "total": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "per_model": {},
    }

    models_to_process = [model_name] if model_name else SYNC_ORDER

    with transaction.atomic():
        # 3. select_for_update na ABERTURA (não no final)
        state, _ = SheetSyncState.objects.select_for_update().get_or_create(key="global")

        set_syncing(True)
        try:
            for m_name in models_to_process:
                if m_name not in NEW_SHEET_MAP:
                    logger.warning("Modelo '%s' não encontrado em NEW_SHEET_MAP. Ignorando.", m_name)
                    continue

                conf = NEW_SHEET_MAP[m_name]
                sheet_name: str = conf["sheet"]
                read_only_columns: set[str] = set(conf.get("read_only_columns", []))
                aliases: dict[str, str] = conf.get("column_aliases", {})
                ModelClass = get_model_class(m_name)

                model_stats = {
                    "total": 0,
                    "created": 0,
                    "updated": 0,
                    "skipped": 0,
                    "errors": 0,
                }
                summary["per_model"][m_name] = model_stats

                # Savepoint por model
                with transaction.atomic():
                    try:
                        raw_rows = read_all("new", sheet_name)
                    except Exception as exc:
                        logger.error("Erro ao ler aba '%s' do Sheets: %s", sheet_name, exc, exc_info=True)
                        model_stats["errors"] += 1
                        summary["errors"] += 1
                        if not dry_run:
                            SyncOperationRecord.objects.create(
                                operation=op,
                                model_name=m_name,
                                lookup_key="sheet",
                                lookup_value=sheet_name,
                                action="ERROR",
                                status="ERROR",
                                sheet_name=sheet_name,
                                error_detail=str(exc),
                            )
                        continue

                    if not raw_rows or len(raw_rows) < 2:
                        logger.info("Aba '%s' está vazia ou contém apenas cabeçalho.", sheet_name)
                        continue

                    header = [str(col).strip() for col in raw_rows[0]]

                    # Linhas de dados a partir da linha 2 (índice 1)
                    for row_idx, row_data in enumerate(raw_rows[1:], start=2):
                        row_number = row_idx
                        model_stats["total"] += 1
                        summary["total"] += 1

                        row_dict: dict[str, Any] = {}
                        for col_idx, col_name in enumerate(header):
                            val = row_data[col_idx] if col_idx < len(row_data) else ""
                            row_dict[col_name] = str(val).strip() if isinstance(val, str) else val

                        row_id_raw = row_dict.get("id", "")
                        row_id = str(row_id_raw).strip() if row_id_raw is not None else ""

                        # read_only_columns filtradas antes de calcular content_hash
                        row_without_readonly = {
                            k: v for k, v in row_dict.items() if k not in read_only_columns
                        }
                        content_hash = compute_content_hash(row_without_readonly)

                        # Savepoint por linha para isolar falhas individuais
                        with transaction.atomic():
                            try:
                                if not row_id:
                                    # Linha sem ID: cria novo objeto no Django
                                    obj = ModelClass()
                                    for col_name, val in row_dict.items():
                                        if col_name in read_only_columns or col_name == "id":
                                            continue
                                        model_field = aliases.get(col_name, col_name)
                                        if hasattr(obj, model_field):
                                            field = ModelClass._meta.get_field(model_field)
                                            setattr(obj, model_field, _cast_field_value(field, val))

                                    if not dry_run:
                                        obj.save()
                                        # Escreve o ID recém-gerado de volta na planilha para evitar duplicação futura
                                        update_row("new", f"'{sheet_name}'!A{row_number}", [[str(obj.pk)]])
                                        row_dict["id"] = str(obj.pk)
                                        row_without_readonly = {
                                            k: v for k, v in row_dict.items() if k not in read_only_columns
                                        }
                                        content_hash = compute_content_hash(row_without_readonly)
                                        SheetRowSnapshot.objects.update_or_create(
                                            model_name=m_name,
                                            lookup_value=str(obj.pk),
                                            defaults={
                                                "lookup_key": "id",
                                                "row_number": row_number,
                                                "content_hash": content_hash,
                                            },
                                        )
                                        SyncOperationRecord.objects.create(
                                            operation=op,
                                            model_name=m_name,
                                            lookup_key="id",
                                            lookup_value=str(obj.pk),
                                            action="CREATE",
                                            status="SUCCESS",
                                            sheet_name=sheet_name,
                                            row_number=row_number,
                                            after_snapshot=serialize_instance(obj),
                                        )

                                    model_stats["created"] += 1
                                    summary["created"] += 1

                                else:
                                    # Linha com ID: busca por pk
                                    try:
                                        obj = ModelClass.objects.get(pk=row_id)
                                    except ModelClass.DoesNotExist:
                                        obj = None

                                    snapshot = SheetRowSnapshot.objects.filter(
                                        model_name=m_name, lookup_value=row_id
                                    ).first()

                                    # Se snapshot.content_hash == content_hash e not force → skip
                                    if snapshot and snapshot.content_hash == content_hash and not force:
                                        model_stats["skipped"] += 1
                                        summary["skipped"] += 1
                                        continue

                                    # Se objeto existe, aplicar Last Write Wins (LWW)
                                    if obj is not None:
                                        django_dt = getattr(obj, "data_atualizacao", None)
                                        sheet_updated_str = str(row_dict.get("atualizado_em", "")).strip()
                                        sheet_dt = parse_datetime(sheet_updated_str) if sheet_updated_str else None

                                        if sheet_dt is None:
                                            # Planilha não tem atualizado_em → Django vence (não sobrescrever)
                                            logger.warning(
                                                "Conflito LWW em %s pk=%s: planilha sem 'atualizado_em'. Django vence.",
                                                m_name,
                                                obj.pk,
                                            )
                                            model_stats["skipped"] += 1
                                            summary["skipped"] += 1
                                            continue

                                        if django_dt is not None:
                                            if timezone.is_naive(django_dt):
                                                django_dt = timezone.make_aware(
                                                    django_dt, timezone.get_current_timezone()
                                                )
                                            if timezone.is_naive(sheet_dt):
                                                sheet_dt = timezone.make_aware(
                                                    sheet_dt, timezone.get_current_timezone()
                                                )

                                            if django_dt > sheet_dt:
                                                # Django é mais recente → logar warning, não sobrescrever
                                                logger.warning(
                                                    "Conflito LWW em %s pk=%s: Django (%s) é mais recente que a planilha (%s). Ignorando.",
                                                    m_name,
                                                    obj.pk,
                                                    django_dt.isoformat(),
                                                    sheet_dt.isoformat(),
                                                )
                                                model_stats["skipped"] += 1
                                                summary["skipped"] += 1
                                                continue

                                        # Planilha é mais recente (ou force=True): aplica alterações
                                        before_snapshot = serialize_instance(obj)
                                        for col_name, val in row_dict.items():
                                            if col_name in read_only_columns or col_name == "id":
                                                continue
                                            model_field = aliases.get(col_name, col_name)
                                            if hasattr(obj, model_field):
                                                field = ModelClass._meta.get_field(model_field)
                                                setattr(obj, model_field, _cast_field_value(field, val))

                                        if not dry_run:
                                            obj.save()
                                            SheetRowSnapshot.objects.update_or_create(
                                                model_name=m_name,
                                                lookup_value=str(obj.pk),
                                                defaults={
                                                    "lookup_key": "id",
                                                    "row_number": row_number,
                                                    "content_hash": content_hash,
                                                },
                                            )
                                            SyncOperationRecord.objects.create(
                                                operation=op,
                                                model_name=m_name,
                                                lookup_key="id",
                                                lookup_value=str(obj.pk),
                                                action="UPDATE",
                                                status="SUCCESS",
                                                sheet_name=sheet_name,
                                                row_number=row_number,
                                                before_snapshot=before_snapshot,
                                                after_snapshot=serialize_instance(obj),
                                            )

                                        model_stats["updated"] += 1
                                        summary["updated"] += 1

                                    else:
                                        # Objeto com ID fornecido que não existia no Django: cria
                                        obj = ModelClass(pk=row_id)
                                        for col_name, val in row_dict.items():
                                            if col_name in read_only_columns or col_name == "id":
                                                continue
                                            model_field = aliases.get(col_name, col_name)
                                            if hasattr(obj, model_field):
                                                field = ModelClass._meta.get_field(model_field)
                                                setattr(obj, model_field, _cast_field_value(field, val))

                                        if not dry_run:
                                            obj.save()
                                            SheetRowSnapshot.objects.update_or_create(
                                                model_name=m_name,
                                                lookup_value=str(obj.pk),
                                                defaults={
                                                    "lookup_key": "id",
                                                    "row_number": row_number,
                                                    "content_hash": content_hash,
                                                },
                                            )
                                            SyncOperationRecord.objects.create(
                                                operation=op,
                                                model_name=m_name,
                                                lookup_key="id",
                                                lookup_value=str(obj.pk),
                                                action="CREATE",
                                                status="SUCCESS",
                                                sheet_name=sheet_name,
                                                row_number=row_number,
                                                after_snapshot=serialize_instance(obj),
                                            )

                                        model_stats["created"] += 1
                                        summary["created"] += 1

                            except Exception as exc:
                                logger.error(
                                    "Erro no pull de %s linha %s (id=%s): %s",
                                    m_name,
                                    row_number,
                                    row_id,
                                    exc,
                                    exc_info=True,
                                )
                                model_stats["errors"] += 1
                                summary["errors"] += 1
                                if not dry_run:
                                    SyncOperationRecord.objects.create(
                                        operation=op,
                                        model_name=m_name,
                                        lookup_key="id",
                                        lookup_value=row_id or f"row_{row_number}",
                                        action="ERROR",
                                        status="ERROR",
                                        sheet_name=sheet_name,
                                        row_number=row_number,
                                        error_detail=str(exc),
                                    )

        finally:
            set_syncing(False)

        # 5. Ao final: state.last_pull_at = now(), status padronizado
        _finalize_operation(op, summary)
        if not dry_run:
            state.last_pull_at = timezone.now()
            state.last_pull_status = op.status
            state.save(update_fields=["last_pull_at", "last_pull_status"])

    return summary
