"""Cliente Google Sheets API (Service Account).

Será implementado na próxima fase.
"""

from __future__ import annotations

from typing import Any


def get_sheets_service() -> Any:
    """Retorna o serviço autenticado da Google Sheets API.

    Raises:
        NotImplementedError: até a implementação na próxima fase.
    """
    raise NotImplementedError("google_client.get_sheets_service — próxima fase")


def list_sheet_titles(spreadsheet_id: str) -> list[str]:
    """Lista os nomes das abas de uma planilha.

    Args:
        spreadsheet_id: ID da planilha no Google Sheets.

    Raises:
        NotImplementedError: até a implementação na próxima fase.
    """
    raise NotImplementedError("google_client.list_sheet_titles — próxima fase")
