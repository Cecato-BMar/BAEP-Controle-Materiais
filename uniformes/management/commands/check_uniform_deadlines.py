from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from uniformes.models import EntregaUniforme, AlertaUniforme


class Command(BaseCommand):
    help = "Verifica entregas ativas com vencimento próximo e cria AlertaUniforme de forma idempotente."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula a verificação e exibe o que seria feito sem criar alertas no banco."
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        hoje = timezone.localdate()

        self.stdout.write(f"Iniciando verificação de prazos de uniformes para {hoje.strftime('%d/%m/%Y')}...")

        entregas = EntregaUniforme.objects.filter(
            ativa=True
        ).select_related('tipo_uniforme', 'policial')

        criados = 0
        ignorados = 0
        total_analisadas = 0

        for entrega in entregas:
            total_analisadas += 1
            if not entrega.data_vencimento_calc or not entrega.tipo_uniforme:
                continue

            limite = entrega.data_vencimento_calc - timedelta(days=entrega.tipo_uniforme.dias_alerta)

            # Verifica se hoje já atingiu ou ultrapassou a data limite de alerta
            if hoje >= limite:
                # Idempotência (Opção B): cada entrega gera no máximo 1 alerta em toda a sua vida ativa
                ja_alertado = AlertaUniforme.objects.filter(entrega=entrega).exists()
                if ja_alertado:
                    ignorados += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        self.style.NOTICE(
                            f"[DRY-RUN] Criaria alerta para: {entrega.policial} - {entrega.tipo_uniforme.nome} "
                            f"(Vence em {entrega.data_vencimento_calc.strftime('%d/%m/%Y')})"
                        )
                    )
                else:
                    AlertaUniforme.objects.create(entrega=entrega)

                criados += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY-RUN] Simulação concluída: {criados} alerta(s) seriam criado(s), "
                    f"{ignorados} entrega(s) já alertada(s) de um total de {total_analisadas} entrega(s) ativa(s). "
                    f"Nenhuma alteração gravada."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Verificação concluída: {criados} novo(s) alerta(s) criado(s), "
                    f"{ignorados} entrega(s) já alertada(s) mantida(s) de um total de {total_analisadas} entrega(s) ativa(s)."
                )
            )
