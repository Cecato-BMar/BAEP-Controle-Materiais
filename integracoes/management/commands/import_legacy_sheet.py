"""Management command para importar dados da planilha antiga (LEGACY) para o Django.

Uso:
    python manage.py import_legacy_sheet --dry-run
    python manage.py import_legacy_sheet --confirm
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from integracoes.exceptions import ImportDisabledError, LegacySheetWriteForbidden
from integracoes.services.import_legacy import import_legacy_sheet


class Command(BaseCommand):
    help = "Importa registros das 6 abas da planilha antiga (LEGACY - Read-Only) para o banco de dados."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula a leitura da planilha e validação dos dados sem modificar o banco de dados.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirma a execução real da importação com persistência no banco de dados.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        confirm: bool = options["confirm"]

        if not dry_run and not confirm:
            raise CommandError(
                "A importação real altera dados no banco de dados. "
                "Para executar a importação real, informe a flag --confirm. "
                "Para apenas simular sem alterações, utilize --dry-run."
            )

        mode_str = "SIMULAÇÃO (DRY-RUN)" if dry_run else "EXECUÇÃO REAL"
        self.stdout.write(self.style.WARNING(f"\n=== Iniciando importação da Planilha Antiga: {mode_str} ===\n"))

        try:
            summary = import_legacy_sheet(dry_run=dry_run, confirm=confirm)
        except ImportDisabledError as exc:
            raise CommandError(f"Importação desabilitada: {exc}") from exc
        except LegacySheetWriteForbidden as exc:
            raise CommandError(f"Violação de segurança: {exc}") from exc
        except Exception as exc:
            raise CommandError(f"Erro durante a importação: {exc}") from exc

        status = summary.get("status", "")
        if status == "FAILED":
            self.stdout.write(self.style.ERROR("[FALHA] Processamento da planilha legada concluido!\n"))
        elif status == "PARTIAL_SUCCESS":
            self.stdout.write(self.style.WARNING("[PARCIAL] Processamento da planilha legada concluido!\n"))
        else:
            self.stdout.write(self.style.SUCCESS("[OK] Processamento da planilha legada concluido!\n"))
        self.stdout.write(f"Operação ID: #{summary['operation_id']}")
        self.stdout.write(f"Status final: {status}")
        self.stdout.write(f"Total de linhas lidas: {summary['total_read']}")
        self.stdout.write(f"Registros criados: {summary['created']}")
        self.stdout.write(f"Registros atualizados: {summary['updated']}")
        self.stdout.write(f"Erros de validação: {summary['errors']}")
        self.stdout.write(f"Linhas ignoradas (em branco): {summary['skipped']}\n")

        self.stdout.write("Detalhamento por modelo:")
        for model_name, stats in summary["details_by_model"].items():
            self.stdout.write(
                f"  - {model_name:18} | Lidos: {stats['read']:3} | "
                f"Criados: {stats['created']:3} | Atualizados: {stats['updated']:3} | "
                f"Erros: {stats['errors']:2} | Ignorados: {stats['skipped']:2}"
            )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    "\n[AVISO] Modo dry-run: Nenhuma alteração foi gravada no banco de dados."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n[SUCESSO] Importação concluída e registrada no histórico de auditoria."
                )
            )
