from django.contrib.auth.models import User
from django.template.loader import get_template
from django.test import TestCase, Client
from django.urls import reverse

from .models import (
    CicloInventario,
    ConferenciaInventario,
    DivergenciaInventario,
    HistoricoCicloInventario,
    ItemInventario,
    MembroComissaoInventario,
)
from .workflow import (
    registrar_conferencia,
    encerrar_divergencia,
    usuario_pode_conferir,
    usuario_pode_gerir_ciclo,
)


class InventarioWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.conferente = User.objects.create_user(username='conferente', password='senha-segura')
        self.presidente = User.objects.create_user(username='presidente', password='senha-segura')
        self.usuario_sem_papel = User.objects.create_user(username='sem_papel', password='senha-segura')

        self.ciclo = CicloInventario.objects.create(
            titulo='Inventário de teste',
            termo_numero='TESTE/2026',
            ano=2026,
            semestre=1,
            status='EM_ANDAMENTO',
        )
        self.item = ItemInventario.objects.create(
            ciclo=self.ciclo,
            secao_subunidade='P/4',
            patrimonio='12345',
            numero_serie='SN-ORIGINAL-01',
            tipo_material='Notebook de teste',
            valor='100.00',
        )
        MembroComissaoInventario.objects.create(
            ciclo=self.ciclo,
            usuario=self.conferente,
            papel='CONFERENTE',
        )
        MembroComissaoInventario.objects.create(
            ciclo=self.ciclo,
            usuario=self.presidente,
            papel='PRESIDENTE',
        )

    def test_conferencia_cria_evento_e_atualiza_resumo_do_item(self):
        conferencia = registrar_conferencia(
            item=self.item,
            usuario=self.conferente,
            resultado='CONFIRMADO',
        )
        self.item.refresh_from_db()

        self.assertEqual(conferencia.resultado, 'CONFIRMADO')
        self.assertTrue(self.item.conferido)
        self.assertEqual(ConferenciaInventario.objects.count(), 1)

    def test_divergencia_e_criada_para_item_nao_localizado(self):
        registrar_conferencia(
            item=self.item,
            usuario=self.conferente,
            resultado='NAO_LOCALIZADO',
            situacao_fisica='NAO_LOCALIZADO',
            observacoes='Sala prevista estava vazia.',
        )
        self.item.refresh_from_db()

        self.assertFalse(self.item.conferido)
        self.assertEqual(DivergenciaInventario.objects.count(), 1)
        self.assertEqual(DivergenciaInventario.objects.first().tipo, 'NAO_LOCALIZADO')

    def test_conferencia_com_serie_divergente_cria_divergencia(self):
        conferencia = registrar_conferencia(
            item=self.item,
            usuario=self.conferente,
            resultado='SERIE_DIVERGENTE',
            numero_serie_encontrado='SN-ENCONTRADO-99',
            observacoes='Número gravado difere da planilha.',
        )
        self.assertEqual(conferencia.numero_serie_encontrado, 'SN-ENCONTRADO-99')
        self.assertEqual(DivergenciaInventario.objects.filter(tipo='SERIE_DIVERGENTE').count(), 1)

    def test_ciclo_homologado_nao_permite_conferencia(self):
        self.ciclo.status = 'HOMOLOGADO'
        self.ciclo.save(update_fields=['status'])

        with self.assertRaisesRegex(ValueError, 'homologado'):
            registrar_conferencia(
                item=self.item,
                usuario=self.conferente,
                resultado='CONFIRMADO',
            )

    def test_usuario_sem_permissao_nao_pode_conferir(self):
        with self.assertRaises(PermissionError):
            registrar_conferencia(
                item=self.item,
                usuario=self.usuario_sem_papel,
                resultado='CONFIRMADO',
            )

    def test_transicao_de_status_valida_cria_historico(self):
        self.ciclo.transicionar_para('EM_ANALISE', self.presidente, 'Fase de campo finalizada.')
        self.assertEqual(self.ciclo.status, 'EM_ANALISE')
        self.assertEqual(HistoricoCicloInventario.objects.count(), 1)
        hist = HistoricoCicloInventario.objects.first()
        self.assertEqual(hist.status_anterior, 'EM_ANDAMENTO')
        self.assertEqual(hist.status_novo, 'EM_ANALISE')
        self.assertEqual(hist.justificativa, 'Fase de campo finalizada.')

    def test_transicao_de_status_invalida_lanca_erro(self):
        with self.assertRaisesRegex(ValueError, 'Transição inválida'):
            self.ciclo.transicionar_para('HOMOLOGADO', self.presidente, 'Pulo direto inválido')

    def test_encerramento_de_divergencia_por_gestor(self):
        registrar_conferencia(
            item=self.item,
            usuario=self.conferente,
            resultado='NAO_LOCALIZADO',
            observacoes='Não encontrado no setor.',
        )
        divergencia = DivergenciaInventario.objects.first()
        self.assertEqual(divergencia.status, 'ABERTA')

        encerrar_divergencia(
            divergencia=divergencia,
            usuario=self.presidente,
            status='REGULARIZADA',
            resolucao='Localizado posteriormente na Seção de Manutenção.',
        )
        divergencia.refresh_from_db()
        self.assertEqual(divergencia.status, 'REGULARIZADA')
        self.assertEqual(divergencia.resolvido_por, self.presidente)
        self.assertIsNotNone(divergencia.resolvido_em)

    def test_encerramento_de_divergencia_por_usuario_sem_permissao_falha(self):
        registrar_conferencia(
            item=self.item,
            usuario=self.conferente,
            resultado='NAO_LOCALIZADO',
            observacoes='Não encontrado.',
        )
        divergencia = DivergenciaInventario.objects.first()

        with self.assertRaises(PermissionError):
            encerrar_divergencia(
                divergencia=divergencia,
                usuario=self.conferente,  # Apenas conferente, não presidente/supervisor
                status='REGULARIZADA',
                resolucao='Tentativa sem permissão',
            )

    def test_conferir_lote_bloqueado_quando_ciclo_homologado(self):
        self.ciclo.status = 'HOMOLOGADO'
        self.ciclo.save(update_fields=['status'])

        self.client.force_login(self.presidente)
        url = reverse('inventario:conferir_lote', args=[self.ciclo.id])
        response = self.client.post(url, {'acao': 'MARCAR_TODOS'})
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertFalse(self.item.conferido)

    def test_detalhe_ciclo_view_e_templates_renderizam(self):
        self.client.force_login(self.presidente)
        url = reverse('inventario:detalhe_ciclo', args=[self.ciclo.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ciclo.termo_numero)
        self.assertContains(response, 'Ciclo de Vida do Inventário')
        self.assertContains(response, 'Divergências e Inconsistências')
        self.assertContains(response, 'Comissão de Inventário')
        self.assertContains(response, 'Trilha de Auditoria')

    def test_template_base_compila(self):
        get_template('base.html')
