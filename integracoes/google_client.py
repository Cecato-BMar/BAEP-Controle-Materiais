"""Cliente Google Sheets API com isolamento estrito de permissões.

SEGURANÇA INEGOCIÁVEL:
- Planilha Antiga (LEGACY_SPREADSHEET_ID): escopo spreadsheets.readonly.
  Qualquer tentativa de escrita gera LegacySheetWriteForbidden.
- Planilha Nova (NEW_SPREADSHEET_ID): escopo spreadsheets (leitura e escrita).
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build

from integracoes.exceptions import (
    GoogleSheetsAPIError,
    GoogleSheetsAuthError,
    LegacySheetWriteForbidden,
)

logger = logging.getLogger(__name__)

READONLY_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
FULL_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_credentials(scopes: list[str]) -> service_account.Credentials:
    """Carrega as credenciais da Service Account a partir de settings.GOOGLE_SERVICE_ACCOUNT_INFO."""
    sa_info = getattr(settings, "GOOGLE_SERVICE_ACCOUNT_INFO", None)
    if not sa_info:
        raise GoogleSheetsAuthError(
            "Service Account do Google Sheets não configurada em settings.GOOGLE_SERVICE_ACCOUNT_INFO."
        )
    try:
        return service_account.Credentials.from_service_account_info(
            sa_info, scopes=scopes
        )
    except Exception as exc:
        raise GoogleSheetsAuthError(f"Falha ao instanciar credenciais do Google Sheets: {exc}") from exc


def get_legacy_service() -> Any:
    """Retorna cliente Google Sheets exclusivamente READ-ONLY para a planilha antiga."""
    creds = _get_credentials(READONLY_SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def get_new_service() -> Any:
    """Retorna cliente Google Sheets com permissão de leitura e escrita para a planilha nova."""
    creds = _get_credentials(FULL_SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def get_legacy_spreadsheet_id() -> str:
    """Obtém o ID da planilha legada configurado em settings."""
    sheet_id = getattr(settings, "LEGACY_SPREADSHEET_ID", None)
    if not sheet_id:
        raise GoogleSheetsAPIError("LEGACY_SPREADSHEET_ID não está configurado em settings.")
    return str(sheet_id).strip()


def get_new_spreadsheet_id() -> str:
    """Obtém o ID da planilha nova configurado em settings."""
    sheet_id = getattr(settings, "NEW_SPREADSHEET_ID", None)
    if not sheet_id:
        raise GoogleSheetsAPIError("NEW_SPREADSHEET_ID não está configurado em settings.")
    return str(sheet_id).strip()


def _resolve_spreadsheet_id(target: str) -> tuple[str, bool]:
    """Resolve o ID efetivo da planilha e se é legado.

    Retorna (spreadsheet_id, is_legacy).
    """
    legacy_id = getattr(settings, "LEGACY_SPREADSHEET_ID", "")
    new_id = getattr(settings, "NEW_SPREADSHEET_ID", "")

    if target == "legacy" or (legacy_id and target == legacy_id):
        return get_legacy_spreadsheet_id(), True
    if target == "new" or (new_id and target == new_id):
        return get_new_spreadsheet_id(), False
    return target, False


def _assert_write_allowed(spreadsheet_id_or_target: str) -> str:
    """Garante que a planilha de destino NÃO é a planilha legada.

    Levanta LegacySheetWriteForbidden caso qualquer tentativa de escrita
    seja direcionada para a planilha antiga.
    """
    legacy_id = getattr(settings, "LEGACY_SPREADSHEET_ID", None)
    target_clean = str(spreadsheet_id_or_target).strip()

    if target_clean == "legacy" or (legacy_id and target_clean == str(legacy_id).strip()):
        raise LegacySheetWriteForbidden(
            "A planilha legada (LEGACY) é estritamente somente leitura. "
            "Nenhuma operação de escrita (update/append/clear/batchUpdate) é permitida."
        )

    actual_id, is_legacy = _resolve_spreadsheet_id(target_clean)
    if is_legacy:
        raise LegacySheetWriteForbidden(
            "A planilha legada (LEGACY) é estritamente somente leitura. "
            "Nenhuma operação de escrita (update/append/clear/batchUpdate) é permitida."
        )
    return actual_id


def list_sheet_titles(spreadsheet_id_or_target: str = "new") -> list[str]:
    """Lista os nomes de todas as abas presentes em uma planilha."""
    actual_id, is_legacy = _resolve_spreadsheet_id(spreadsheet_id_or_target)
    service = get_legacy_service() if is_legacy else get_new_service()
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=actual_id).execute()
        sheets = sheet_metadata.get("sheets", [])
        return [s["properties"]["title"] for s in sheets if "properties" in s and "title" in s["properties"]]
    except Exception as exc:
        raise GoogleSheetsAPIError(f"Erro ao listar abas da planilha ({actual_id}): {exc}") from exc


def col_letter_to_index(col: str) -> int:
    """Converte letra de coluna do Sheets para índice 0-based ('A' -> 0, 'B' -> 1, 'AA' -> 26)."""
    idx = 0
    for char in col.upper():
        if "A" <= char <= "Z":
            idx = idx * 26 + (ord(char) - ord("A") + 1)
    return idx - 1


def read_sheet_values(spreadsheet_id_or_target: str, range_name: str) -> list[list[Any]]:
    """Lê todas as linhas de um intervalo especificado em uma planilha.

    Se o alvo for 'legacy' ou LEGACY_SPREADSHEET_ID, utiliza explicitamente o serviço read-only.
    """
    actual_id, is_legacy = _resolve_spreadsheet_id(spreadsheet_id_or_target)
    service = get_legacy_service() if is_legacy else get_new_service()
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=actual_id, range=range_name)
            .execute()
        )
        return result.get("values", [])
    except Exception as exc:
        raise GoogleSheetsAPIError(
            f"Erro ao ler intervalo '{range_name}' da planilha ({actual_id}): {exc}"
        ) from exc


def read_all(spreadsheet_id_or_target: str, sheet_name: str) -> list[list[Any]]:
    """Lê todas as linhas de uma aba da planilha."""
    range_name = f"'{sheet_name}'" if "'" not in sheet_name else sheet_name
    return read_sheet_values(spreadsheet_id_or_target, range_name)



def read_sheet_as_dicts(
    spreadsheet_id_or_target: str,
    sheet_name: str,
    data_start_row: int = 2,
    columns: dict[str, str] | None = None,
    stop_on_blank_lookup: bool = True,
    lookup_key: str | None = None,
    filter_rows: Callable[[dict[str, Any]], bool] | None = None,
) -> list[dict[str, Any]]:
    """Lê uma aba da planilha e converte as linhas em lista de dicionários mapeados por coluna.

    Cada dicionário resultante inclui '_row_number' indicando a linha física 1-based original.
    Linhas com número < data_start_row são ignoradas (cabeçalho/linhas iniciais).
    """
    if columns is None:
        columns = {}

    raw_rows = read_all(spreadsheet_id_or_target, sheet_name)
    col_map = {col_letter_to_index(letter): field_name for letter, field_name in columns.items()}
    records: list[dict[str, Any]] = []

    for row_idx, row in enumerate(raw_rows):
        row_num = row_idx + 1  # 1-based
        if row_num < data_start_row:
            continue

        item: dict[str, Any] = {"_row_number": row_num}
        for col_idx, field_name in col_map.items():
            val = row[col_idx] if col_idx < len(row) else ""
            if isinstance(val, str):
                val = val.strip()
            item[field_name] = val

        if lookup_key:
            lookup_val = str(item.get(lookup_key, "")).strip()
            if not lookup_val:
                if stop_on_blank_lookup:
                    break
                continue

        if filter_rows and not filter_rows(item):
            continue

        records.append(item)

    return records


# ============================================================================
# OPERAÇÕES DE ESCRITA — PROTEGIDAS PELA BARREIRA _assert_write_allowed

# ============================================================================

def update_row(
    spreadsheet_id_or_target: str,
    range_name: str,
    values: list[list[Any]],
    value_input_option: str = "USER_ENTERED",
) -> dict[str, Any]:
    """Atualiza linhas em um intervalo na planilha nova.

    BARREIRA: Levanta LegacySheetWriteForbidden imediatamente se o alvo for legado.
    """
    actual_id = _assert_write_allowed(spreadsheet_id_or_target)
    service = get_new_service()
    try:
        body = {"values": values}
        return (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=actual_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body,
            )
            .execute()
        )
    except Exception as exc:
        raise GoogleSheetsAPIError(
            f"Erro ao atualizar linhas em '{range_name}' na planilha ({actual_id}): {exc}"
        ) from exc


def append_row(
    spreadsheet_id_or_target: str,
    range_name: str,
    values: list[list[Any]],
    value_input_option: str = "USER_ENTERED",
) -> dict[str, Any]:
    """Adiciona novas linhas a uma aba na planilha nova.

    BARREIRA: Levanta LegacySheetWriteForbidden imediatamente se o alvo for legado.
    """
    actual_id = _assert_write_allowed(spreadsheet_id_or_target)
    service = get_new_service()
    try:
        body = {"values": values}
        return (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=actual_id,
                range=range_name,
                valueInputOption=value_input_option,
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )
    except Exception as exc:
        raise GoogleSheetsAPIError(
            f"Erro ao adicionar linhas em '{range_name}' na planilha ({actual_id}): {exc}"
        ) from exc


def clear(spreadsheet_id_or_target: str, range_name: str) -> dict[str, Any]:
    """Limpa o conteúdo de um intervalo na planilha nova.

    BARREIRA: Levanta LegacySheetWriteForbidden imediatamente se o alvo for legado.
    """
    actual_id = _assert_write_allowed(spreadsheet_id_or_target)
    service = get_new_service()
    try:
        return (
            service.spreadsheets()
            .values()
            .clear(spreadsheetId=actual_id, range=range_name)
            .execute()
        )
    except Exception as exc:
        raise GoogleSheetsAPIError(
            f"Erro ao limpar intervalo '{range_name}' na planilha ({actual_id}): {exc}"
        ) from exc


def batch_update(
    spreadsheet_id_or_target: str, requests: list[dict[str, Any]]
) -> dict[str, Any]:
    """Executa um lote de modificações (batchUpdate) na planilha nova.

    BARREIRA: Levanta LegacySheetWriteForbidden imediatamente se o alvo for legado.
    """
    actual_id = _assert_write_allowed(spreadsheet_id_or_target)
    service = get_new_service()
    try:
        body = {"requests": requests}
        return (
            service.spreadsheets()
            .batchUpdate(spreadsheetId=actual_id, body=body)
            .execute()
        )
    except Exception as exc:
        raise GoogleSheetsAPIError(
            f"Erro ao executar batchUpdate na planilha ({actual_id}): {exc}"
        ) from exc


# Aliases para compatibilidade
update_sheet_values = update_row
append_sheet_values = append_row
clear_sheet_values = clear
batch_update_spreadsheet = batch_update
