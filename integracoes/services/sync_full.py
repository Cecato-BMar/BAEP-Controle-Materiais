"""Seed da planilha nova e orquestração pull + push (Bloco 3).

REGRAS:
- Escrita exclusivamente em NEW_SPREADSHEET_ID (nunca LEGACY).
- Guard SHEETS_SYNC_ENABLED em seed e no orquestrador (pull/push têm o próprio).
- Backup automático apenas quando dry_run=False.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from integracoes.backup import serialize_instance
from integracoes.exceptions import SheetsSyncDisabledError
from integracoes.google_client import (
    append_row,
    batch_update,
    list_sheet_titles,
    update_row,
)
from integracoes.mapping import NEW_SHEET_MAP, SYNC_ORDER, get_model_class
from integracoes.models import (
    SheetRowSnapshot,
    SheetSyncState,
    SyncOperation,
    SyncOperationRecord,
)

logger = logging.getLogger(__name__)

SEED_APPEND_BATCH_SIZE = 500
_UPDATED_RANGE_ROW_RE = re.compile(r"!\$?[A-Za-z]+\$?(\d+)", re.IGNORECASE)
_BARE_RANGE_ROW_RE = re.compile(r"^\$?[A-Za-z]+\$?(\d+)", re.IGNORECASE)


def _assert_sheets_sync_enabled() -> None:
    if not getattr(settings, "SHEETS_SYNC_ENABLED", False):
        raise SheetsSyncDisabledError(
            "SHEETS_SYNC_ENABLED está desabilitado em settings. "
            "Ligue a flag antes de executar seed/sync."
        )


def _extract_row_from_updated_range(updated_range: str | None) -> int | None:
    """Extrai o número da primeira linha de um updatedRange do Sheets.

    Exemplos:
        "Pistolas_Glock!A5:K5" → 5
        "'HT 26'!A2:H10" → 2
        "A3:C3" → 3
    """
    if not updated_range or not str(updated_range).strip():
        return None
    text = str(updated_range).strip()
    match = _UPDATED_RANGE_ROW_RE.search(text)
    if match:
        return int(match.group(1))
    match = _BARE_RANGE_ROW_RE.match(text)
    if match:
        return int(match.group(1))
    return None


def _serialize_cell(value: Any) -> Any:
    """Converte valores Python para representação adequada à planilha."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        # Número nativo no Sheets (não texto) para fórmulas (=SUM etc.)
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, bool):
        return value
    return value


def compute_content_hash(row: dict[str, Any]) -> str:
    """SHA-256 determinístico do conteúdo da linha (chaves ordenadas)."""
    payload = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_row_from_instance(model_name: str, obj: Any) -> tuple[list[Any], dict[str, Any]]:
    """Monta lista de valores (ordem das colunas) e dict nome→valor para hash/audit.

    Usa column_aliases: nome na planilha → atributo no model
    (ex.: atualizado_em → data_atualizacao).
    """
    conf = NEW_SHEET_MAP[model_name]
    columns: list[str] = conf["columns"]
    aliases: dict[str, str] = conf.get("column_aliases", {})

    values: list[Any] = []
    row_dict: dict[str, Any] = {}
    for col in columns:
        model_field = aliases.get(col, col)
        raw = getattr(obj, model_field, None)
        cell = _serialize_cell(raw)
        values.append(cell)
        row_dict[col] = cell
    return values, row_dict


def _sheet_range(sheet_name: str, a1: str) -> str:
    """Monta range A1 com nome de aba escapado."""
    if "'" in sheet_name:
        return f"{sheet_name}!{a1}"
    return f"'{sheet_name}'!{a1}"


def _ensure_sheet_exists(existing_titles: list[str], sheet_name: str, dry_run: bool) -> list[str]:
    """Cria a aba na planilha nova se ainda não existir. Retorna lista atualizada de títulos."""
    if sheet_name in existing_titles:
        return existing_titles
    if dry_run:
        logger.info("[dry-run] Criaria aba '%s' via batch_update(addSheet).", sheet_name)
        return existing_titles + [sheet_name]
    batch_update(
        "new",
        [{"addSheet": {"properties": {"title": sheet_name}}}],
    )
    return existing_titles + [sheet_name]


def _finalize_operation(op: SyncOperation, summary: dict[str, Any]) -> dict[str, Any]:
    op.finished_at = timezone.now()
    op.total_records = summary.get("total", summary.get("processed", 0))
    op.created_count = summary.get("created", 0)
    op.updated_count = summary.get("updated", 0)
    op.error_count = summary.get("errors", 0)
    op.skipped_count = summary.get("skipped", 0)
    if op.error_count == 0:
        op.status = "SUCCESS"
    elif op.created_count > 0 or op.updated_count > 0:
        op.status = "PARTIAL_SUCCESS"
    else:
        op.status = "FAILED"
    op.metadata = summary
    op.save()
    summary["status"] = op.status
    summary["operation_id"] = op.pk
    return summary


def seed_new_spreadsheet(dry_run: bool = False) -> dict[str, Any]:
    """Popula a planilha nova com o estado atual do Django (abas 1:1).

    - Cria SyncOperation(operation_type="SEED")
    - Sem backup físico (seed só escreve na planilha nova + snapshots)
    - Para cada model em SYNC_ORDER: cria aba, cabeçalho, append em lotes de 500
    - Popula SheetRowSnapshot e SyncOperationRecord
    - Atualiza SheetSyncState.last_push_at ao final
    """
    _assert_sheets_sync_enabled()

    op = SyncOperation.objects.create(
        operation_type="SEED",
        status="IN_PROGRESS",
        backup_file_path=None,
        metadata={"dry_run": dry_run},
    )

    summary: dict[str, Any] = {
        "operation_id": op.pk,
        "dry_run": dry_run,
        "total": 0,
        "created": 0,
        "errors": 0,
        "per_model": {},
    }

    try:
        existing_titles = list_sheet_titles("new") if not dry_run else []
    except Exception as exc:
        logger.error("Falha ao listar abas da planilha nova: %s", exc)
        summary["errors"] += 1
        op.error_message = str(exc)
        return _finalize_operation(op, summary)

    try:
        for model_name in SYNC_ORDER:
            if model_name not in NEW_SHEET_MAP:
                continue

            conf = NEW_SHEET_MAP[model_name]
            sheet_name: str = conf["sheet"]
            columns: list[str] = conf["columns"]
            lookup_key: str = conf["lookup_key"]
            ModelClass = get_model_class(model_name)

            model_stats = {"total": 0, "created": 0, "errors": 0}
            summary["per_model"][model_name] = model_stats

            try:
                existing_titles = _ensure_sheet_exists(existing_titles, sheet_name, dry_run)

                if not dry_run:
                    update_row(
                        "new",
                        _sheet_range(sheet_name, "A1"),
                        [columns],
                    )

                objects = list(ModelClass.objects.all().order_by("pk"))
                model_stats["total"] = len(objects)
                summary["total"] += len(objects)

                # Contador sequencial local (fallback / dry-run): linha 1 = header
                next_row = 2
                batch_values: list[list[Any]] = []
                batch_meta: list[tuple[Any, dict[str, Any]]] = []

                def _flush_batch() -> None:
                    nonlocal next_row, batch_values, batch_meta
                    if not batch_values:
                        return

                    start_row = next_row
                    if not dry_run:
                        response = append_row(
                            "new",
                            _sheet_range(sheet_name, "A:ZZ"),
                            batch_values,
                        )
                        updates = (response or {}).get("updates") or {}
                        parsed = _extract_row_from_updated_range(updates.get("updatedRange"))
                        if parsed is not None:
                            start_row = parsed

                    for offset, (obj, row_dict) in enumerate(batch_meta):
                        row_number = start_row + offset
                        content_hash = compute_content_hash(row_dict)
                        lookup_value = str(obj.pk)

                        if not dry_run:
                            SheetRowSnapshot.objects.update_or_create(
                                model_name=model_name,
                                lookup_value=lookup_value,
                                defaults={
                                    "lookup_key": lookup_key,
                                    "row_number": row_number,
                                    "content_hash": content_hash,
                                },
                            )
                            SyncOperationRecord.objects.create(
                                operation=op,
                                model_name=model_name,
                                lookup_key=lookup_key,
                                lookup_value=lookup_value,
                                action="CREATE",
                                status="SUCCESS",
                                sheet_name=sheet_name,
                                row_number=row_number,
                                after_snapshot=serialize_instance(obj),
                            )

                        model_stats["created"] += 1
                        summary["created"] += 1

                    next_row = start_row + len(batch_values)
                    batch_values = []
                    batch_meta = []

                for obj in objects:
                    try:
                        values, row_dict = build_row_from_instance(model_name, obj)
                        batch_values.append(values)
                        batch_meta.append((obj, row_dict))
                        if len(batch_values) >= SEED_APPEND_BATCH_SIZE:
                            _flush_batch()
                    except Exception as exc:
                        logger.error(
                            "Erro no seed de %s pk=%s: %s",
                            model_name,
                            getattr(obj, "pk", "?"),
                            exc,
                            exc_info=True,
                        )
                        model_stats["errors"] += 1
                        summary["errors"] += 1
                        if not dry_run:
                            SyncOperationRecord.objects.create(
                                operation=op,
                                model_name=model_name,
                                lookup_key=lookup_key,
                                lookup_value=str(getattr(obj, "pk", "")),
                                action="ERROR",
                                status="ERROR",
                                sheet_name=sheet_name,
                                error_detail=str(exc),
                            )

                _flush_batch()

            except Exception as exc:
                logger.error("Erro ao processar model %s no seed: %s", model_name, exc, exc_info=True)
                model_stats["errors"] += 1
                summary["errors"] += 1
                if not dry_run:
                    SyncOperationRecord.objects.create(
                        operation=op,
                        model_name=model_name,
                        lookup_key="sheet",
                        lookup_value=sheet_name,
                        action="ERROR",
                        status="ERROR",
                        sheet_name=sheet_name,
                        error_detail=str(exc),
                    )

        if not dry_run:
            with transaction.atomic():
                state, _ = SheetSyncState.objects.select_for_update().get_or_create(key="global")
                state.last_push_at = timezone.now()
                state.last_push_status = "SUCCESS" if summary["errors"] == 0 else "PARTIAL"
                state.save(update_fields=["last_push_at", "last_push_status"])

    except Exception as exc:
        logger.error("Falha geral no seed: %s", exc, exc_info=True)
        summary["errors"] += 1
        op.error_message = str(exc)

    return _finalize_operation(op, summary)


def sync_full(model_name: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Orquestra pull_from_sheets seguido de push_to_sheets.

    Imports lazy para permitir carregar este módulo antes de pull/push existirem.
    """
    _assert_sheets_sync_enabled()

    from integracoes.services.pull import pull_from_sheets
    from integracoes.services.push import push_to_sheets

    pull_summary = pull_from_sheets(model_name=model_name, dry_run=dry_run)
    push_summary = push_to_sheets(model_name=model_name, dry_run=dry_run)

    pull_status = pull_summary.get("status", "")
    push_status = push_summary.get("status", "")
    if pull_status == "FAILED" or push_status == "FAILED":
        combined_status = "FAILED"
    elif pull_status == "PARTIAL_SUCCESS" or push_status == "PARTIAL_SUCCESS":
        combined_status = "PARTIAL_SUCCESS"
    else:
        combined_status = "SUCCESS"

    return {
        "dry_run": dry_run,
        "model_name": model_name,
        "status": combined_status,
        "pull": pull_summary,
        "push": push_summary,
    }
