import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from estoque.pdf_import.gemini_extractor import extract_nfe_items_with_gemini


class GeminiExtractorTests(SimpleTestCase):
    @override_settings(GEMINI_API_KEY="")
    def test_sem_api_key_retorna_lista_vazia(self):
        with patch.dict("os.environ", {}, clear=True):
            itens = extract_nfe_items_with_gemini(b"%PDF-1.4 dummy")
        self.assertEqual(itens, [])

    @override_settings(GEMINI_API_KEY="test-api-key")
    @patch("estoque.pdf_import.gemini_extractor.genai.Client")
    def test_extracao_sucesso(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "itens": [
                {
                    "codigo": "001",
                    "descricao": "Margarina Becel 500g",
                    "ncm": "15171000",
                    "cfop": "5102",
                    "unidade": "UN",
                    "quantidade": 40.0,
                    "valor_unitario": 9.8,
                    "valor_total": 392.0,
                },
                {
                    "codigo": "002",
                    "descricao": "Adoçante Líquido 100ml",
                    "ncm": "29251100",
                    "cfop": "5102",
                    "unidade": "UN",
                    "quantidade": 36.0,
                    "valor_unitario": 6.1,
                    "valor_total": 219.6,
                },
            ]
        })

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        itens = extract_nfe_items_with_gemini(b"%PDF-1.4 dummy")

        mock_client_class.assert_called_once_with(api_key="test-api-key")
        self.assertEqual(len(itens), 2)

        it1 = itens[0]
        self.assertEqual(it1["codigo"], "001")
        self.assertEqual(it1["descricao"], "Margarina Becel 500g")
        self.assertEqual(it1["quantidade"], Decimal("40.0"))
        self.assertEqual(it1["valor_unitario"], Decimal("9.8"))
        self.assertEqual(it1["valor_total"], Decimal("392.0"))

        it2 = itens[1]
        self.assertEqual(it2["codigo"], "002")
        self.assertEqual(it2["descricao"], "Adoçante Líquido 100ml")
        self.assertEqual(it2["quantidade"], Decimal("36.0"))
        self.assertEqual(it2["valor_unitario"], Decimal("6.1"))
        self.assertEqual(it2["valor_total"], Decimal("219.6"))

    @override_settings(GEMINI_API_KEY="test-api-key")
    @patch("estoque.pdf_import.gemini_extractor.genai.Client")
    def test_falha_api_retorna_lista_vazia(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("Google API Quota Exceeded")
        mock_client_class.return_value = mock_client

        itens = extract_nfe_items_with_gemini(b"%PDF-1.4 dummy")
        self.assertEqual(itens, [])
