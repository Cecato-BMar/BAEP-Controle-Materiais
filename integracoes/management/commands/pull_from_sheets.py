"""Management command: pull de dados da planilha Google Sheets para o Django."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from integracoes.services.pull import pull_from_sheets


class Command(BaseCommand):
    help = (
        "Sincroniza dados da planilha nova (Google Sheets) para o Django (material_belico).\n\n"
        "Requer --confirm para aplicar alterações no banco ou --dry-run para simular.\n"
        "Com --force: força atualização mesmo se o content_hash da linha não tiver mudado."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirma a execução real e escrita no banco de dados.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula a execução sem alterar o banco de dados nem a planilha.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Força atualização dos registros ignorando o content_hash.",
        )
        parser.add_argument(
            "--model",
            type=str,
            default=None,
            help="Limita o pull a um model específico (ex: PistolaGlock).",
        )

    def handle(self, *args: object, **options: object) -> None:
        confirm = bool(options.get("confirm", False))
        dry_run = bool(options.get("dry_run", False))
        force = bool(options.get("force", False))
        model_name = options.get("model")

        if not confirm and not dry_run:
            raise CommandError(
                "O comando pull_from_sheets requer --confirm para aplicar alterações "
                "no banco de dados ou --dry-run para simulação segura."
            )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Iniciando PULL do Google Sheets (model={model_name}, dry_run={dry_run}, force={force})..."
            )
        )

        try:
            summary = pull_from_sheets(
                model_name=str(model_name) if model_name else None,
                dry_run=dry_run,
                force=force,
            )
        except Exception as exc:
            raise CommandError(f"Falha ao executar pull_from_sheets: {exc}") from exc

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
            f"{tag} Pull finalizado. Total: {total}, Criados: {created}, "
            f"Atualizados: {updated}, Ignorados (skip): {skipped}, Erros: {errors} (Op #{op_id})"
        )
        self.stdout.write(style_fn(msg))

        if status == "FAILED":
            raise CommandError(msg)
