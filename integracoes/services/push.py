"""Serviço de PUSH do Django para a planilha nova Google Sheets (Bloco 3).

REGRAS:
- Escrita exclusivamente em NEW_SPREADSHEET_ID (nunca LEGACY).
- Guard SHEETS_SYNC_ENABLED no serviço.
- Backup automático do banco de dados (se not dry_run) antes de iniciar.
- select_for_update na abertura do transaction.atomic().
- Marco temporal capturado ANTES de qualquer leitura de objetos.
- state.last_push_at = marco (não now()!) para cobrir alterações concorrentes.
- Apenas objetos com data_atualizacao > marco são selecionados.
- Se objeto tem snapshot: acumula update e escreve via batch_update a cada 100 itens.
- Se objeto não tem snapshot: append_row e update_or_create no snapshot.
- Se _extract_row_from_updated_range falhar no append: fallback len(read_all) + 1 com warning.
- Range explícito: A{row}:{last_col}{row}.
- Atualiza content_hash no snapshot após escrita.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from integracoes.backup import create_db_backup, serialize_instance
from integracoes.exceptions import SheetsSyncDisabledError
from integracoes.google_client import append_row, batch_update, read_all
from integracoes.mapping import NEW_SHEET_MAP, SYNC_ORDER, get_model_class
from integracoes.models import (
    SheetRowSnapshot,
    SheetSyncState,
    SyncOperation,
    SyncOperationRecord,
)
from integracoes.services.sync_full import (
    _extract_row_from_updated_range,
    _finalize_operation,
    build_row_from_instance,
    compute_content_hash,
)

logger = logging.getLogger(__name__)

PUSH_BATCH_SIZE = 100


def _assert_sheets_sync_enabled() -> None:
    if not getattr(settings, "SHEETS_SYNC_ENABLED", False):
        raise SheetsSyncDisabledError(
            "SHEETS_SYNC_ENABLED está desabilitado em settings. "
            "Ligue a flag antes de executar push."
        )


def _index_to_col_letter(idx: int) -> str:
    """Converte índice 0-based para letra de coluna ('0' -> 'A', '25' -> 'Z', '26' -> 'AA')."""
    result = []
    while idx >= 0:
        result.append(chr(idx % 26 + ord("A")))
        idx = idx // 26 - 1
    return "".join(reversed(result))


def _sheet_range(sheet_name: str, a1: str) -> str:
    """Monta range A1 com nome de aba escapado."""
    if "'" in sheet_name:
        return f"{sheet_name}!{a1}"
    return f"'{sheet_name}'!{a1}"


def push_to_sheets(
    model_name: str | None = None,
    dry_run: bool = False,
    since: Any = None,
) -> dict[str, Any]:
    """Envia alterações do Django para a planilha nova do Google Sheets.

    1. Guard SHEETS_SYNC_ENABLED.
    2. Cria SyncOperation(operation_type="PUSH") + backup (se not dry_run).
    3. Abre transaction.atomic() com select_for_update na abertura.
    4. Captura marco = since or state.last_push_at or (now() - 1h) ANTES da leitura.
    5. Itera modelos filtrando data_atualizacao > marco.
    6. Atualiza existentes via batch_update ou faz append de novos registros.
    7. Atualiza state.last_push_at = marco e status padronizado.
    """
    _assert_sheets_sync_enabled()

    backup_path = None
    if not dry_run:
        try:
            backup_path = create_db_backup(tag="push")
        except Exception as exc:
            logger.error("Falha ao criar backup antes do push: %s", exc)

    op = SyncOperation.objects.create(
        operation_type="PUSH",
        status="IN_PROGRESS",
        backup_file_path=backup_path,
        metadata={"dry_run": dry_run, "model_name": model_name, "since": str(since) if since else None},
    )

    summary: dict[str, Any] = {
        "operation_id": op.pk,
        "dry_run": dry_run,
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
        # 2. select_for_update NA ABERTURA
        state, _ = SheetSyncState.objects.select_for_update().get_or_create(key="global")

        # 3. Capturar marco ANTES de qualquer leitura
        if since is not None:
            if isinstance(since, str):
                parsed = parse_datetime(since)
                marco = parsed if parsed else (timezone.now() - timedelta(hours=1))
            else:
                marco = since
        elif state.last_push_at is not None:
            marco = state.last_push_at
        else:
            marco = timezone.now() - timedelta(hours=1)

        if timezone.is_naive(marco):
            marco = timezone.make_aware(marco, timezone.get_current_timezone())

        summary["marco"] = marco.isoformat()

        for m_name in models_to_process:
            if m_name not in NEW_SHEET_MAP:
                logger.warning("Modelo '%s' não encontrado em NEW_SHEET_MAP. Ignorando.", m_name)
                continue

            conf = NEW_SHEET_MAP[m_name]
            sheet_name: str = conf["sheet"]
            columns: list[str] = conf["columns"]
            read_only_columns: set[str] = set(conf.get("read_only_columns", []))
            last_col: str = _index_to_col_letter(len(columns) - 1)
            ModelClass = get_model_class(m_name)

            model_stats = {
                "total": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0,
            }
            summary["per_model"][m_name] = model_stats

            # 4. Lê apenas objetos modificados após o marco temporal
            try:
                qs = ModelClass.objects.filter(data_atualizacao__gt=marco).order_by("pk")
                objects = list(qs)
            except Exception as exc:
                logger.error("Erro ao consultar %s com data_atualizacao > %s: %s", m_name, marco, exc, exc_info=True)
                model_stats["errors"] += 1
                summary["errors"] += 1
                if not dry_run:
                    SyncOperationRecord.objects.create(
                        operation=op,
                        model_name=m_name,
                        lookup_key="query",
                        lookup_value=str(marco),
                        action="ERROR",
                        status="ERROR",
                        sheet_name=sheet_name,
                        error_detail=str(exc),
                    )
                continue

            model_stats["total"] = len(objects)
            summary["total"] += len(objects)

            batch_updates_queue: list[dict[str, Any]] = []

            def _flush_updates() -> None:
                nonlocal batch_updates_queue
                if not batch_updates_queue:
                    return

                batch_payload = [
                    {"range": item["range"], "values": item["values"]}
                    for item in batch_updates_queue
                ]

                try:
                    if not dry_run:
                        batch_update("new", batch_payload)

                    for item in batch_updates_queue:
                        if not dry_run:
                            snapshot = item["snapshot"]
                            snapshot.content_hash = item["content_hash"]
                            snapshot.save(update_fields=["content_hash"])

                            SyncOperationRecord.objects.create(
                                operation=op,
                                model_name=m_name,
                                lookup_key="id",
                                lookup_value=str(item["obj"].pk),
                                action="UPDATE",
                                status="SUCCESS",
                                sheet_name=sheet_name,
                                row_number=snapshot.row_number,
                                after_snapshot=serialize_instance(item["obj"]),
                            )

                        model_stats["updated"] += 1
                        summary["updated"] += 1

                except Exception as exc:
                    logger.error("Erro ao aplicar batch_update em %s: %s", m_name, exc, exc_info=True)
                    for item in batch_updates_queue:
                        model_stats["errors"] += 1
                        summary["errors"] += 1
                        if not dry_run:
                            SyncOperationRecord.objects.create(
                                operation=op,
                                model_name=m_name,
                                lookup_key="id",
                                lookup_value=str(item["obj"].pk),
                                action="ERROR",
                                status="ERROR",
                                sheet_name=sheet_name,
                                row_number=item["snapshot"].row_number,
                                error_detail=str(exc),
                            )

                batch_updates_queue = []

            for obj in objects:
                try:
                    row_values, row_dict = build_row_from_instance(m_name, obj)
                    row_without_readonly = {k: v for k, v in row_dict.items() if k not in read_only_columns}
                    content_hash = compute_content_hash(row_without_readonly)

                    snapshot = SheetRowSnapshot.objects.filter(
                        model_name=m_name, lookup_value=str(obj.pk)
                    ).first()

                    if snapshot is not None:
                        # Objeto já existe na planilha → range explícito A{row}:{last_col}{row}
                        explicit_range = _sheet_range(
                            sheet_name, f"A{snapshot.row_number}:{last_col}{snapshot.row_number}"
                        )
                        batch_updates_queue.append({
                            "range": explicit_range,
                            "values": [row_values],
                            "snapshot": snapshot,
                            "content_hash": content_hash,
                            "obj": obj,
                        })

                        if len(batch_updates_queue) >= PUSH_BATCH_SIZE:
                            _flush_updates()

                    else:
                        # Objeto novo no Django sem snapshot → append_row
                        row_number = None
                        if not dry_run:
                            response = append_row(
                                "new",
                                _sheet_range(sheet_name, "A:ZZ"),
                                [row_values],
                            )
                            updates = (response or {}).get("updates") or {}
                            parsed = _extract_row_from_updated_range(updates.get("updatedRange"))
                            if parsed is not None:
                                row_number = parsed
                            else:
                                logger.warning(
                                    "Não foi possível extrair número de linha de updatedRange (%s) para %s pk=%s. "
                                    "Recuperando via read_all.",
                                    updates.get("updatedRange"),
                                    m_name,
                                    obj.pk,
                                )
                                existing_rows = read_all("new", sheet_name)
                                row_number = len(existing_rows) + 1

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
                    logger.error("Erro ao preparar push de %s pk=%s: %s", m_name, obj.pk, exc, exc_info=True)
                    model_stats["errors"] += 1
                    summary["errors"] += 1
                    if not dry_run:
                        SyncOperationRecord.objects.create(
                            operation=op,
                            model_name=m_name,
                            lookup_key="id",
                            lookup_value=str(obj.pk),
                            action="ERROR",
                            status="ERROR",
                            sheet_name=sheet_name,
                            error_detail=str(exc),
                        )

            # Flush de updates remanescentes
            _flush_updates()

        # 5. state.last_push_at = marco (não now()!) capturado ANTES
        _finalize_operation(op, summary)
        if not dry_run:
            state.last_push_at = marco
            state.last_push_status = op.status
            state.save(update_fields=["last_push_at", "last_push_status"])

    return summary
