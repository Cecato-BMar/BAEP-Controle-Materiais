from decimal import Decimal
from pathlib import Path
from django.test import TestCase

from estoque.pdf_import.nfe_parser import parse_nfe

class NFeParserTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixture_path = Path(__file__).resolve().parent / "fixtures" / "nfe_sample.pdf"
        # Parseia uma vez na classe para os testes rodarem instantaneamente
        cls.parsed_result = parse_nfe(cls.fixture_path)

    def test_parse_nfe_chave_acesso(self):
        self.assertEqual(self.parsed_result["chave_acesso"], "35261064490977000117550010000003621297599470")

    def test_parse_nfe_numero(self):
        self.assertEqual(self.parsed_result["numero_nf"], "000362")

    def test_parse_nfe_cnpj_emitente(self):
        cnpj = self.parsed_result["emitente"]["cnpj"]
        self.assertTrue(cnpj in ("64.490.977/0001-17", "64490977000117"))

    def test_parse_nfe_valor_total(self):
        self.assertEqual(self.parsed_result["valor_total_nota"], Decimal("981.60"))

    def test_parse_nfe_empenho_referencia(self):
        self.assertEqual(self.parsed_result["empenho_referencia"], "2026NE01176")

    def test_parse_nfe_itens_count(self):
        self.assertEqual(len(self.parsed_result["itens"]), 3)

    def test_parse_nfe_itens_margarina(self):
        margarina = next((i for i in self.parsed_result["itens"] if i["quantidade"] == Decimal("40.00")), None)
        self.assertIsNotNone(margarina)
        self.assertEqual(margarina["valor_unitario"], Decimal("9.80"))
        self.assertEqual(margarina["codigo"], "margesal")

    def test_parse_nfe_confidence(self):
        self.assertTrue(self.parsed_result["_ocr_used"])
        self.assertEqual(self.parsed_result["_confidence"]["chave_acesso"], "high")
        self.assertEqual(self.parsed_result["_confidence"]["itens"], "low")

    def test_parse_nfe_arquivo_invalido_retorna_dict_vazio(self):
        result = parse_nfe(b"not a pdf")
        self.assertIsNone(result["chave_acesso"])
        self.assertIsNone(result["numero_nf"])
        self.assertEqual(result["itens"], [])
