"""Management command: push de alterações do Django para a planilha Google Sheets."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from integracoes.services.push import push_to_sheets


class Command(BaseCommand):
    help = (
        "Envia alterações do Django (material_belico) para a planilha nova (Google Sheets).\n\n"
        "Requer --confirm para aplicar alterações na planilha ou --dry-run para simulação.\n"
        "Com --since <ISO8601>: define marco temporal inicial para envio."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirma a execução real e escrita na planilha.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula a execução sem alterar a planilha nem o banco.",
        )
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="Data/hora inicial ISO8601 (ex: 2026-10-13T10:00:00).",
        )
        parser.add_argument(
            "--model",
            type=str,
            default=None,
            help="Limita o push a um model específico (ex: PistolaGlock).",
        )

    def handle(self, *args: object, **options: object) -> None:
        confirm = bool(options.get("confirm", False))
        dry_run = bool(options.get("dry_run", False))
        since_str = options.get("since")
        model_name = options.get("model")

        if not confirm and not dry_run:
            raise CommandError(
                "O comando push_to_sheets requer --confirm para aplicar alterações "
                "na planilha ou --dry-run para simulação segura."
            )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Iniciando PUSH para Google Sheets (model={model_name}, dry_run={dry_run}, since={since_str})..."
            )
        )

        try:
            summary = push_to_sheets(
                model_name=str(model_name) if model_name else None,
                dry_run=dry_run,
                since=str(since_str) if since_str else None,
            )
        except Exception as exc:
            raise CommandError(f"Falha ao executar push_to_sheets: {exc}") from exc

        status = summary.get("status", "UNKNOWN")
        total = summary.get("total", 0)
        created = summary.get("created", 0)
        updated = summary.get("updated", 0)
        skipped = summary.get("skipped", 0)
        errors = summary.get("errors", 0)
        op_id = summary.get("operation_id")

        if status == "SUCCESS":
            tag = "[OK]"
            style_fn = self.style.SUCCESS
        elif status == "PARTIAL_SUCCESS":
            tag = "[PARCIAL]"
            style_fn = self.style.WARNING
        else:
            tag = "[FALHA]"
            style_fn = self.style.ERROR

        msg = (
            f"{tag} Push finalizado. Total considerados: {total}, Novos (append): {created}, "
            f"Atualizados (batch): {updated}, Ignorados: {skipped}, Erros: {errors} (Op #{op_id})"
        )
        self.stdout.write(style_fn(msg))

        if status == "FAILED":
            raise CommandError(msg)
