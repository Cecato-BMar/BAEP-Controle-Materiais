"""Exceções customizadas para o módulo de integrações com Google Sheets."""

class IntegracoesBaseError(Exception):
    """Exceção base para o app integracoes."""
    pass


class LegacySheetWriteForbidden(IntegracoesBaseError):
    """Lançada quando qualquer tentativa de escrita é feita contra a planilha antiga (LEGACY).
    A planilha legada é estritamente somente leitura (spreadsheets.readonly).
    """
    pass


class SheetsSyncDisabledError(IntegracoesBaseError):
    """Lançada quando a sincronização com Google Sheets está desativada em settings."""
    pass


class ImportDisabledError(IntegracoesBaseError):
    """Lançada quando a importação legada está desativada em settings."""
    pass


class GoogleSheetsAuthError(IntegracoesBaseError):
    """Lançada quando as credenciais da Service Account do Google Sheets são inválidas ou ausentes."""
    pass


class GoogleSheetsAPIError(IntegracoesBaseError):
    """Lançada em caso de erro na comunicação com a Google Sheets API."""
    pass


class SyncConflictError(IntegracoesBaseError):
    """Lançada quando um conflito não resolvível é detectado durante a sincronização."""
    pass


class RollbackError(IntegracoesBaseError):
    """Lançada quando uma tentativa de reversão/rollback via restore_point falha."""
    pass
