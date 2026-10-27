import datetime
from unittest.mock import patch
from django.contrib.auth.models import Group, User
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from estoque.models import Categoria, Produto
from licenciamento.license_core import LicenseManager
from licenciamento.models import LicenseRecord


class CriarProdutoInlineViewTests(TestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.url = reverse("estoque:criar_produto_inline")

        # Garante licença ativa para os testes HTTP (LicenseCheckMiddleware)
        token = LicenseManager.generate_token("baep-teste", "2º BAEP Testes", 365)
        is_valid, payload = LicenseManager.verify_token(token)
        expires_at = datetime.datetime.fromtimestamp(payload["exp"], tz=datetime.timezone.utc)
        issued_at = datetime.datetime.fromtimestamp(payload["iat"], tz=datetime.timezone.utc)
        LicenseRecord.objects.create(
            client_id="baep-teste",
            client_name="2º BAEP Testes",
            token_base64=token,
            issued_at=issued_at,
            expires_at=expires_at,
            is_active=True,
        )

        # Usuários
        self.user = User.objects.create_user(username="operador_inline", password="password123")
        self.grupo_materiais, _ = Group.objects.get_or_create(name="materiais")
        self.user.groups.add(self.grupo_materiais)

        self.user_sem_permissao = User.objects.create_user(
            username="sem_permissao_inline", password="password123"
        )

        # Categoria default para testes
        self.categoria = Categoria.objects.create(
            codigo="GEN-ALIM", nome="Gêneros Alimentícios"
        )

    def test_rejeita_sem_login(self):
        response = self.client.post(self.url, {"nome": "Teste", "categoria_id": self.categoria.pk})
        self.assertEqual(response.status_code, 302)

    def test_rejeita_sem_permissao(self):
        self.client.force_login(self.user_sem_permissao)
        response = self.client.post(self.url, {"nome": "Teste", "categoria_id": self.categoria.pk})
        self.assertEqual(response.status_code, 403)

    def test_rejeita_nome_vazio(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"nome": "   ", "categoria_id": self.categoria.pk})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Nome é obrigatório.")

    def test_rejeita_sem_categoria(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"nome": "Margarina"})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Categoria é obrigatória.")

    def test_rejeita_categoria_invalida(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"nome": "Margarina", "categoria_id": 99999})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Categoria inválida.")

    def test_sucesso_gera_mat_001(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            "nome": "Margarina Becel 500g",
            "categoria_id": self.categoria.pk,
            "codigo_cat_mat": "00459577-7",
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["codigo"], "MAT-001")
        self.assertEqual(data["nome"], "Margarina Becel 500g")
        self.assertEqual(data["codigo_cat_mat"], "00459577-7")

        produto = Produto.objects.get(pk=data["id"])
        self.assertEqual(produto.codigo, "MAT-001")
        self.assertEqual(produto.status, "ATIVO")
        self.assertEqual(produto.criado_por, self.user)

    def test_sucesso_gera_mat_002_apos_mat_001(self):
        self.client.force_login(self.user)
        # Primeiro produto
        self.client.post(self.url, {
            "nome": "Primeiro",
            "categoria_id": self.categoria.pk,
        })
        # Segundo produto
        response2 = self.client.post(self.url, {
            "nome": "Segundo",
            "categoria_id": self.categoria.pk,
        })
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertEqual(data2["codigo"], "MAT-002")

    def test_codigo_cat_mat_salvo_corretamente(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            "nome": "Açúcar 1kg",
            "categoria_id": self.categoria.pk,
            "codigo_cat_mat": "00123456-7",
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["codigo_cat_mat"], "00123456-7")
        produto = Produto.objects.get(pk=data["id"])
        self.assertEqual(produto.codigo_cat_mat, "00123456-7")

    def test_retry_em_colisao_de_codigo(self):
        self.client.force_login(self.user)
        original_create = Produto.objects.create
        attempts = {"count": 0}

        def mock_create(*args, **kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                # Simula race condition onde outro worker acabou de inserir MAT-001
                Produto.objects.create(
                    codigo="MAT-001",
                    nome="Criado por outro worker",
                    categoria=self.categoria,
                    criado_por=self.user,
                )
                raise IntegrityError("UNIQUE constraint failed: estoque_produto.codigo")
            return original_create(*args, **kwargs)

        with patch.object(Produto.objects, "create", side_effect=mock_create):
            response = self.client.post(self.url, {
                "nome": "Meu Produto Concorrente",
                "categoria_id": self.categoria.pk,
            })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Deve ter recuperado na 2ª tentativa gerando MAT-002
        self.assertEqual(data["codigo"], "MAT-002")
