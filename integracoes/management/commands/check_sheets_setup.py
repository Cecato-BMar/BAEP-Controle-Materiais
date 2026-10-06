"""Valida a configuração da integração Google Sheets."""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verifica se as variáveis e credenciais do Google Sheets estão configuradas."

    def handle(self, *args: object, **options: object) -> None:
        # 1) Service Account
        sa_info = getattr(settings, "GOOGLE_SERVICE_ACCOUNT_INFO", None)
        if sa_info is not None:
            client_email = sa_info.get("client_email", "(desconhecido)")
            self.stdout.write(
                self.style.SUCCESS(f"[OK] Service Account: {client_email}")
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "[ERRO] Service Account não carregada — verifique GOOGLE_SERVICE_ACCOUNT_JSON"
                )
            )

        # 2) Planilha antiga (LEGACY_SPREADSHEET_ID)
        legacy_id = (getattr(settings, "LEGACY_SPREADSHEET_ID", "") or "").strip()
        if legacy_id:
            self.stdout.write(
                self.style.SUCCESS(f"[OK] LEGACY_SPREADSHEET_ID: {legacy_id[:12]}…")
            )
        else:
            self.stdout.write(
                self.style.WARNING("[AVISO] LEGACY_SPREADSHEET_ID não configurado")
            )

        # 3) Planilha nova (NEW_SPREADSHEET_ID)
        new_id = (getattr(settings, "NEW_SPREADSHEET_ID", "") or "").strip()
        if new_id:
            self.stdout.write(
                self.style.SUCCESS(f"[OK] NEW_SPREADSHEET_ID: {new_id[:12]}…")
            )
        else:
            self.stdout.write(
                self.style.WARNING("[AVISO] NEW_SPREADSHEET_ID não configurado")
            )

        # 4) Flags informativas
        sync_enabled = bool(getattr(settings, "SHEETS_SYNC_ENABLED", False))
        import_enabled = bool(getattr(settings, "IMPORT_ENABLED", False))
        self.stdout.write(f"[INFO] SHEETS_SYNC_ENABLED = {sync_enabled}")
        self.stdout.write(f"[INFO] IMPORT_ENABLED = {import_enabled}")

        self.stdout.write(
            "Configuração validada. Próxima fase: conectar às planilhas."
        )
