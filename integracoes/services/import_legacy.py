"""Serviço de importação dos dados da planilha antiga (LEGACY) para o Django.

REGRAS RÍGIDAS:
- Acesso estritamente READ-ONLY à planilha legada.
- Guards de confirmação (--confirm) e feature flag (IMPORT_ENABLED).
- Proteção anti-loop de signals via is_syncing/set_syncing.
- Transação atômica por modelo.
- Nenhuma injeção de valores artificiais; falhas de validação viram status='ERROR'.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from integracoes.backup import create_db_backup, serialize_instance
from integracoes.exceptions import ImportDisabledError
from integracoes.google_client import read_sheet_as_dicts
from integracoes.mapping import LEGACY_PARSERS, SYNC_ORDER, get_model_class
from integracoes.models import SyncOperation, SyncOperationRecord
from materiais.sync_to_belico import set_syncing

logger = logging.getLogger(__name__)


def _parse_date(val: Any) -> Any:
    """Converte strings de datas variadas (DD/MM/YYYY ou YYYY-MM-DD) para date."""
    if not val or not str(val).strip():
        return None
    val_str = str(val).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            pass
    return None


def _parse_int(val: Any) -> int | None:
    """Converte valores numéricos para int, ignorando formatações."""
    if val is None or str(val).strip() == "":
        return None
    try:
        # Trata números decimais ou com ponto/vírgula
        clean = str(val).strip().split(".")[0].split(",")[0]
        return int(clean)
    except (ValueError, TypeError):
        return None


def _clean_row_data(model_name: str, row: dict[str, Any]) -> dict[str, Any]:
    """Sanitiza e tipa os campos brutos da linha de acordo com o modelo Django."""
    data = dict(row)

    if model_name == "PistolaGlock":
        # Normalização de escolhas
        sit = str(data.get("situacao_reserva", "")).strip().upper()
        if sit in ("OK", "DISPONIVEL", "DISPONÍVEL"):
            data["situacao_reserva"] = "ok"
        elif sit in ("EM USO", "EM_USO", "USO"):
            data["situacao_reserva"] = "EM_USO"
        elif sit in ("APREENDIDA", "APREENDIDO"):
            data["situacao_reserva"] = "APREENDIDA"
        elif sit in ("NOVIDADE", "NOVO"):
            data["situacao_reserva"] = "NOVIDADE"

    elif model_name == "PistolaTaurus":
        mod = str(data.get("modelo", "")).strip().upper()
        if "24/7" in mod:
            data["modelo"] = "TAURUS_24_7"
        elif "100" in mod or "PT100" in mod:
            data["modelo"] = "TAURUS_PT100"
        elif "640" in mod:
            data["modelo"] = "TAURUS_640"

    elif model_name == "EspingardaCal12":
        st = str(data.get("status", "")).strip().upper()
        if st in ("OK", "DISPONIVEL", "DISPONÍVEL"):
            data["status"] = "OK"
        elif st in ("EM USO", "EM_USO"):
            data["status"] = "EM_USO"
        elif st in ("BAIXADO", "BAIXADA", "BXA"):
            data["status"] = "BAIXADO"
        elif st in ("MANUTENÇÃO", "MANUTENCAO", "MANUT"):
            data["status"] = "MANUTENCAO"

    elif model_name == "EscudoBalistico":
        data["numero"] = _parse_int(data.get("numero"))
        data["fabricacao"] = _parse_date(data.get("fabricacao"))
        data["validade"] = _parse_date(data.get("validade"))
        # Normaliza lote_companhia para as choices do model (1cia / 2cia / EM).
        # pop remove o valor bruto; se não casar, o campo não é setado (não inventa).
        lote_raw = str(data.pop("lote_companhia", "") or "").strip().lower()
        if "1" in lote_raw:
            data["lote_companhia"] = "1cia"
        elif "2" in lote_raw:
            data["lote_companhia"] = "2cia"
        elif "em" in lote_raw:
            data["lote_companhia"] = "EM"

    elif model_name == "TASER":
        data["carga_bateria_percent"] = _parse_int(data.get("carga_bateria_percent"))

    elif model_name == "RadioHT":
        data["data_chamado_dtic"] = _parse_date(data.get("data_chamado_dtic"))

    return data


def import_legacy_sheet(
    dry_run: bool = False,
    confirm: bool = False,
) -> dict[str, Any]:
    """Executa a importação das 6 abas da planilha legada para o Django.

    Args:
        dry_run: Se True, simula a leitura e validação sem persistir no banco.
        confirm: Obrigatório quando dry_run=False.

    Returns:
        Dicionário com o resumo da operação.
    """
    if not dry_run:
        if not confirm:
            raise ValueError("Operação destrutiva de importação exige confirmação explícita (--confirm).")
        if not getattr(settings, "IMPORT_ENABLED", True):
            raise ImportDisabledError("IMPORT_ENABLED está desabilitado em settings.")

    # 1. Criação do registro mestre SyncOperation
    backup_file: str | None = None
    if not dry_run:
        try:
            backup_file = create_db_backup(tag="import_legacy")
        except Exception as exc:
            logger.warning("Falha ao criar backup físico do banco antes da importação: %s", exc)

    op = SyncOperation.objects.create(
        operation_type="IMPORT_LEGACY",
        status="IN_PROGRESS",
        backup_file_path=backup_file,
        metadata={"dry_run": dry_run},
    )

    summary = {
        "operation_id": op.pk,
        "dry_run": dry_run,
        "total_read": 0,
        "created": 0,
        "updated": 0,
        "errors": 0,
        "skipped": 0,
        "details_by_model": {},
    }

    # 2. Ativa proteção contra loops de sincronização com materiais
    set_syncing(True)
    try:
        for model_name in SYNC_ORDER:
            if model_name not in LEGACY_PARSERS:
                continue

            parser_conf = LEGACY_PARSERS[model_name]
            sheet_title = parser_conf["sheet"]
            lookup_key = parser_conf["lookup_key"]
            ModelClass = get_model_class(model_name)

            model_stats = {"read": 0, "created": 0, "updated": 0, "errors": 0, "skipped": 0}
            summary["details_by_model"][model_name] = model_stats

            try:
                rows = read_sheet_as_dicts(
                    spreadsheet_id_or_target="legacy",
                    sheet_name=sheet_title,
                    data_start_row=parser_conf["data_start_row"],
                    columns=parser_conf["columns"],
                    stop_on_blank_lookup=parser_conf.get("stop_on_blank_lookup", True),
                    lookup_key=lookup_key,
                    filter_rows=parser_conf.get("filter_rows"),
                )
            except Exception as exc:
                logger.error("Erro ao ler aba legada '%s': %s", sheet_title, exc)
                SyncOperationRecord.objects.create(
                    operation=op,
                    model_name=model_name,
                    lookup_key="aba",
                    lookup_value=sheet_title,
                    action="ERROR",
                    status="ERROR",
                    sheet_name=sheet_title,
                    error_detail=f"Falha de leitura da aba: {exc}",
                )
                op.error_count += 1
                model_stats["errors"] += 1
                continue

            model_stats["read"] = len(rows)
            summary["total_read"] += len(rows)

            # 3. Processamento com savepoint atômico por linha
            for raw_row in rows:
                row_number = raw_row.pop("_row_number", None)
                raw_lookup_val = raw_row.get(lookup_key)

                if raw_lookup_val is None or str(raw_lookup_val).strip() == "":
                    model_stats["skipped"] += 1
                    summary["skipped"] += 1
                    continue

                lookup_val = str(raw_lookup_val).strip()
                before_snapshot = None

                try:
                    with transaction.atomic():
                        clean_data = _clean_row_data(model_name, raw_row)
                        clean_lookup_val = clean_data.get(lookup_key, lookup_val)

                        existing_instance = (
                            ModelClass.objects.filter(**{lookup_key: clean_lookup_val}).first()
                        )
                        before_snapshot = (
                            serialize_instance(existing_instance) if existing_instance else None
                        )

                        if dry_run:
                            if existing_instance:
                                model_stats["updated"] += 1
                                summary["updated"] += 1
                            else:
                                model_stats["created"] += 1
                                summary["created"] += 1
                            continue

                        # Persistência real
                        if existing_instance:
                            action = "UPDATE"
                            for fld, val in clean_data.items():
                                if hasattr(existing_instance, fld):
                                    setattr(existing_instance, fld, val)
                            existing_instance.save()
                            instance = existing_instance
                            model_stats["updated"] += 1
                            summary["updated"] += 1
                            op.updated_count += 1
                        else:
                            action = "CREATE"
                            # Filtra apenas os atributos que realmente existem no model
                            valid_fields = {f.name for f in ModelClass._meta.fields}
                            create_kwargs = {k: v for k, v in clean_data.items() if k in valid_fields}
                            instance = ModelClass.objects.create(**create_kwargs)
                            model_stats["created"] += 1
                            summary["created"] += 1
                            op.created_count += 1

                        after_snapshot = serialize_instance(instance)

                        SyncOperationRecord.objects.create(
                            operation=op,
                            model_name=model_name,
                            lookup_key=lookup_key,
                            lookup_value=str(clean_lookup_val),
                            action=action,
                            status="SUCCESS",
                            sheet_name=sheet_title,
                            row_number=row_number,
                            before_snapshot=before_snapshot,
                            after_snapshot=after_snapshot,
                        )

                except ValidationError as val_err:
                    # Registra erro de validação sem injetar valores falsos e segue
                    logger.warning(
                        "Validação falhou para %s linha %s (%s): %s",
                        model_name, row_number, lookup_val, val_err
                    )
                    model_stats["errors"] += 1
                    summary["errors"] += 1
                    op.error_count += 1
                    if not dry_run:
                        SyncOperationRecord.objects.create(
                            operation=op,
                            model_name=model_name,
                            lookup_key=lookup_key,
                            lookup_value=str(lookup_val),
                            action="ERROR",
                            status="ERROR",
                            sheet_name=sheet_title,
                            row_number=row_number,
                            before_snapshot=before_snapshot,
                            error_detail=str(val_err),
                        )

                except Exception as exc:
                    logger.error(
                        "Erro ao processar %s linha %s (%s): %s",
                        model_name, row_number, lookup_val, exc, exc_info=True
                    )
                    model_stats["errors"] += 1
                    summary["errors"] += 1
                    op.error_count += 1
                    if not dry_run:
                        SyncOperationRecord.objects.create(
                            operation=op,
                            model_name=model_name,
                            lookup_key=lookup_key,
                            lookup_value=str(lookup_val),
                            action="ERROR",
                            status="ERROR",
                            sheet_name=sheet_title,
                            row_number=row_number,
                            before_snapshot=before_snapshot,
                            error_detail=str(exc),
                        )


        # 4. Finaliza SyncOperation
        op.finished_at = timezone.now()
        op.total_records = summary["total_read"]
        if op.error_count == 0:
            op.status = "SUCCESS"
        elif op.created_count > 0 or op.updated_count > 0:
            op.status = "PARTIAL_SUCCESS"
        else:
            op.status = "FAILED"

        op.metadata = summary
        op.save()
        summary["status"] = op.status

    finally:
        set_syncing(False)

    return summary
