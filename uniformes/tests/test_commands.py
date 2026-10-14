from io import StringIO
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils import timezone

from policiais.models import Policial
from uniformes.models import TipoUniforme, EntregaUniforme, AlertaUniforme

User = get_user_model()


class CheckUniformDeadlinesCommandTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="sargento_test",
            password="password123"
        )
        self.policial = Policial.objects.create(
            re="112233-4",
            nome="SGT ALMEIDA",
            posto="2SGT_PM"
        )
        self.tipo = TipoUniforme.objects.create(
            nome="Gandola Tática",
            prazo_meses=12,
            dias_alerta=30,
            ativo=True
        )

    def test_cria_alerta_dentro_do_prazo(self):
        """Entrega vencendo em 10 dias com dias_alerta=30 deve gerar 1 AlertaUniforme."""
        hoje = timezone.localdate()
        # Data de entrega configurada para vencer em 10 dias
        data_entrega = hoje - relativedelta(months=12) + timedelta(days=10)
        entrega = EntregaUniforme.objects.create(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=data_entrega,
            quantidade=1
        )

        out = StringIO()
        call_command("check_uniform_deadlines", stdout=out)

        self.assertEqual(AlertaUniforme.objects.filter(entrega=entrega).count(), 1)
        self.assertIn("1 novo(s) alerta(s) criado(s)", out.getvalue())

    def test_nao_cria_alerta_fora_do_prazo(self):
        """Entrega vencendo em 60 dias com dias_alerta=30 não deve gerar alerta."""
        hoje = timezone.localdate()
        data_entrega = hoje - relativedelta(months=12) + timedelta(days=60)
        entrega = EntregaUniforme.objects.create(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=data_entrega,
            quantidade=1
        )

        out = StringIO()
        call_command("check_uniform_deadlines", stdout=out)

        self.assertEqual(AlertaUniforme.objects.filter(entrega=entrega).count(), 0)
        self.assertIn("0 novo(s) alerta(s) criado(s)", out.getvalue())

    def test_idempotencia_apos_leitura(self):
        """(Opção B): Alerta criado e já lido pelo operador NÃO deve ser duplicado em novas execuções."""
        hoje = timezone.localdate()
        data_entrega = hoje - relativedelta(months=12) + timedelta(days=5)
        entrega = EntregaUniforme.objects.create(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=data_entrega,
            quantidade=1
        )

        # 1ª execução: cria o alerta
        call_command("check_uniform_deadlines", stdout=StringIO())
        alerta = AlertaUniforme.objects.get(entrega=entrega)
        alerta.marcar_como_lido(self.user)
        self.assertTrue(alerta.lido)

        # 2ª execução: não deve criar novo alerta
        out = StringIO()
        call_command("check_uniform_deadlines", stdout=out)

        self.assertEqual(AlertaUniforme.objects.filter(entrega=entrega).count(), 1)
        self.assertIn("0 novo(s) alerta(s) criado(s)", out.getvalue())
        self.assertIn("1 entrega(s) já alertada(s) mantida(s)", out.getvalue())

    def test_idempotencia_com_alerta_pendente(self):
        """Rodar o comando 2 vezes consecutivas com alerta pendente não duplica."""
        hoje = timezone.localdate()
        data_entrega = hoje - relativedelta(months=12) + timedelta(days=15)
        entrega = EntregaUniforme.objects.create(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=data_entrega,
            quantidade=1
        )

        # 1ª execução
        call_command("check_uniform_deadlines", stdout=StringIO())
        self.assertEqual(AlertaUniforme.objects.filter(entrega=entrega, lido=False).count(), 1)

        # 2ª execução
        out = StringIO()
        call_command("check_uniform_deadlines", stdout=out)

        self.assertEqual(AlertaUniforme.objects.filter(entrega=entrega).count(), 1)
        self.assertIn("0 novo(s) alerta(s) criado(s)", out.getvalue())

    def test_ignora_entrega_inativa(self):
        """Entregas canceladas (ativa=False) devem ser ignoradas mesmo se vencidas."""
        hoje = timezone.localdate()
        data_entrega = hoje - relativedelta(months=12) - timedelta(days=20)
        entrega = EntregaUniforme.objects.create(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=data_entrega,
            quantidade=1,
            ativa=False
        )

        out = StringIO()
        call_command("check_uniform_deadlines", stdout=out)

        self.assertEqual(AlertaUniforme.objects.filter(entrega=entrega).count(), 0)
        self.assertIn("0 novo(s) alerta(s) criado(s)", out.getvalue())

    def test_dry_run_nao_altera_banco(self):
        """A flag --dry-run deve exibir a simulação sem persistir alertas no banco de dados."""
        hoje = timezone.localdate()
        data_entrega = hoje - relativedelta(months=12) + timedelta(days=10)
        entrega = EntregaUniforme.objects.create(
            policial=self.policial,
            tipo_uniforme=self.tipo,
            data_entrega=data_entrega,
            quantidade=1
        )

        out = StringIO()
        call_command("check_uniform_deadlines", "--dry-run", stdout=out)

        self.assertEqual(AlertaUniforme.objects.filter(entrega=entrega).count(), 0)
        self.assertIn("[DRY-RUN] Criaria alerta para", out.getvalue())
        self.assertIn("[DRY-RUN] Simulação concluída", out.getvalue())
