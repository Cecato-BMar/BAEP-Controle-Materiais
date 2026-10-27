from decimal import Decimal
from django.test import SimpleTestCase

from estoque.pdf_import.validators import validate_nfe_vs_empenho


class ValidatorsTests(SimpleTestCase):
    def test_cnpj_match_com_formatacao_diferente(self):
        nfe = {
            "emitente": {"cnpj": "64.490.977/0001-17"},
            "valor_total_nota": Decimal("981.60"),
            "empenho_referencia": "2026NE01176",
            "itens": [{"valor_total": Decimal("981.60")}],
        }
        empenho = {
            "credor": {"cnpj": "64490977000117"},
            "valor_empenho": Decimal("981.60"),
            "numero_empenho": "2026NE01176",
        }
        res = validate_nfe_vs_empenho(nfe, empenho)
        self.assertTrue(res["checks"]["cnpj_match"])
        self.assertTrue(res["valid"])

    def test_valor_match_exato(self):
        nfe = {
            "emitente": {"cnpj": "64490977000117"},
            "valor_total_nota": Decimal("981.60"),
            "empenho_referencia": "2026NE01176",
            "itens": [{"valor_total": Decimal("981.60")}],
        }
        empenho = {
            "credor": {"cnpj": "64490977000117"},
            "valor_empenho": Decimal("981.60"),
            "numero_empenho": "2026NE01176",
        }
        res = validate_nfe_vs_empenho(nfe, empenho)
        self.assertTrue(res["checks"]["valor_match"])
        self.assertTrue(res["valid"])

    def test_valor_divergente_gera_error(self):
        nfe = {
            "emitente": {"cnpj": "64490977000117"},
            "valor_total_nota": Decimal("981.60"),
            "empenho_referencia": "2026NE01176",
            "itens": [{"valor_total": Decimal("981.60")}],
        }
        empenho = {
            "credor": {"cnpj": "64490977000117"},
            "valor_empenho": Decimal("900.00"),
            "numero_empenho": "2026NE01176",
        }
        res = validate_nfe_vs_empenho(nfe, empenho)
        self.assertFalse(res["checks"]["valor_match"])
        self.assertFalse(res["valid"])
        self.assertTrue(len(res["errors"]) > 0)

    def test_empenho_ref_match(self):
        nfe = {
            "emitente": {"cnpj": "64490977000117"},
            "valor_total_nota": Decimal("981.60"),
            "empenho_referencia": "2026NE01176",
            "itens": [{"valor_total": Decimal("981.60")}],
        }
        empenho = {
            "credor": {"cnpj": "64490977000117"},
            "valor_empenho": Decimal("981.60"),
            "numero_empenho": "2026NE01176",
        }
        res = validate_nfe_vs_empenho(nfe, empenho)
        self.assertTrue(res["checks"]["empenho_ref_match"])
        self.assertTrue(res["valid"])

    def test_empenho_ref_divergente_gera_error(self):
        nfe = {
            "emitente": {"cnpj": "64490977000117"},
            "valor_total_nota": Decimal("981.60"),
            "empenho_referencia": "2026NE01176",
            "itens": [{"valor_total": Decimal("981.60")}],
        }
        empenho = {
            "credor": {"cnpj": "64490977000117"},
            "valor_empenho": Decimal("981.60"),
            "numero_empenho": "2026NE99999",
        }
        res = validate_nfe_vs_empenho(nfe, empenho)
        self.assertFalse(res["checks"]["empenho_ref_match"])
        self.assertFalse(res["valid"])
        self.assertTrue(len(res["errors"]) > 0)

    def test_ocr_ruim_gera_warning_nao_error(self):
        # Quando OCR falha e campos vêm None, gera warning, mas não bloqueia com error se não há conflito explícito
        nfe = {
            "emitente": {"cnpj": None},
            "valor_total_nota": None,
            "empenho_referencia": None,
            "itens": [],
        }
        empenho = {
            "credor": {"cnpj": None},
            "valor_empenho": None,
            "numero_empenho": None,
            "itens": [],
        }
        res = validate_nfe_vs_empenho(nfe, empenho)
        self.assertTrue(res["valid"])
        self.assertEqual(len(res["errors"]), 0)
        self.assertTrue(len(res["warnings"]) > 0)
