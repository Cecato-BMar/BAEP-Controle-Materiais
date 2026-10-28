import datetime
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from estoque.models import (
    AnexoMovimentacao,
    Categoria,
    Fornecedor,
    MovimentacaoEstoque,
    Produto,
)
from estoque.pdf_import.importer import create_movimentacoes_from_import


class ImporterTests(TestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="operador_importer", password="password")
        self.categoria = Categoria.objects.create(
            codigo="GEN-ALIM", nome="Gêneros Alimentícios"
        )

        self.produto1 = Produto.objects.create(
            codigo="MAT-001",
            nome="Margarina Becel 500g",
            categoria=self.categoria,
            status="ATIVO",
            criado_por=self.user,
        )
        self.produto2 = Produto.objects.create(
            codigo="MAT-002",
            nome="Açúcar Refinado 1kg",
            categoria=self.categoria,
            status="ATIVO",
            criado_por=self.user,
        )
        self.produto3 = Produto.objects.create(
            codigo="MAT-003",
            nome="Café Torrado 500g",
            categoria=self.categoria,
            status="ATIVO",
            criado_por=self.user,
        )

        self.header_data = {
            "nota_fiscal": "000362",
            "documento_referencia": "2026NE01176",
            "data_movimentacao": "2026-10-14",
            "fornecedor_nome": "COMERCIAL ALIMENTOS LTDA",
            "fornecedor_cnpj": "64.490.977/0001-17",
        }

        self.items_data = [
            {"produto_id": self.produto1.pk, "quantidade": "40.00", "valor_unitario": "9.80"},
            {"produto_id": self.produto2.pk, "quantidade": "60.00", "valor_unitario": "3.66"},
            {"produto_id": self.produto3.pk, "quantidade": "20.00", "valor_unitario": "18.50"},
        ]

    def _build_request(self):
        request = self.factory.post("/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        return request

    def _build_files(self):
        nfe_file = SimpleUploadedFile("nfe_362.pdf", b"%PDF-1.4 test nfe content")
        empenho_file = SimpleUploadedFile("empenho_1176.pdf", b"%PDF-1.4 test empenho content")
        return nfe_file, empenho_file

    def test_cria_3_movimentacoes(self):
        request = self._build_request()
        nfe_file, empenho_file = self._build_files()

        result = create_movimentacoes_from_import(
            request=request,
            header_data=self.header_data,
            items=self.items_data,
            nfe_file=nfe_file,
            empenho_file=empenho_file,
        )

        self.assertEqual(result["movimentacoes_criadas"], 3)
        self.assertEqual(MovimentacaoEstoque.objects.count(), 3)

        mov1 = MovimentacaoEstoque.objects.get(produto=self.produto1)
        self.assertEqual(mov1.subtipo, "COMPRA_NOVA")
        self.assertEqual(mov1.tipo_movimentacao, "ENTRADA")
        self.assertEqual(mov1.quantidade, Decimal("40.00"))
        self.assertEqual(mov1.valor_unitario, Decimal("9.80"))
        self.assertEqual(mov1.valor_total, Decimal("392.00"))
        self.assertEqual(mov1.nota_fiscal, "000362")
        self.assertEqual(mov1.documento_referencia, "2026NE01176")
        self.assertEqual(mov1.data_movimentacao, datetime.date(2026, 10, 14))
        self.assertEqual(mov1.ip_address, "192.168.1.100")
        self.assertEqual(mov1.usuario, self.user)

    def test_cria_6_anexos(self):
        request = self._build_request()
        nfe_file, empenho_file = self._build_files()

        result = create_movimentacoes_from_import(
            request=request,
            header_data=self.header_data,
            items=self.items_data,
            nfe_file=nfe_file,
            empenho_file=empenho_file,
        )

        self.assertEqual(result["anexos_criados"], 6)
        self.assertEqual(AnexoMovimentacao.objects.count(), 6)
        self.assertEqual(AnexoMovimentacao.objects.filter(tipo="NFE").count(), 3)
        self.assertEqual(AnexoMovimentacao.objects.filter(tipo="EMPENHO").count(), 3)

    def test_anexos_referenciam_mesmo_path(self):
        request = self._build_request()
        nfe_file, empenho_file = self._build_files()

        create_movimentacoes_from_import(
            request=request,
            header_data=self.header_data,
            items=self.items_data,
            nfe_file=nfe_file,
            empenho_file=empenho_file,
        )

        nfe_paths = set(AnexoMovimentacao.objects.filter(tipo="NFE").values_list("arquivo", flat=True))
        empenho_paths = set(AnexoMovimentacao.objects.filter(tipo="EMPENHO").values_list("arquivo", flat=True))

        self.assertEqual(len(nfe_paths), 1, "Todos os anexos NFE devem referenciar o mesmo arquivo físico")
        self.assertEqual(len(empenho_paths), 1, "Todos os anexos EMPENHO devem referenciar o mesmo arquivo físico")

    def test_atomico_item_invalido_reverte_tudo(self):
        request = self._build_request()
        nfe_file, empenho_file = self._build_files()

        items_com_erro = [
            {"produto_id": self.produto1.pk, "quantidade": "40.00", "valor_unitario": "9.80"},
            {"produto_id": 99999, "quantidade": "60.00", "valor_unitario": "3.66"},  # Não existe
        ]

        with self.assertRaises(ValueError) as ctx:
            create_movimentacoes_from_import(
                request=request,
                header_data=self.header_data,
                items=items_com_erro,
                nfe_file=nfe_file,
                empenho_file=empenho_file,
            )

        self.assertIn("produto ID 99999 não existe", str(ctx.exception))
        self.assertEqual(MovimentacaoEstoque.objects.count(), 0)
        self.assertEqual(AnexoMovimentacao.objects.count(), 0)

    def test_valida_quantidade_positiva(self):
        request = self._build_request()
        nfe_file, empenho_file = self._build_files()

        items_qtd_zero = [
            {"produto_id": self.produto1.pk, "quantidade": "0", "valor_unitario": "9.80"},
        ]

        with self.assertRaises(ValueError) as ctx:
            create_movimentacoes_from_import(
                request=request,
                header_data=self.header_data,
                items=items_qtd_zero,
                nfe_file=nfe_file,
                empenho_file=empenho_file,
            )
        self.assertIn("quantidade deve ser > 0", str(ctx.exception))

    def test_fornecedor_criado_se_nao_existe(self):
        request = self._build_request()
        nfe_file, empenho_file = self._build_files()

        self.assertFalse(Fornecedor.objects.filter(documento="64490977000117").exists())

        create_movimentacoes_from_import(
            request=request,
            header_data=self.header_data,
            items=self.items_data,
            nfe_file=nfe_file,
            empenho_file=empenho_file,
        )

        fornecedor = Fornecedor.objects.filter(documento="64490977000117").first()
        self.assertIsNotNone(fornecedor)
        self.assertEqual(fornecedor.nome, "COMERCIAL ALIMENTOS LTDA")

    def test_fornecedor_reusado_se_existe(self):
        fornecedor_existente = Fornecedor.objects.create(
            documento="64490977000117",
            nome="FORNECEDOR JA CADASTRADO",
            tipo_pessoa="JURIDICA",
        )

        request = self._build_request()
        nfe_file, empenho_file = self._build_files()

        create_movimentacoes_from_import(
            request=request,
            header_data=self.header_data,
            items=self.items_data,
            nfe_file=nfe_file,
            empenho_file=empenho_file,
        )

        self.assertEqual(Fornecedor.objects.filter(documento="64490977000117").count(), 1)
        mov = MovimentacaoEstoque.objects.first()
        self.assertEqual(mov.fornecedor, fornecedor_existente)

    def test_fornecedor_normaliza_cnpj(self):
        header = {
            **self.header_data,
            "fornecedor_cnpj": "64.490.977/0001-17",
        }
        request = self._build_request()
        nfe_file, empenho_file = self._build_files()

        create_movimentacoes_from_import(
            request=request,
            header_data=header,
            items=self.items_data,
            nfe_file=nfe_file,
            empenho_file=empenho_file,
        )

        fornecedor = Fornecedor.objects.get(documento="64490977000117")
        self.assertEqual(fornecedor.documento, "64490977000117")
        self.assertFalse(Fornecedor.objects.filter(documento="64.490.977/0001-17").exists())

    def test_sem_empenho_cria_apenas_anexo_nfe(self):
        request = self._build_request()
        nfe_file, _ = self._build_files()

        result = create_movimentacoes_from_import(
            request=request,
            header_data=self.header_data,
            items=self.items_data,
            nfe_file=nfe_file,
            empenho_file=None,
        )

        self.assertEqual(result["movimentacoes_criadas"], 3)
        self.assertEqual(result["anexos_criados"], 3)
        self.assertEqual(MovimentacaoEstoque.objects.count(), 3)
        self.assertEqual(AnexoMovimentacao.objects.count(), 3)
        tipos = list(AnexoMovimentacao.objects.values_list("tipo", flat=True))
        self.assertEqual(tipos, ["NFE", "NFE", "NFE"])

