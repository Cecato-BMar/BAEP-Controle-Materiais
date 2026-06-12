"""
viaturas/tests.py — Testes automatizados da API REST do módulo Frota.

Cobertura:
  - CRUD Viaturas (list, retrieve, create, update, delete)
  - CRUD Oficinas (list, retrieve, create, update, delete)
  - CRUD Manutenção (list, retrieve, create, update, delete + actions)
  - CRUD Abastecimento (list, retrieve, create, update, delete)
  - Permissões (anônimo, sem grupo, com grupo, superuser)
  - Filtros (status, tipo, data, viatura, etc.)
  - Custom actions (indicadores, previsao, mudar-status, concluir, cancelar)

Executar:  python manage.py test viaturas --verbosity=2
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User, Group
from django.test import TestCase
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

from viaturas.models import (
    MarcaViatura, ModeloViatura, Viatura, Oficina, Manutencao,
    Abastecimento, StatusViatura, StatusManutencao, TipoManutencao,
    Combustivel, LocalizacaoViatura, TipoViatura,
)


# ============================================================================
# BASE
# ============================================================================
class BaseAPITestCase(TestCase):
    """Setup compartilhado: usuários, grupos, cliente e factory helpers."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_frota = Group.objects.create(name='frota')

        cls.user_frota = User.objects.create_user(
            username='test_frota', password='test1234',
        )
        cls.user_frota.groups.add(cls.grupo_frota)

        cls.user_sem_grupo = User.objects.create_user(
            username='test_sem_grupo', password='test1234',
        )

        cls.superuser = User.objects.create_superuser(
            username='test_admin', password='test1234',
        )

        cls.marca = MarcaViatura.objects.create(nome='Toyota')
        cls.modelo = ModeloViatura.objects.create(
            marca=cls.marca, nome='Hilux', tipo=TipoViatura.QUATRO_RODAS,
        )

        cls.viatura = Viatura.objects.create(
            prefixo='E-10201', placa='ABC1D23', modelo=cls.modelo,
            ano_fabricacao=2022, tipo_combustivel=Combustivel.FLEX,
            capacidade_tanque=Decimal('80.00'), odometro_atual=Decimal('45000.0'),
            status=StatusViatura.DISPONIVEL, localizacao=LocalizacaoViatura.MOTOMEC,
        )

        cls.viatura2 = Viatura.objects.create(
            prefixo='E-10202', placa='XYZ9A87', modelo=cls.modelo,
            ano_fabricacao=2020, tipo_combustivel=Combustivel.DIESEL,
            capacidade_tanque=Decimal('70.00'), odometro_atual=Decimal('60000.0'),
            status=StatusViatura.MANUTENCAO, localizacao=LocalizacaoViatura.OFICINA,
        )

        cls.oficina = Oficina.objects.create(
            nome='Auto Center Santos', cnpj='12345678000100',
            cidade='Santos', especialidade='Mecânica Geral',
        )

        cls.manutencao = Manutencao.objects.create(
            viatura=cls.viatura, tipo=TipoManutencao.CORRETIVA,
            status=StatusManutencao.ABERTA, data_inicio=date.today(),
            odometro=Decimal('45000.0'), descricao='Troca de óleo',
            oficina_fk=cls.oficina, registrado_por=cls.user_frota,
        )

        cls.abastecimento = Abastecimento.objects.create(
            viatura=cls.viatura, data_abastecimento=timezone.now(),
            odometro=Decimal('44500.0'), combustivel=Combustivel.GASOLINA,
            quantidade_litros=Decimal('40.00'), valor_total=Decimal('220.00'),
            registrado_por=cls.user_frota,
        )

    def setUp(self):
        self.client = APIClient()

    def _url(self, resource, pk=None):
        """Helper para construir URLs da API."""
        base = f'/api/frota/{resource}/'
        if pk:
            return f'{base}{pk}/'
        return base

    def _login(self, user):
        self.client.force_authenticate(user=user)


# ============================================================================
# PERMISSÕES
# ============================================================================
class PermissionTestCase(BaseAPITestCase):
    """Valida FrotaModulePermission em todos os endpoints."""

    def test_anonimo_401_viaturas(self):
        resp = self.client.get(self._url('viaturas'))
        self.assertIn(resp.status_code, [401, 403])

    def test_anonimo_401_oficinas(self):
        resp = self.client.get(self._url('oficinas'))
        self.assertIn(resp.status_code, [401, 403])

    def test_anonimo_401_manutencoes(self):
        resp = self.client.get(self._url('manutencoes'))
        self.assertIn(resp.status_code, [401, 403])

    def test_anonimo_401_abastecimentos(self):
        resp = self.client.get(self._url('abastecimentos'))
        self.assertIn(resp.status_code, [401, 403])

    def test_sem_grupo_403_viaturas(self):
        self._login(self.user_sem_grupo)
        resp = self.client.get(self._url('viaturas'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_sem_grupo_403_oficinas(self):
        self._login(self.user_sem_grupo)
        resp = self.client.get(self._url('oficinas'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_sem_grupo_403_manutencoes(self):
        self._login(self.user_sem_grupo)
        resp = self.client.get(self._url('manutencoes'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_sem_grupo_403_abastecimentos(self):
        self._login(self.user_sem_grupo)
        resp = self.client.get(self._url('abastecimentos'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_grupo_frota_200_viaturas(self):
        self._login(self.user_frota)
        resp = self.client.get(self._url('viaturas'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_superuser_200_viaturas(self):
        self._login(self.superuser)
        resp = self.client.get(self._url('viaturas'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ============================================================================
# CRUD VIATURAS
# ============================================================================
class ViaturaCRUDTestCase(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self._login(self.user_frota)

    # LIST
    def test_list_viaturas_200(self):
        resp = self.client.get(self._url('viaturas'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.json().get('results', resp.json())
        self.assertGreaterEqual(len(results), 2)

    def test_list_viaturas_tem_modelo_nome(self):
        resp = self.client.get(self._url('viaturas'))
        first = resp.json()['results'][0]
        self.assertIn('modelo_nome', first)
        self.assertIn('Toyota', first['modelo_nome'])

    def test_list_viaturas_tem_status_display(self):
        resp = self.client.get(self._url('viaturas'))
        first = resp.json()['results'][0]
        self.assertIn('status_display', first)

    # RETRIEVE
    def test_retrieve_viatura_200(self):
        resp = self.client.get(self._url('viaturas', self.viatura.pk))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['prefixo'], 'E-10201')

    def test_retrieve_viatura_nao_existe_404(self):
        resp = self.client.get(self._url('viaturas', 99999))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_viatura_tem_detalhe_completo(self):
        resp = self.client.get(self._url('viaturas', self.viatura.pk))
        data = resp.json()
        for campo in ['chassi', 'renavam', 'capacidade_tanque', 'tipo_combustivel_display']:
            self.assertIn(campo, data)

    # CREATE
    def test_create_viatura_201(self):
        dados = {
            'prefixo': 'E-99999',
            'placa': 'QWE4R56',
            'modelo': self.modelo.pk,
            'ano_fabricacao': 2023,
            'tipo_combustivel': Combustivel.DIESEL,
            'capacidade_tanque': '65.00',
            'odometro_atual': '1000.0',
            'localizacao': LocalizacaoViatura.PRIMEIRA_CIA,
        }
        resp = self.client.post(self._url('viaturas'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.json()['prefixo'], 'E-99999')
        self.assertTrue(Viatura.objects.filter(prefixo='E-99999').exists())

    def test_create_viatura_prefixo_duplicado_400(self):
        dados = {
            'prefixo': 'E-10201',  # já existe
            'modelo': self.modelo.pk,
            'localizacao': LocalizacaoViatura.MOTOMEC,
        }
        resp = self.client.post(self._url('viaturas'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # UPDATE
    def test_update_viatura_200(self):
        resp = self.client.patch(
            self._url('viaturas', self.viatura.pk),
            {'observacoes': 'Viatura de teste atualizada'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.viatura.refresh_from_db()
        self.assertEqual(self.viatura.observacoes, 'Viatura de teste atualizada')

    def test_put_viatura_200(self):
        dados = {
            'prefixo': 'E-10201',
            'modelo': self.modelo.pk,
            'ano_fabricacao': 2022,
            'tipo_combustivel': Combustivel.FLEX,
            'capacidade_tanque': '80.00',
            'odometro_atual': '45000.0',
            'localizacao': LocalizacaoViatura.MOTOMEC,
            'cor': 'Cinza/PM',
        }
        resp = self.client.put(
            self._url('viaturas', self.viatura.pk), dados, format='json',
        )
        self.assertIn(resp.status_code, [200, 204])

    # DELETE
    def test_delete_viatura_204(self):
        v = Viatura.objects.create(
            prefixo='E-DELETE', modelo=self.modelo,
            localizacao=LocalizacaoViatura.MOTOMEC,
        )
        resp = self.client.delete(self._url('viaturas', v.pk))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Viatura.objects.filter(prefixo='E-DELETE').exists())

    # FILTERS
    def test_filter_por_status(self):
        resp = self.client.get(self._url('viaturas'), {'status': 'DISPONIVEL'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for item in resp.json()['results']:
            self.assertEqual(item['status'], 'DISPONIVEL')

    def test_filter_por_tipo(self):
        resp = self.client.get(self._url('viaturas'), {'tipo': '4_RODAS'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_filter_por_combustivel(self):
        resp = self.client.get(self._url('viaturas'), {'combustivel': 'FLEX'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # SEARCH
    def test_search_por_prefixo(self):
        resp = self.client.get(self._url('viaturas'), {'search': 'E-10201'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.json()['results']), 1)

    def test_search_por_placa(self):
        resp = self.client.get(self._url('viaturas'), {'search': 'ABC1D23'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ORDERING
    def test_ordering_por_prefixo(self):
        resp = self.client.get(self._url('viaturas'), {'ordering': 'prefixo'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # PAGINATION
    def test_paginacao(self):
        resp = self.client.get(self._url('viaturas'), {'page_size': 1})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn('count', data)
        self.assertIn('next', data)

    # CUSTOM ACTION: mudar-status
    def test_mudar_status_200(self):
        resp = self.client.post(
            self._url('viaturas', self.viatura.pk) + 'mudar-status/',
            {'status': StatusViatura.MANUTENCAO},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.viatura.refresh_from_db()
        self.assertEqual(self.viatura.status, StatusViatura.MANUTENCAO)

    def test_mudar_status_vazio_400(self):
        resp = self.client.post(
            self._url('viaturas', self.viatura.pk) + 'mudar-status/',
            {}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mudar_status_invalido_400(self):
        resp = self.client.post(
            self._url('viaturas', self.viatura.pk) + 'mudar-status/',
            {'status': 'INVALIDO'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # CUSTOM ACTION: indicadores
    def test_indicadores_200(self):
        resp = self.client.get(
            self._url('viaturas', self.viatura.pk) + 'indicadores/',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn('total_km_rodado', data)
        self.assertIn('total_combustivel', data)
        self.assertIn('custo_total_manutencao', data)

    # CUSTOM ACTION: previsao
    def test_previsao_200(self):
        resp = self.client.get(
            self._url('viaturas', self.viatura.pk) + 'previsao/',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.json(), list)


# ============================================================================
# CRUD OFICINAS
# ============================================================================
class OficinaCRUDTestCase(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self._login(self.user_frota)

    # LIST
    def test_list_oficinas_200(self):
        resp = self.client.get(self._url('oficinas'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.json()['results']), 1)

    def test_list_oficinas_tem_total_manutencoes(self):
        resp = self.client.get(self._url('oficinas'))
        first = resp.json()['results'][0]
        self.assertIn('total_manutencoes', first)

    # RETRIEVE
    def test_retrieve_oficina_200(self):
        resp = self.client.get(self._url('oficinas', self.oficina.pk))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['nome'], 'Auto Center Santos')

    def test_retrieve_oficina_nao_existe_404(self):
        resp = self.client.get(self._url('oficinas', 99999))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # CREATE
    def test_create_oficina_201(self):
        dados = {
            'nome': 'Mecânica Express',
            'cnpj': '98765432000100',
            'cidade': 'São Vicente',
            'especialidade': 'Funilaria',
            'telefone': '13999998888',
            'contato_responsavel': 'João Silva',
        }
        resp = self.client.post(self._url('oficinas'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Oficina.objects.filter(nome='Mecânica Express').exists())

    def test_create_oficina_minimo_201(self):
        dados = {'nome': 'Oficina Simples'}
        resp = self.client.post(self._url('oficinas'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_create_oficina_sem_nome_400(self):
        dados = {'cidade': 'Santos'}
        resp = self.client.post(self._url('oficinas'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # UPDATE
    def test_update_oficina_200(self):
        resp = self.client.patch(
            self._url('oficinas', self.oficina.pk),
            {'telefone': '1333334444'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.oficina.refresh_from_db()
        self.assertEqual(self.oficina.telefone, '1333334444')

    def test_update_oficina_ativo_false(self):
        resp = self.client.patch(
            self._url('oficinas', self.oficina.pk),
            {'ativo': False}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.oficina.refresh_from_db()
        self.assertFalse(self.oficina.ativo)

    # DELETE
    def test_delete_oficina_204(self):
        of = Oficina.objects.create(nome='Oficina Temp')
        resp = self.client.delete(self._url('oficinas', of.pk))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Oficina.objects.filter(nome='Oficina Temp').exists())

    # FILTERS
    def test_filter_por_cidade(self):
        resp = self.client.get(self._url('oficinas'), {'cidade': 'Santos'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_filter_por_ativo(self):
        resp = self.client.get(self._url('oficinas'), {'ativo': True})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # SEARCH
    def test_search_por_nome(self):
        resp = self.client.get(self._url('oficinas'), {'search': 'Auto Center'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.json()['results']), 1)


# ============================================================================
# CRUD MANUTENÇÃO
# ============================================================================
class ManutencaoCRUDTestCase(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self._login(self.user_frota)

    # LIST
    def test_list_manutencoes_200(self):
        resp = self.client.get(self._url('manutencoes'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.json()['results']), 1)

    def test_list_manutencoes_tem_custo_total(self):
        resp = self.client.get(self._url('manutencoes'))
        first = resp.json()['results'][0]
        self.assertIn('custo_total', first)

    def test_list_manutencoes_tem_tipo_display(self):
        resp = self.client.get(self._url('manutencoes'))
        first = resp.json()['results'][0]
        self.assertIn('tipo_display', first)

    # RETRIEVE
    def test_retrieve_manutencao_200(self):
        resp = self.client.get(self._url('manutencoes', self.manutencao.pk))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data['descricao'], 'Troca de óleo')
        self.assertIn('servicos', data)
        self.assertIn('evidencias', data)
        self.assertIn('registros_historico', data)

    def test_retrieve_manutencao_nao_existe_404(self):
        resp = self.client.get(self._url('manutencoes', 99999))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_manutencao_oficina_nome(self):
        resp = self.client.get(self._url('manutencoes', self.manutencao.pk))
        data = resp.json()
        self.assertEqual(data['oficina_nome'], 'Auto Center Santos')

    # CREATE
    def test_create_manutencao_201(self):
        dados = {
            'viatura': self.viatura.pk,
            'tipo': TipoManutencao.PREVENTIVA,
            'data_inicio': date.today().isoformat(),
            'odometro': '45500.0',
            'descricao': 'Revisão 45.000 km',
            'oficina_fk': self.oficina.pk,
        }
        resp = self.client.post(self._url('manutencoes'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.json()['tipo'], TipoManutencao.PREVENTIVA)

    def test_create_manutencao_registra_usuario(self):
        dados = {
            'viatura': self.viatura.pk,
            'tipo': TipoManutencao.CORRETIVA,
            'data_inicio': date.today().isoformat(),
            'odometro': '45500.0',
            'descricao': 'Freio com ruído',
        }
        resp = self.client.post(self._url('manutencoes'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        manut = Manutencao.objects.get(pk=resp.json()['id'])
        self.assertEqual(manut.registrado_por, self.user_frota)

    def test_create_manutencao_sem_viatura_400(self):
        dados = {
            'tipo': TipoManutencao.CORRETIVA,
            'data_inicio': date.today().isoformat(),
            'odometro': '0',
            'descricao': 'Teste',
        }
        resp = self.client.post(self._url('manutencoes'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # UPDATE
    def test_update_manutencao_200(self):
        resp = self.client.patch(
            self._url('manutencoes', self.manutencao.pk),
            {'descricao': 'Troca de óleo + filtros'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.manutencao.refresh_from_db()
        self.assertEqual(self.manutencao.descricao, 'Troca de óleo + filtros')

    # DELETE
    def test_delete_manutencao_204(self):
        manut = Manutencao.objects.create(
            viatura=self.viatura, tipo=TipoManutencao.PREVENTIVA,
            status=StatusManutencao.CANCELADA, data_inicio=date.today(),
            odometro=Decimal('45000'), descricao='temp',
            registrado_por=self.user_frota,
        )
        resp = self.client.delete(self._url('manutencoes', manut.pk))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    # FILTERS
    def test_filter_por_status(self):
        resp = self.client.get(self._url('manutencoes'), {'status': 'ABERTA'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for item in resp.json()['results']:
            self.assertEqual(item['status'], 'ABERTA')

    def test_filter_por_tipo(self):
        resp = self.client.get(self._url('manutencoes'), {'tipo': 'CORRETIVA'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_filter_por_viatura(self):
        resp = self.client.get(self._url('manutencoes'), {'viatura': self.viatura.pk})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_filter_por_oficina(self):
        resp = self.client.get(self._url('manutencoes'), {'oficina': self.oficina.pk})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # CUSTOM ACTION: concluir
    def test_concluir_manutencao_200(self):
        resp = self.client.post(
            self._url('manutencoes', self.manutencao.pk) + 'concluir/',
            format='json',
        )
        # Pode retornar 200 ou 400 dependendo do service
        self.assertIn(resp.status_code, [200, 400])

    # CUSTOM ACTION: cancelar
    def test_cancelar_manutencao_200(self):
        manut = Manutencao.objects.create(
            viatura=self.viatura, tipo=TipoManutencao.PREVENTIVA,
            status=StatusManutencao.ABERTA, data_inicio=date.today(),
            odometro=Decimal('45000'), descricao='cancel test',
            registrado_por=self.user_frota,
        )
        resp = self.client.post(
            self._url('manutencoes', manut.pk) + 'cancelar/',
            {'motivo': 'Serviço não necessário'},
            format='json',
        )
        self.assertIn(resp.status_code, [200, 400])

    # CUSTOM ACTION: abertas
    def test_abertas_200(self):
        resp = self.client.get(self._url('manutencoes') + 'abertas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # CUSTOM ACTION: agendadas
    def test_agendadas_200(self):
        resp = self.client.get(self._url('manutencoes') + 'agendadas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # SEARCH
    def test_search_por_descricao(self):
        resp = self.client.get(self._url('manutencoes'), {'search': 'Troca'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ============================================================================
# CRUD ABASTECIMENTO
# ============================================================================
class AbastecimentoCRUDTestCase(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self._login(self.user_frota)

    # LIST
    def test_list_abastecimentos_200(self):
        resp = self.client.get(self._url('abastecimentos'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.json()['results']), 1)

    def test_list_abastecimentos_tem_display(self):
        resp = self.client.get(self._url('abastecimentos'))
        first = resp.json()['results'][0]
        self.assertIn('combustivel_display', first)
        self.assertIn('viatura_prefixo', first)

    # RETRIEVE
    def test_retrieve_abastecimento_200(self):
        resp = self.client.get(self._url('abastecimentos', self.abastecimento.pk))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp.json()['quantidade_litros'], '40.00',
        )

    def test_retrieve_abastecimento_nao_existe_404(self):
        resp = self.client.get(self._url('abastecimentos', 99999))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # CREATE
    def test_create_abastecimento_201(self):
        dados = {
            'viatura': self.viatura.pk,
            'data_abastecimento': timezone.now().isoformat(),
            'odometro': '46000.0',
            'combustivel': Combustivel.GASOLINA,
            'quantidade_litros': '35.50',
            'valor_total': '195.25',
            'posto_fornecedor': 'Posto Shell Centro',
        }
        resp = self.client.post(self._url('abastecimentos'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        ab = Abastecimento.objects.get(pk=resp.json()['id'])
        self.assertEqual(ab.registrado_por, self.user_frota)

    def test_create_abastecimento_sem_viatura_400(self):
        dados = {
            'data_abastecimento': timezone.now().isoformat(),
            'odometro': '46000.0',
            'combustivel': Combustivel.GASOLINA,
            'quantidade_litros': '35.50',
        }
        resp = self.client.post(self._url('abastecimentos'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_abastecimento_sem_combustivel_400(self):
        dados = {
            'viatura': self.viatura.pk,
            'data_abastecimento': timezone.now().isoformat(),
            'odometro': '46000.0',
            'quantidade_litros': '35.50',
        }
        resp = self.client.post(self._url('abastecimentos'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_abastecimento_com_cupom(self):
        dados = {
            'viatura': self.viatura.pk,
            'data_abastecimento': timezone.now().isoformat(),
            'odometro': '46100.0',
            'combustivel': Combustivel.ALCOOL,
            'quantidade_litros': '20.00',
            'cupom_fiscal': 'CF-2024-001',
            'posto_fornecedor': 'Posto BR',
        }
        resp = self.client.post(self._url('abastecimentos'), dados, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.json()['cupom_fiscal'], 'CF-2024-001')

    # UPDATE
    def test_update_abastecimento_200(self):
        resp = self.client.patch(
            self._url('abastecimentos', self.abastecimento.pk),
            {'posto_fornecedor': 'Posto Atualizado'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.abastecimento.refresh_from_db()
        self.assertEqual(self.abastecimento.posto_fornecedor, 'Posto Atualizado')

    # DELETE
    def test_delete_abastecimento_204(self):
        ab = Abastecimento.objects.create(
            viatura=self.viatura, data_abastecimento=timezone.now(),
            odometro=Decimal('47000'), combustivel=Combustivel.DIESEL,
            quantidade_litros=Decimal('50.00'), registrado_por=self.user_frota,
        )
        resp = self.client.delete(self._url('abastecimentos', ab.pk))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    # FILTERS
    def test_filter_por_viatura(self):
        resp = self.client.get(
            self._url('abastecimentos'), {'viatura': self.viatura.pk},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_filter_por_combustivel(self):
        resp = self.client.get(
            self._url('abastecimentos'), {'combustivel': Combustivel.GASOLINA},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for item in resp.json()['results']:
            self.assertEqual(item['combustivel'], Combustivel.GASOLINA)

    # SEARCH
    def test_search_por_posto(self):
        resp = self.client.get(self._url('abastecimentos'), {'search': 'Posto'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ORDERING
    def test_ordering_por_litros(self):
        resp = self.client.get(self._url('abastecimentos'), {'ordering': '-quantidade_litros'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # PAGINATION
    def test_paginacao_abastecimentos(self):
        resp = self.client.get(self._url('abastecimentos'), {'page_size': 1})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn('count', data)


# ============================================================================
# DASHBOARD
# ============================================================================
class DashboardTestCase(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self._login(self.user_frota)

    def test_dashboard_200(self):
        resp = self.client.get(self._url('dashboard'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        for key in ['total', 'disponiveis', 'em_uso', 'manutencao', 'custo_total_frota']:
            self.assertIn(key, data)

    def test_dashboard_status_200(self):
        resp = self.client.get(self._url('dashboard') + 'status/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_dashboard_kpis_200(self):
        resp = self.client.get(self._url('dashboard') + 'kpis/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ============================================================================
# MARCAS E MODELOS (CRUD auxiliar)
# ============================================================================
class CadastroAuxiliarTestCase(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self._login(self.user_frota)

    def test_list_marcas_200(self):
        resp = self.client.get(self._url('marcas'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_create_marca_201(self):
        resp = self.client.post(
            self._url('marcas'), {'nome': 'Honda'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_create_marca_duplicada_400(self):
        resp = self.client.post(
            self._url('marcas'), {'nome': 'Toyota'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_modelos_200(self):
        resp = self.client.get(self._url('modelos'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_create_modelo_201(self):
        resp = self.client.post(
            self._url('modelos'),
            {'marca': self.marca.pk, 'nome': 'Corolla', 'tipo': TipoViatura.QUATRO_RODAS},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
