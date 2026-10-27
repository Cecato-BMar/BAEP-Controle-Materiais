from datetime import date
from decimal import Decimal
from pathlib import Path
from django.test import TestCase

from estoque.pdf_import.empenho_parser import parse_empenho

class EmpenhoParserTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixture_path = Path(__file__).resolve().parent / "fixtures" / "empenho_sample.pdf"
        cls.parsed_result = parse_empenho(cls.fixture_path)

    def test_parse_empenho_numero(self):
        self.assertEqual(self.parsed_result["numero_empenho"], "2026NE01176")

    def test_parse_empenho_data_emissao(self):
        # 18SET2026 → date(2026, 9, 18)
        self.assertEqual(self.parsed_result["data_emissao"], date(2026, 9, 18))

    def test_parse_empenho_valor(self):
        self.assertEqual(self.parsed_result["valor_empenho"], Decimal("981.60"))

    def test_parse_empenho_credor_cnpj(self):
        self.assertEqual(self.parsed_result["credor"]["cnpj"], "64490977000117")

    def test_parse_empenho_contrato(self):
        self.assertEqual(self.parsed_result["numero_contrato"], "2026CT00267")

    def test_parse_empenho_itens(self):
        self.assertEqual(len(self.parsed_result["itens"]), 3)
        # Validação do item 1 (Margarina)
        it1 = self.parsed_result["itens"][0]
        self.assertEqual(it1["sequencia"], "001")
        self.assertEqual(it1["quantidade"], Decimal("40"))
        self.assertEqual(it1["valor_unitario"], Decimal("9.80"))
        self.assertEqual(it1["preco_total"], Decimal("392.00"))
        self.assertIn("MARGARINA", it1["descricao"].upper())

    def test_parse_empenho_data_entrega(self):
        # 30SET2026 → date(2026, 9, 30)
        self.assertEqual(self.parsed_result["data_entrega"], date(2026, 9, 30))

    def test_parse_empenho_local_entrega(self):
        self.assertIn("MONTENEGRO", self.parsed_result["local_entrega"].upper())

    def test_parse_empenho_arquivo_invalido(self):
        result = parse_empenho(b"not a pdf")
        self.assertIsNone(result["numero_empenho"])
        self.assertEqual(result["itens"], [])
