import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from estoque.pdf_import.gemini_extractor import extract_nfe_items_with_gemini


class GeminiExtractorTests(SimpleTestCase):
    @override_settings(GEMINI_API_KEY="")
    def test_sem_api_key_levanta_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            extract_nfe_items_with_gemini(b"%PDF-1.4 dummy")
        self.assertIn("GEMINI_API_KEY não configurada", str(ctx.exception))

    @override_settings(GEMINI_API_KEY="test-api-key")
    @patch("estoque.pdf_import.gemini_extractor.genai.GenerativeModel")
    @patch("estoque.pdf_import.gemini_extractor.genai.configure")
    def test_extracao_sucesso_lista_json(self, mock_configure, mock_model_class):
        mock_response = MagicMock()
        mock_response.text = json.dumps([
            {
                "codigo": "001",
                "descricao": "Margarina Becel 500g",
                "ncm": "15171000",
                "cfop": "5102",
                "unidade": "UN",
                "quantidade": "40.00",
                "valor_unitario": "9.80",
                "valor_total": "392.00",
            },
            {
                "codigo": "002",
                "descricao": "Adoçante Líquido 100ml",
                "ncm": "29251100",
                "cfop": "5102",
                "quantidade": 36,
                "valor_unitario": 6.1,
                "valor_total": 219.60,
            },
        ])

        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_instance

        itens = extract_nfe_items_with_gemini(b"%PDF-1.4 dummy")

        mock_configure.assert_called_once_with(api_key="test-api-key")
        self.assertEqual(len(itens), 2)

        it1 = itens[0]
        self.assertEqual(it1["codigo"], "001")
        self.assertEqual(it1["descricao"], "Margarina Becel 500g")
        self.assertEqual(it1["ncm"], "15171000")
        self.assertEqual(it1["cfop"], "5102")
        self.assertEqual(it1["unidade"], "UN")
        self.assertEqual(it1["quantidade"], Decimal("40.00"))
        self.assertEqual(it1["valor_unitario"], Decimal("9.80"))
        self.assertEqual(it1["valor_total"], Decimal("392.00"))

        it2 = itens[1]
        self.assertEqual(it2["codigo"], "002")
        self.assertEqual(it2["quantidade"], Decimal("36.00"))
        self.assertEqual(it2["valor_unitario"], Decimal("6.10"))
        self.assertEqual(it2["valor_total"], Decimal("219.60"))

    @override_settings(GEMINI_API_KEY="test-api-key")
    @patch("estoque.pdf_import.gemini_extractor.genai.GenerativeModel")
    @patch("estoque.pdf_import.gemini_extractor.genai.configure")
    def test_extracao_sucesso_dict_com_chave_itens(self, mock_configure, mock_model_class):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "itens": [
                {
                    "codigo": "CAF-01",
                    "descricao": "Café Torrado 500g",
                    "quantidade": "20",
                    "valor_unitario": "18.50",
                    "valor_total": "370.00",
                }
            ]
        })

        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_instance

        itens = extract_nfe_items_with_gemini(b"%PDF-1.4 dummy")
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["descricao"], "Café Torrado 500g")
        self.assertEqual(itens[0]["valor_total"], Decimal("370.00"))

    @override_settings(GEMINI_API_KEY="test-api-key")
    @patch("estoque.pdf_import.gemini_extractor.genai.GenerativeModel")
    @patch("estoque.pdf_import.gemini_extractor.genai.configure")
    def test_falha_api_levanta_runtime_error(self, mock_configure, mock_model_class):
        mock_instance = MagicMock()
        mock_instance.generate_content.side_effect = Exception("Google API Quota Exceeded")
        mock_model_class.return_value = mock_instance

        with self.assertRaises(RuntimeError) as ctx:
            extract_nfe_items_with_gemini(b"%PDF-1.4 dummy")
        self.assertIn("Falha na extração de itens via Gemini", str(ctx.exception))
