import datetime
import json
from decimal import Decimal
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from estoque.models import (
    AnexoMovimentacao,
    Categoria,
    MovimentacaoEstoque,
    Produto,
)
from licenciamento.license_core import LicenseManager
from licenciamento.models import LicenseRecord


class ConfirmarImportacaoViewTests(TestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.url = reverse("estoque:confirmar_importacao")

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
        self.user = User.objects.create_user(username="operador_confirmar", password="password123")
        self.grupo_materiais, _ = Group.objects.get_or_create(name="materiais")
        self.user.groups.add(self.grupo_materiais)

        self.user_sem_permissao = User.objects.create_user(
            username="sem_permissao_confirmar", password="password123"
        )

        # Dados base
        self.categoria = Categoria.objects.create(
            codigo="GEN-ALIM", nome="Gêneros Alimentícios"
        )
        self.p1 = Produto.objects.create(
            codigo="MAT-001", nome="Item 1", categoria=self.categoria, status="ATIVO", criado_por=self.user
        )
        self.p2 = Produto.objects.create(
            codigo="MAT-002", nome="Item 2", categoria=self.categoria, status="ATIVO", criado_por=self.user
        )
        self.p3 = Produto.objects.create(
            codigo="MAT-003", nome="Item 3", categoria=self.categoria, status="ATIVO", criado_por=self.user
        )

        self.payload_dict = {
            "header": {
                "nota_fiscal": "000362",
                "documento_referencia": "2026NE01176",
                "data_movimentacao": "2026-10-14",
                "fornecedor_nome": "COMERCIAL ALIMENTOS LTDA",
                "fornecedor_cnpj": "64.490.977/0001-17",
            },
            "items": [
                {"produto_id": self.p1.pk, "quantidade": "40.00", "valor_unitario": "9.80"},
                {"produto_id": self.p2.pk, "quantidade": "60.00", "valor_unitario": "3.66"},
                {"produto_id": self.p3.pk, "quantidade": "20.00", "valor_unitario": "18.50"},
            ],
        }

    def _files(self):
        return {
            "nfe_pdf": SimpleUploadedFile("nfe.pdf", b"%PDF-1.4 test nfe content"),
            "empenho_pdf": SimpleUploadedFile("empenho.pdf", b"%PDF-1.4 test empenho content"),
        }

    def test_rejeita_sem_login(self):
        response = self.client.post(self.url, {"payload": json.dumps(self.payload_dict)})
        self.assertEqual(response.status_code, 302)

    def test_rejeita_sem_permissao(self):
        self.client.force_login(self.user_sem_permissao)
        response = self.client.post(self.url, {"payload": json.dumps(self.payload_dict)})
        self.assertEqual(response.status_code, 403)

    def test_rejeita_sem_payload(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self._files())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Payload ausente.")

    def test_rejeita_payload_invalido(self):
        self.client.force_login(self.user)
        data = {"payload": "{json_invalido: 123", **self._files()}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "JSON inválido.")

    def test_rejeita_sem_pdfs(self):
        self.client.force_login(self.user)
        # Falta empenho_pdf
        data = {
            "payload": json.dumps(self.payload_dict),
            "nfe_pdf": SimpleUploadedFile("nfe.pdf", b"%PDF-1.4"),
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Reenvie os PDFs.")

    def test_sucesso_cria_3_movimentacoes(self):
        self.client.force_login(self.user)
        data = {
            "payload": json.dumps(self.payload_dict),
            **self._files(),
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)

        res_json = response.json()
        self.assertTrue(res_json.get("success"))
        self.assertEqual(res_json.get("movimentacoes_criadas"), 3)
        self.assertEqual(res_json.get("anexos_criados"), 6)
        self.assertEqual(len(res_json.get("ids")), 3)

        self.assertEqual(MovimentacaoEstoque.objects.count(), 3)
        self.assertEqual(AnexoMovimentacao.objects.count(), 6)

        # Checar que o valor_total foi calculado corretamente para cada item
        m1 = MovimentacaoEstoque.objects.get(produto=self.p1)
        self.assertEqual(m1.valor_total, Decimal("392.00"))
        m2 = MovimentacaoEstoque.objects.get(produto=self.p2)
        self.assertEqual(m2.valor_total, Decimal("219.60"))
        m3 = MovimentacaoEstoque.objects.get(produto=self.p3)
        self.assertEqual(m3.valor_total, Decimal("370.00"))

    def test_rollback_em_erro_no_item_2(self):
        self.client.force_login(self.user)
        payload_erro = {
            **self.payload_dict,
            "items": [
                {"produto_id": self.p1.pk, "quantidade": "40.00", "valor_unitario": "9.80"},
                {"produto_id": 99999, "quantidade": "60.00", "valor_unitario": "3.66"},  # ID inválido
                {"produto_id": self.p3.pk, "quantidade": "20.00", "valor_unitario": "18.50"},
            ],
        }
        data = {
            "payload": json.dumps(payload_erro),
            **self._files(),
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("produto ID 99999 não existe", response.json()["error"])

        # Nenhuma movimentação ou anexo pode ter ficado no banco
        self.assertEqual(MovimentacaoEstoque.objects.count(), 0)
        self.assertEqual(AnexoMovimentacao.objects.count(), 0)
