"""Valida a configuração da integração Google Sheets."""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verifica se as variáveis e credenciais do Google Sheets estão ok."

    def handle(self, *args: object, **options: object) -> None:
        ok = True

        # 1) Service Account JSON carregado
        sa_info = getattr(settings, "GOOGLE_SERVICE_ACCOUNT_INFO", None)
        if sa_info is None:
            ok = False
            self.stdout.write(
                self.style.ERROR(
                    "[FALHA] GOOGLE_SERVICE_ACCOUNT_INFO não carregado. "
                    "Defina GOOGLE_SERVICE_ACCOUNT_JSON (base64 do creds.json)."
                )
            )
        else:
            client_email = sa_info.get("client_email", "(ausente no JSON)")
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Service Account carregada: {client_email}"
                )
            )

        # 2) Spreadsheet ID
        spreadsheet_id = getattr(settings, "GOOGLE_SHEETS_SPREADSHEET_ID", "") or ""
        if not spreadsheet_id.strip():
            ok = False
            self.stdout.write(
                self.style.ERROR(
                    "[FALHA] GOOGLE_SHEETS_SPREADSHEET_ID está vazio."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Spreadsheet ID configurado: {spreadsheet_id[:8]}…"
                )
            )

        # 3) Flag de sync (informativo)
        enabled = getattr(settings, "SHEETS_SYNC_ENABLED", False)
        self.stdout.write(
            f"[INFO] SHEETS_SYNC_ENABLED = {enabled}"
        )

        # 4) TODO: abrir planilha e listar abas (próxima fase — google_client)
        # from integracoes.google_client import list_sheet_titles
        # titles = list_sheet_titles(spreadsheet_id)
        # self.stdout.write(f"[OK] Abas: {', '.join(titles)}")
        self.stdout.write(
            self.style.WARNING(
                "[TODO] Conexão com a planilha (listar abas) — próxima fase."
            )
        )

        if ok:
            self.stdout.write(
                self.style.SUCCESS(
                    "Setup parcial OK. Complete as variáveis e aguarde a próxima fase."
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Setup incompleto. Corrija os itens [FALHA] acima."
                )
            )
