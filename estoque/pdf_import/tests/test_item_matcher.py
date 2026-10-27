from decimal import Decimal
from pathlib import Path
from django.test import TestCase

from estoque.pdf_import.empenho_parser import parse_empenho
from estoque.pdf_import.item_matcher import match_items
from estoque.pdf_import.nfe_parser import parse_nfe


class ItemMatcherTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        cls.nfe = parse_nfe(fixtures_dir / "nfe_sample.pdf")
        cls.empenho = parse_empenho(fixtures_dir / "empenho_sample.pdf")
        cls.matches = match_items(cls.nfe, cls.empenho)

    def test_matching_por_qty_value(self):
        # 3 itens na NFe devem casar com os 3 do Empenho
        self.assertEqual(len(self.matches), 3)
        for m in self.matches:
            self.assertEqual(m["match_method"], "qty_value")
            self.assertEqual(m["confidence"], "high")
            self.assertIsNotNone(m["empenho_item"])

    def test_item1_nfe_casa_com_margarina_empenho(self):
        # item[0] NFe (Margarina 40/9.80) casa com item[0] Empenho (Margarina 40/9.80)
        m = self.matches[0]
        self.assertEqual(m["nfe_item"]["quantidade"], Decimal("40.00"))
        self.assertEqual(m["nfe_item"]["valor_unitario"], Decimal("9.80"))
        self.assertEqual(m["empenho_item"]["sequencia"], "001")
        self.assertEqual(m["empenho_item"]["quantidade"], Decimal("40"))
        self.assertIn("MARGARINA", m["empenho_item"]["descricao"].upper())

    def test_item2_nfe_casa_com_adocante_empenho(self):
        # item[1] NFe (Adoçante 36/6.10) casa com item[2] Empenho (Adoçante 36/6.10, seq 003) — ordem diferente!
        m = self.matches[1]
        self.assertEqual(m["nfe_item"]["quantidade"], Decimal("36.00"))
        self.assertEqual(m["nfe_item"]["valor_unitario"], Decimal("6.10"))
        self.assertEqual(m["empenho_item"]["sequencia"], "003")
        self.assertEqual(m["empenho_item"]["quantidade"], Decimal("36"))
        self.assertIn("ADOCANTE", m["empenho_item"]["descricao"].upper())

    def test_item3_nfe_casa_com_acucar_empenho(self):
        # item[2] NFe (Açúcar 100/3.70) casa com item[1] Empenho (Açúcar 100/3.70, seq 002)
        m = self.matches[2]
        self.assertEqual(m["nfe_item"]["quantidade"], Decimal("100.00"))
        self.assertEqual(m["nfe_item"]["valor_unitario"], Decimal("3.70"))
        self.assertEqual(m["empenho_item"]["sequencia"], "002")
        self.assertEqual(m["empenho_item"]["quantidade"], Decimal("100"))
        self.assertIn("ACUCAR", m["empenho_item"]["descricao"].upper())

    def test_nenhum_item_empenho_usado_duas_vezes(self):
        matched_seqs = [m["empenho_item"]["sequencia"] for m in self.matches if m["empenho_item"]]
        self.assertEqual(len(matched_seqs), len(set(matched_seqs)))

    def test_sem_match_retorna_empenho_item_none(self):
        nfe_item_avulso = {
            "itens": [
                {
                    "codigo": "xyz",
                    "descricao": "Item Inexistente",
                    "quantidade": Decimal("999"),
                    "valor_unitario": Decimal("999.00"),
                    "valor_total": Decimal("999.00"),
                }
            ]
        }
        res = match_items(nfe_item_avulso, self.empenho)
        self.assertEqual(len(res), 1)
        self.assertIsNone(res[0]["empenho_item"])
        self.assertEqual(res[0]["match_method"], "none")
        self.assertEqual(res[0]["confidence"], "low")
