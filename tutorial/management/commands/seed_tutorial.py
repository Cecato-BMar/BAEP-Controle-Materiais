from django.core.management.base import BaseCommand

from tutorial.seeder import seed_tutorial


class Command(BaseCommand):
    help = 'Sincroniza o conteúdo padrão do tutorial (idempotente).'

    def handle(self, *args, **options):
        criados_m, novos_s = seed_tutorial()
        self.stdout.write(self.style.SUCCESS(
            f'Tutorial sincronizado: {criados_m} módulos novos, '
            f'{novos_s} seções novas.'))