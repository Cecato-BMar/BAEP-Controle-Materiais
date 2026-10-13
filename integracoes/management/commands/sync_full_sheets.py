"""Management command: sincronização e seed Sheets ↔ material_belico."""

from __future__ import annotations

import sys
from django.core.management.base import BaseCommand, CommandError

from integracoes.services.sync_full import seed_new_spreadsheet, sync_full


class Command(BaseCommand):
    help = (
        "Sincroniza material_belico com Google Sheets.\n\n"
        "Com --seed: executa o seed inicial da planilha nova a partir do Django.\n"
        "  - Sem --force: recusa execução se SheetRowSnapshot já existir.\n"
        "  - Com --force: limpa as abas da planilha nova (perde formatação manual) e reescreve tudo.\n\n"
        "Sem --seed: executa a sincronização completa bidirecional (pull + push)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--seed",
            action="store_true",
            help="Executa o seed inicial da planilha nova a partir do Django.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Força a re-execução do seed quando já executado anteriormente. "
                "ATENÇÃO: limpa as abas na planilha nova (perde formatação manual) e reescreve tudo."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula a execução sem alterar o banco de dados ou a planilha.",
        )
        parser.add_argument(
            "--model",
            type=str,
            default=None,
            help="Limita a operação a um model específico (ex: PistolaGlock).",
        )

    def handle(self, *args: object, **options: object) -> None:
        is_seed = bool(options.get("seed", False))
        force = bool(options.get("force", False))
        dry_run = bool(options.get("dry_run", False))
        model_name = options.get("model")

        if is_seed:
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"Iniciando SEED da planilha nova (dry_run={dry_run}, force={force})..."
                )
            )
            try:
                summary = seed_new_spreadsheet(dry_run=dry_run, force=force)
            except Exception as exc:
                raise CommandError(f"Falha ao executar seed_new_spreadsheet: {exc}") from exc

            status = summary.get("status", "UNKNOWN")
            msg = (
                f"Seed finalizado com status [{status}]. Total criados: {summary.get('created', 0)}, "
                f"Erros: {summary.get('errors', 0)} (Op #{summary.get('operation_id')})"
            )
            if status == "SUCCESS":
                self.stdout.write(self.style.SUCCESS(msg))
            elif status == "PARTIAL_SUCCESS":
                self.stdout.write(self.style.WARNING(msg))
            else:
                self.stdout.write(self.style.ERROR(msg))
                raise CommandError(msg)
        else:
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"Iniciando sincronização completa (pull + push, dry_run={dry_run}, model={model_name})..."
                )
            )
            try:
                summary = sync_full(model_name=str(model_name) if model_name else None, dry_run=dry_run)
            except Exception as exc:
                raise CommandError(f"Falha ao executar sync_full: {exc}") from exc

            status = summary.get("status", "UNKNOWN")
            msg = f"Sincronização finalizada com status [{status}]."
            if status == "SUCCESS":
                self.stdout.write(self.style.SUCCESS(msg))
            elif status == "PARTIAL_SUCCESS":
                self.stdout.write(self.style.WARNING(msg))
            else:
                self.stdout.write(self.style.ERROR(msg))
                raise CommandError(msg)
