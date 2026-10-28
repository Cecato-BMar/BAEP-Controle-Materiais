from pathlib import Path
from unittest.mock import patch
from django.test import TestCase, override_settings

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

    def test_process_pdfs_apenas_nfe(self):
        result = process_pdfs(self.nfe_path, None)
        for key in ["nfe", "empenho", "validation", "matches", "header_suggestions", "warnings"]:
            self.assertIn(key, result)
        self.assertEqual(result["empenho"], {})
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(len(result["matches"]), 3)
        for m in result["matches"]:
            self.assertEqual(m["match_method"], "nfe_only")
            self.assertEqual(m["match_confidence"], "medium")
            self.assertIsNone(m["empenho_item"])

    def test_header_suggestions_fallback_empenho_ref(self):
        result = process_pdfs(self.nfe_path, None)
        hdr = result["header_suggestions"]
        self.assertEqual(hdr["documento_referencia"], "2026NE01176")
        self.assertEqual(hdr["nota_fiscal"], "000362")

    def test_metodo_extracao_padrao_local_ocr(self):
        self.assertEqual(self.result["nfe"].get("_extraction_method"), "local_ocr")

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("estoque.pdf_import.orchestrator.extract_nfe_items_with_gemini")
    def test_gemini_fallback_nao_acionado_quando_ocr_bate(self, mock_gemini):
        result = process_pdfs(self.nfe_path, None)
        mock_gemini.assert_not_called()
        self.assertEqual(result["nfe"]["_extraction_method"], "local_ocr")

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("estoque.pdf_import.orchestrator.extract_nfe_items_with_gemini")
    @patch("estoque.pdf_import.orchestrator.parse_nfe")
    def test_gemini_fallback_acionado_quando_ocr_diverge(self, mock_parse_nfe, mock_gemini):
        from decimal import Decimal
        mock_parse_nfe.return_value = {
            "chave_acesso": "35261064490977000117550010000003621415663784",
            "numero_nf": "000362",
            "valor_total_nota": Decimal("981.60"),
            "itens": [
                {
                    "codigo": "001",
                    "descricao": "Item Incompleto OCR",
                    "valor_total": Decimal("100.00"),
                    "quantidade": Decimal("10.00"),
                    "valor_unitario": Decimal("10.00"),
                }
            ],
            "empenho_referencia": "2026NE01176",
            "_confidence": {"itens": "low"},
        }

        mock_gemini.return_value = [
            {
                "codigo": "001",
                "descricao": "Margarina Becel 500g",
                "ncm": "15171000",
                "cfop": "5102",
                "unidade": "UN",
                "quantidade": Decimal("40.00"),
                "valor_unitario": Decimal("9.80"),
                "valor_total": Decimal("392.00"),
            },
            {
                "codigo": "002",
                "descricao": "Adoçante Líquido 100ml",
                "ncm": "29251100",
                "cfop": "5102",
                "unidade": "UN",
                "quantidade": Decimal("36.00"),
                "valor_unitario": Decimal("6.10"),
                "valor_total": Decimal("219.60"),
            },
            {
                "codigo": "003",
                "descricao": "Café Torrado 500g",
                "ncm": "09012100",
                "cfop": "5102",
                "unidade": "UN",
                "quantidade": Decimal("20.00"),
                "valor_unitario": Decimal("18.50"),
                "valor_total": Decimal("370.00"),
            },
        ]

        result = process_pdfs(self.nfe_path, None)

        mock_gemini.assert_called_once()
        self.assertEqual(result["nfe"]["_extraction_method"], "gemini_fallback")
        self.assertEqual(len(result["nfe"]["itens"]), 3)
        self.assertEqual(result["nfe"]["_confidence"]["itens"], "high")


