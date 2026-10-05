from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.test.client import RequestFactory
from administracao.context_processors import user_groups


class PermissoesMaterialConsumoTests(TestCase):
    """
    Testes de permissão de acesso ao módulo Material de Consumo (estoque/almoxarifado)
    e gerenciamento de permissões pela tela administrativa.
    """

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Garante a existência dos grupos
        self.grupo_materiais, _ = Group.objects.get_or_create(name='materiais')
        self.grupo_admin, _ = Group.objects.get_or_create(name='administracao')

        # Cria licença ativa para o ambiente de testes
        from licenciamento.license_core import LicenseManager
        from licenciamento.models import LicenseRecord
        import datetime
        token = LicenseManager.generate_token('baep-teste', '2º BAEP Testes', 365)
        is_valid, payload = LicenseManager.verify_token(token)
        expires_at = datetime.datetime.fromtimestamp(payload['exp'], tz=datetime.timezone.utc)
        issued_at = datetime.datetime.fromtimestamp(payload['iat'], tz=datetime.timezone.utc)
        LicenseRecord.objects.create(
            client_id='baep-teste',
            client_name='2º BAEP Testes',
            token_base64=token,
            issued_at=issued_at,
            expires_at=expires_at,
            is_active=True
        )

        # Usuário Comum (sem grupo inicial)
        self.user_comum = User.objects.create_user(
            username='sd_silva',
            password='senha_teste_123',
            first_name='Silva',
            last_name='Oliveira'
        )

        # Usuário Administrador (com grupo administracao)
        self.user_admin = User.objects.create_user(
            username='cap_gestor',
            password='senha_teste_123',
            first_name='Capitão',
            last_name='Gestor'
        )
        self.user_admin.groups.add(self.grupo_admin)

        # Superusuário (acesso irrestrito)
        self.superuser = User.objects.create_superuser(
            username='master_teste',
            password='senha_teste_123',
            email='master@baep.com.br'
        )

        self.url_dashboard_estoque = reverse('estoque:dashboard')
        self.url_listar_permissoes = reverse('administracao:listar_permissoes')
        self.url_gerenciar_permissoes = reverse('administracao:gerenciar_permissoes_usuario', args=[self.user_comum.id])

    def test_1_usuario_sem_grupo_materiais_recebe_403(self):
        """
        Teste 1: Usuário comum autenticado sem o Group 'materiais'
        deve receber HTTP 403 Forbidden ao acessar o módulo de Material de Consumo.
        """
        self.client.login(username='sd_silva', password='senha_teste_123')
        response = self.client.get(self.url_dashboard_estoque)
        self.assertEqual(response.status_code, 403)

    def test_2_apos_adicionar_grupo_materiais_acesso_liberado(self):
        """
        Teste 2: Após adicionar o usuário ao Group 'materiais', o acesso ao módulo
        Material de Consumo deve ser liberado (HTTP 200).
        """
        self.user_comum.groups.add(self.grupo_materiais)
        self.client.login(username='sd_silva', password='senha_teste_123')
        response = self.client.get(self.url_dashboard_estoque)
        self.assertEqual(response.status_code, 200)

    def test_3_superuser_sempre_tem_acesso_sem_grupo(self):
        """
        Teste 3: Superusuário sempre tem acesso liberado ao módulo,
        mesmo sem pertencer explicitamente ao Group 'materiais'.
        """
        self.assertFalse(self.superuser.groups.filter(name='materiais').exists())
        self.client.login(username='master_teste', password='senha_teste_123')
        response = self.client.get(self.url_dashboard_estoque)
        self.assertEqual(response.status_code, 200)

    def test_4_administrador_concede_e_revoga_permissao_via_post(self):
        """
        Teste 4: Administrador acessa a tela de gerenciamento de permissões do usuário,
        concede o grupo 'materiais' via POST e depois revoga, validando o impacto no acesso.
        """
        self.client.login(username='cap_gestor', password='senha_teste_123')

        # 4.1 GET na tela de formulário de permissões
        res_get = self.client.get(self.url_gerenciar_permissoes)
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, 'Material de Consumo')

        # 4.2 POST concedendo o grupo 'materiais'
        res_post_conceder = self.client.post(self.url_gerenciar_permissoes, {
            'grupos': ['materiais']
        })
        self.assertRedirects(res_post_conceder, self.url_listar_permissoes)
        self.assertTrue(self.user_comum.groups.filter(name='materiais').exists())

        # Verifica que o usuário agora acessa o estoque
        self.client.login(username='sd_silva', password='senha_teste_123')
        res_acesso_ok = self.client.get(self.url_dashboard_estoque)
        self.assertEqual(res_acesso_ok.status_code, 200)

        # 4.3 POST revogando o grupo 'materiais'
        self.client.login(username='cap_gestor', password='senha_teste_123')
        res_post_revogar = self.client.post(self.url_gerenciar_permissoes, {
            'grupos': []  # Nenhuma caixa marcada
        })
        self.assertRedirects(res_post_revogar, self.url_listar_permissoes)
        self.assertFalse(self.user_comum.groups.filter(name='materiais').exists())

        # Verifica que o usuário comum volta a receber 403
        self.client.login(username='sd_silva', password='senha_teste_123')
        res_acesso_bloqueado = self.client.get(self.url_dashboard_estoque)
        self.assertEqual(res_acesso_bloqueado.status_code, 403)

    def test_5_usuario_comum_bloqueado_em_telas_de_gerenciamento(self):
        """
        Teste 5: Usuário sem permissão de administração recebe 403
        ao tentar acessar as telas de gerenciamento de permissões.
        """
        self.client.login(username='sd_silva', password='senha_teste_123')

        res_lista = self.client.get(self.url_listar_permissoes)
        self.assertEqual(res_lista.status_code, 403)

        res_form = self.client.get(self.url_gerenciar_permissoes)
        self.assertEqual(res_form.status_code, 403)

    def test_6_context_processor_user_groups(self):
        """
        Teste 6: O context processor 'user_groups' injeta a lista correta
        de grupos do usuário autenticado no contexto.
        """
        request = self.factory.get('/')
        request.user = self.user_admin
        context = user_groups(request)
        self.assertIn('user_groups', context)
        self.assertIn('administracao', context['user_groups'])

    def test_admin_nao_pode_remover_proprio_group_administracao(self):
        """
        Teste 7: Administrador não pode remover seu próprio group 'administracao'.
        Ao tentar fazer isso via POST em seu próprio ID, o grupo permanece
        e uma mensagem de erro é exibida.
        """
        self.client.login(username='cap_gestor', password='senha_teste_123')
        url_proprio_gerenciar = reverse('administracao:gerenciar_permissoes_usuario', args=[self.user_admin.id])

        # POST tentando remover o grupo 'administracao' (enviando grupos vazio)
        response = self.client.post(url_proprio_gerenciar, {
            'grupos': []
        }, follow=True)

        self.assertRedirects(response, self.url_listar_permissoes)
        # Assert: group permanece
        self.user_admin.refresh_from_db()
        self.assertTrue(self.user_admin.groups.filter(name='administracao').exists())
        # Assert: mensagem de erro presente
        messages_list = list(response.context['messages'])
        self.assertTrue(any("Você não pode remover sua própria permissão de administração." in m.message for m in messages_list))

    def test_permissoes_do_master_nao_podem_ser_alteradas(self):
        """
        Teste 8: Tentativa de alterar permissões do usuário master via POST
        é bloqueada, mantendo os grupos inalterados e exibindo mensagem de erro.
        """
        # Garante usuário master
        user_master, _ = User.objects.get_or_create(username='master')
        user_master.set_password('senha_teste_123')
        user_master.is_superuser = True
        user_master.is_staff = True
        user_master.save()

        # Guarda grupos anteriores do master
        grupos_antes = set(user_master.groups.values_list('name', flat=True))

        self.client.login(username='cap_gestor', password='senha_teste_123')
        url_master_gerenciar = reverse('administracao:gerenciar_permissoes_usuario', args=[user_master.id])

        # POST tentando adicionar grupo ou alterar permissões do master
        response = self.client.post(url_master_gerenciar, {
            'grupos': ['materiais', 'inventario']
        }, follow=True)

        self.assertRedirects(response, self.url_listar_permissoes)
        # Assert: permissões inalteradas
        user_master.refresh_from_db()
        grupos_depois = set(user_master.groups.values_list('name', flat=True))
        self.assertEqual(grupos_antes, grupos_depois)
        # Assert: mensagem de erro presente
        messages_list = list(response.context['messages'])
        self.assertTrue(any("As permissões do usuário master não podem ser alteradas." in m.message for m in messages_list))


class PermissoesInventarioTests(TestCase):
    """
    Testes de permissão de acesso ao módulo Inventário Semestral (Conferência Cega)
    e gerenciamento de permissões pela tela administrativa.
    """

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Garante a existência dos grupos
        self.grupo_inventario, _ = Group.objects.get_or_create(name='inventario')
        self.grupo_admin, _ = Group.objects.get_or_create(name='administracao')

        # Cria licença ativa para o ambiente de testes
        from licenciamento.license_core import LicenseManager
        from licenciamento.models import LicenseRecord
        import datetime
        token = LicenseManager.generate_token('baep-teste', '2º BAEP Testes', 365)
        is_valid, payload = LicenseManager.verify_token(token)
        expires_at = datetime.datetime.fromtimestamp(payload['exp'], tz=datetime.timezone.utc)
        issued_at = datetime.datetime.fromtimestamp(payload['iat'], tz=datetime.timezone.utc)
        LicenseRecord.objects.create(
            client_id='baep-teste',
            client_name='2º BAEP Testes',
            token_base64=token,
            issued_at=issued_at,
            expires_at=expires_at,
            is_active=True
        )

        # Usuário Comum (sem grupo inicial)
        self.user_comum = User.objects.create_user(
            username='cb_souza',
            password='senha_teste_123',
            first_name='Souza',
            last_name='Silva'
        )

        # Usuário Administrador (com grupo administracao)
        self.user_admin = User.objects.create_user(
            username='ten_gestor',
            password='senha_teste_123',
            first_name='Tenente',
            last_name='Gestor'
        )
        self.user_admin.groups.add(self.grupo_admin)

        # Superusuário (acesso irrestrito)
        self.superuser = User.objects.create_superuser(
            username='coronel_master',
            password='senha_teste_123',
            email='master@baep.com.br'
        )

        self.url_dashboard_inventario = reverse('inventario:dashboard')
        self.url_lista_ciclos = reverse('inventario:lista_ciclos')
        self.url_novo_ciclo = reverse('inventario:novo_ciclo')
        self.url_importar = reverse('inventario:importar')
        self.url_listar_permissoes = reverse('administracao:listar_permissoes')
        self.url_gerenciar_permissoes = reverse('administracao:gerenciar_permissoes_usuario', args=[self.user_comum.id])

    def test_1_usuario_sem_grupo_inventario_recebe_403(self):
        """
        Teste 1: Usuário comum autenticado sem o Group 'inventario'
        deve receber HTTP 403 Forbidden ao acessar o dashboard de Inventário.
        """
        self.client.login(username='cb_souza', password='senha_teste_123')
        response = self.client.get(self.url_dashboard_inventario)
        self.assertEqual(response.status_code, 403)

    def test_2_apos_adicionar_grupo_inventario_acesso_liberado(self):
        """
        Teste 2: Após adicionar o usuário ao Group 'inventario', o acesso
        ao dashboard deve ser liberado (HTTP 200).
        """
        self.user_comum.groups.add(self.grupo_inventario)
        self.client.login(username='cb_souza', password='senha_teste_123')
        response = self.client.get(self.url_dashboard_inventario)
        self.assertEqual(response.status_code, 200)

    def test_3_superuser_sempre_tem_acesso_sem_grupo(self):
        """
        Teste 3: Superusuário sempre tem acesso liberado ao módulo de Inventário,
        mesmo sem pertencer explicitamente ao Group 'inventario'.
        """
        self.assertFalse(self.superuser.groups.filter(name='inventario').exists())
        self.client.login(username='coronel_master', password='senha_teste_123')
        response = self.client.get(self.url_dashboard_inventario)
        self.assertEqual(response.status_code, 200)

    def test_4_administrador_concede_e_revoga_permissao_inventario_via_post(self):
        """
        Teste 4: Administrador acessa a tela de gerenciamento de permissões do usuário,
        vê a opção 'Inventário Semestral', concede o grupo 'inventario' via POST e depois revoga.
        """
        self.client.login(username='ten_gestor', password='senha_teste_123')

        # 4.1 GET na tela de formulário de permissões (deve conter o módulo Inventário Semestral)
        res_get = self.client.get(self.url_gerenciar_permissoes)
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, 'Inventário Semestral')

        # 4.2 POST concedendo o grupo 'inventario'
        res_post_conceder = self.client.post(self.url_gerenciar_permissoes, {
            'grupos': ['inventario']
        })
        self.assertRedirects(res_post_conceder, self.url_listar_permissoes)
        self.assertTrue(self.user_comum.groups.filter(name='inventario').exists())

        # Verifica que o usuário agora acessa o inventário
        self.client.login(username='cb_souza', password='senha_teste_123')
        res_acesso_ok = self.client.get(self.url_dashboard_inventario)
        self.assertEqual(res_acesso_ok.status_code, 200)

        # 4.3 POST revogando o grupo 'inventario'
        self.client.login(username='ten_gestor', password='senha_teste_123')
        res_post_revogar = self.client.post(self.url_gerenciar_permissoes, {
            'grupos': []
        })
        self.assertRedirects(res_post_revogar, self.url_listar_permissoes)
        self.assertFalse(self.user_comum.groups.filter(name='inventario').exists())

        # Verifica que o usuário comum volta a receber 403
        self.client.login(username='cb_souza', password='senha_teste_123')
        res_acesso_bloqueado = self.client.get(self.url_dashboard_inventario)
        self.assertEqual(res_acesso_bloqueado.status_code, 403)

    def test_5_todas_views_inventario_bloqueadas_sem_permissao(self):
        """
        Teste 5: Usuário autenticado sem o grupo 'inventario' recebe 403
        em múltiplas rotas do módulo de Inventário.
        """
        self.client.login(username='cb_souza', password='senha_teste_123')

        for url in [self.url_lista_ciclos, self.url_novo_ciclo, self.url_importar]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, f"Rota {url} não retornou 403!")

    def test_6_context_processor_user_groups_com_inventario(self):
        """
        Teste 6: O context processor 'user_groups' inclui 'inventario'
        quando o usuário pertence a este grupo.
        """
        self.user_comum.groups.add(self.grupo_inventario)
        request = self.factory.get('/')
        request.user = self.user_comum
        context = user_groups(request)
        self.assertIn('user_groups', context)
        self.assertIn('inventario', context['user_groups'])

