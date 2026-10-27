from pathlib import Path
from unittest.mock import patch
from django.test import TestCase

from estoque.pdf_import.orchestrator import process_pdfs


class OrchestratorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        cls.nfe_path = fixtures_dir / "nfe_sample.pdf"
        cls.empenho_path = fixtures_dir / "empenho_sample.pdf"
        cls.result = process_pdfs(cls.nfe_path, cls.empenho_path)

    def test_estrutura_completa(self):
        # Verifica presença das chaves principais
        for key in ["nfe", "empenho", "validation", "matches", "header_suggestions", "warnings"]:
            self.assertIn(key, self.result)

    def test_validacao_cruzada_ok(self):
        val = self.result["validation"]
        self.assertTrue(val["valid"])
        self.assertTrue(val["checks"]["cnpj_match"])
        self.assertTrue(val["checks"]["valor_match"])
        self.assertTrue(val["checks"]["empenho_ref_match"])

    def test_matching_ordem_invertida(self):
        # NFe item 1 (Adoçante 36x6.10) deve casar com o item 3 do empenho (seq 003)
        matches = self.result["matches"]
        self.assertEqual(len(matches), 3)
        it1 = matches[1]
        self.assertIn("ADOCANTE", it1["nfe_item"]["descricao"].upper())
        self.assertEqual(it1["empenho_item"]["sequencia"], "003")
        self.assertEqual(it1["match_method"], "qty_value")
        self.assertEqual(it1["match_confidence"], "high")

    def test_sugestao_para_cada_item(self):
        matches = self.result["matches"]
        for m in matches:
            self.assertIn("suggestion", m)
            sug = m["suggestion"]
            self.assertIn("method", sug)
            self.assertIn("confidence", sug)
            self.assertIn("ncm_nfe", sug)

    def test_header_suggestions_preenchidas(self):
        hdr = self.result["header_suggestions"]
        self.assertEqual(hdr["nota_fiscal"], "000362")
        self.assertEqual(hdr["documento_referencia"], "2026NE01176")
        self.assertEqual(hdr["data_movimentacao"], "2026-10-14")
        self.assertEqual(hdr["fornecedor_cnpj"], "64.490.977/0001-17")

    def test_rejeita_dois_pdfs_mesmo_tipo(self):
        # Enviar 2 NFes deve levantar ValueError
        with self.assertRaises(ValueError) as ctx:
            process_pdfs(self.nfe_path, self.nfe_path)
        self.assertIn("Recebi 2 do mesmo tipo", str(ctx.exception))

    def test_consolida_warnings_ocr(self):
        # Se OCR de itens for low, consolida warning explicativo
        self.assertIn("Descrições de itens com baixa confiança (OCR)", self.result["warnings"])
