from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from policiais.models import Policial
from uniformes.models import TipoUniforme, EntregaUniforme, AlertaUniforme

User = get_user_model()


class UniformesModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="arquiteto_test",
            password="password123"
        )
        self.policial = Policial.objects.create(
            re="998877-6",
            nome="CABO OLIVEIRA",
            posto="CB_PM"
        )
        self.tipo = TipoUniforme.objects.create(
            nome="Calça Tática Ripstop",
            descricao="Calça reforçada tática preta",
            prazo_meses=12,
            dias_alerta=30,
            ativo=True
        )

    def test_data_vencimento_calc_basico(self):
        """Verifica se data_vencimento_calc é calculada com relativedelta(months=prazo_meses)."""
        tipo6m = TipoUniforme.objects.create(
            nome="Camisa Polo",
            prazo_meses=6,
            dias_alerta=15
        )
        data_base = date(2026, 3, 10)
        entrega = EntregaUniforme.objects.create(
            policial=self.policial,
            tipo_uniforme=tipo6m,
            data_entrega=data_base,
            quantidade=2
        )
        esperado = data_base + relativedelta(months=6)
        self.assertEqual(entrega.data_vencimento_calc, esperado)
        self.assertEqual(entrega.data_vencimento_calc, date(2026, 9, 10))

    def test_data_vencimento_boundary_month_end(self):
        """Verifica a fronteira de final de mês: 31/01/2026 + 1 mês = 28/02/2026."""
        tipo1m = TipoUniforme.objects.create(
            nome="Boina",
            prazo_meses=1,
            dias_alerta=5
        )
        data_janeiro = date(2026, 1, 31)
        entrega = EntregaUniforme.objects.create(
            policial=self.policial,
            tipo_uniforme=tipo1m,
            data_entrega=data_janeiro,
            quantidade=1
        )
        self.assertEqual(entrega.data_vencimento_calc, date(2026, 2, 28))

    def test_save_sem_tipo_carregado(self):
        """Testa salvar informando apenas tipo_uniforme_id sem a instância em cache."""
        entrega = EntregaUniforme(
            policial=self.policial,
            tipo_uniforme_id=self.tipo.pk,
            data_entrega=date(2026, 5, 1),
            quantidade=1
        )
        entrega.save()
        esperado = date(2026, 5, 1) + relativedelta(months=12)
        self.assertEqual(entrega.data_vencimento_calc, esperado)

    def test_dias_restantes_property(self):
        """Testa o cálculo da property dias_restantes para data futura e passada."""
        hoje = timezone.localdate()
        # Entrega vencendo daqui a 10 dias
        entrega_futura = EntregaUniforme(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=hoje,
            data_vencimento_calc=hoje + timedelta(days=10)
        )
        self.assertEqual(entrega_futura.dias_restantes, 10)

        # Entrega vencida há 5 dias
        entrega_passada = EntregaUniforme(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=hoje - timedelta(days=400),
            data_vencimento_calc=hoje - timedelta(days=5)
        )
        self.assertEqual(entrega_passada.dias_restantes, -5)

    def test_esta_vencido_property(self):
        """Testa se esta_vencido retorna True quando dias_restantes < 0."""
        hoje = timezone.localdate()
        entrega_vencida = EntregaUniforme(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=hoje - timedelta(days=400),
            data_vencimento_calc=hoje - timedelta(days=1)
        )
        entrega_ok = EntregaUniforme(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=hoje,
            data_vencimento_calc=hoje + timedelta(days=5)
        )
        self.assertTrue(entrega_vencida.esta_vencido)
        self.assertFalse(entrega_ok.esta_vencido)

    def test_esta_em_alerta_property(self):
        """Testa se esta_em_alerta é True quando 0 <= dias_restantes <= dias_alerta."""
        hoje = timezone.localdate()
        # dias_alerta = 30
        entrega_alerta = EntregaUniforme(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=hoje,
            data_vencimento_calc=hoje + timedelta(days=20)
        )
        entrega_longe = EntregaUniforme(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=hoje,
            data_vencimento_calc=hoje + timedelta(days=45)
        )
        entrega_ja_vencida = EntregaUniforme(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=hoje - timedelta(days=400),
            data_vencimento_calc=hoje - timedelta(days=1)
        )

        self.assertTrue(entrega_alerta.esta_em_alerta)
        self.assertFalse(entrega_longe.esta_em_alerta)
        self.assertFalse(entrega_ja_vencida.esta_em_alerta)  # Se venceu, não está em alerta, está vencido

    def test_str_tipo_uniforme(self):
        """__str__ retorna '{nome} ({prazo_meses} meses)'."""
        self.assertEqual(str(self.tipo), "Calça Tática Ripstop (12 meses)")

    def test_str_entrega_uniforme(self):
        """__str__ retorna formato esperado incluindo tipo, qtd, policial e data formatada."""
        entrega = EntregaUniforme.objects.create(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=date(2026, 4, 15),
            quantidade=3
        )
        esperado = f"Calça Tática Ripstop (x3) - {self.policial} (15/04/2026)"
        self.assertEqual(str(entrega), esperado)

    def test_marcar_como_lido(self):
        """Chama alerta.marcar_como_lido(user) e valida campos atualizados."""
        entrega = EntregaUniforme.objects.create(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=date(2026, 1, 1),
            quantidade=1
        )
        alerta = AlertaUniforme.objects.create(entrega=entrega)
        self.assertFalse(alerta.lido)
        self.assertIsNone(alerta.lido_em)
        self.assertIsNone(alerta.lido_por)

        alerta.marcar_como_lido(self.user)
        alerta.refresh_from_db()

        self.assertTrue(alerta.lido)
        self.assertIsNotNone(alerta.lido_em)
        self.assertEqual(alerta.lido_por, self.user)
