from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase

from estoque.models import Categoria, Produto
from estoque.pdf_import.product_matcher import suggest_product


class ProductMatcherTests(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="testuser_matcher", password="password123")
        self.cat = Categoria.objects.create(nome="Alimentação", codigo="ALIM")

        self.prod_margarina = Produto.objects.create(
            codigo="MAT-001",
            nome="MARGARINA COM SAL 500G",
            categoria=self.cat,
            codigo_cat_mat="4595777",  # sem zeros e sem traço para testar normalização
            status="ATIVO",
            criado_por=self.user,
        )
        self.prod_acucar = Produto.objects.create(
            codigo="MAT-002",
            nome="ACUCAR REFINADO 1KG",
            categoria=self.cat,
            codigo_cat_mat="17019900",
            status="ATIVO",
            criado_por=self.user,
        )
        self.prod_adocante = Produto.objects.create(
            codigo="MAT-003",
            nome="ADOCANTE DIETETICO 100ML",
            categoria=self.cat,
            codigo_cat_mat="29251100",
            status="ATIVO",
            criado_por=self.user,
        )

    def test_match_por_catmat_exato(self):
        nfe_item = {
            "descricao": "Item Qualquer",
            "ncm": "17019900",
        }
        empenho_item = {
            "codigo_item": "17019900",
            "descricao": "ACUCAR REFINADO...",
        }
        res = suggest_product(nfe_item, empenho_item)
        self.assertEqual(res["method"], "catmat_exact")
        self.assertEqual(res["confidence"], "high")
        self.assertEqual(res["produto_id"], self.prod_acucar.id)
        self.assertEqual(res["produto_nome"], self.prod_acucar.nome)

    def test_normalizacao_catmat(self):
        # codigo_item="00459577-7" casa com codigo_cat_mat="4595777" (após normalizar)
        nfe_item = {
            "descricao": "Margaina Becel cm sal 5009",
            "ncm": "15171000",
        }
        empenho_item = {
            "codigo_item": "00459577-7",
            "descricao": "MARGARINA, COM SAL...",
        }
        res = suggest_product(nfe_item, empenho_item)
        self.assertEqual(res["method"], "catmat_exact")
        self.assertEqual(res["confidence"], "high")
        self.assertEqual(res["produto_id"], self.prod_margarina.id)
        self.assertEqual(res["produto_nome"], self.prod_margarina.nome)

    def test_sem_codigo_item_cai_para_nome(self):
        # empenho_item=None → usa name_similar
        nfe_item = {
            "descricao": "Margarina Becel",
            "ncm": "15171000",
        }
        res = suggest_product(nfe_item, empenho_item=None)
        self.assertEqual(res["method"], "name_similar")
        self.assertEqual(res["produto_id"], self.prod_margarina.id)
        self.assertEqual(res["confidence"], "medium")

    def test_match_por_nome_similar(self):
        nfe_item = {
            "descricao": "Margarina Becel",
            "ncm": None,
        }
        # Empenho com codigo que não bate com nada
        empenho_item = {
            "codigo_item": "99999999",
            "descricao": "Margarina vegetal",
        }
        res = suggest_product(nfe_item, empenho_item)
        self.assertEqual(res["method"], "name_similar")
        self.assertEqual(res["produto_id"], self.prod_margarina.id)
        self.assertEqual(res["produto_nome"], self.prod_margarina.nome)
        self.assertEqual(res["confidence"], "medium")

    def test_sem_match_retorna_alternatives_top3(self):
        nfe_item = {
            "descricao": "Parafuso Sextavado de Aço Inox",
            "ncm": "73181500",
        }
        empenho_item = {
            "codigo_item": "88888888",
            "descricao": "PARAFUSO METALICO",
        }
        res = suggest_product(nfe_item, empenho_item)
        self.assertEqual(res["method"], "none")
        self.assertEqual(res["confidence"], "low")
        self.assertIsNone(res["produto_id"])
        self.assertIsNone(res["produto_nome"])
        self.assertEqual(len(res["alternatives"]), 3)

    def test_retorno_inclui_ncm_nfe(self):
        nfe_item = {
            "descricao": "Margarina",
            "ncm": "15171000",
        }
        res = suggest_product(nfe_item)
        self.assertEqual(res["ncm_nfe"], "15171000")
