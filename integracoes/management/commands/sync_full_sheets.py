"""Management command: sincronização completa Sheets ↔ material_belico.

Será implementado na próxima fase.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sincroniza material_belico com Google Sheets (pull + push). Placeholder."

    def handle(self, *args: object, **options: object) -> None:
        self.stdout.write(
            self.style.WARNING(
                "sync_full_sheets ainda não implementado — próxima fase."
            )
        )
