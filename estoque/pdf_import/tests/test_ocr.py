import io
import os
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase

from estoque.pdf_import.ocr import (
    extract_text_raw,
    get_lang,
    read_file_bytes,
    ensure_tesseract,
)

class OCRTests(TestCase):
    def setUp(self):
        self.fixture_dir = Path(__file__).resolve().parent / "fixtures"
        self.nfe_pdf = self.fixture_dir / "nfe_sample.pdf"

    def test_get_lang_retorna_por_quando_instalado(self):
        lang = get_lang()
        self.assertEqual(lang, "por")

    def test_extract_text_raw_nfe_sample(self):
        self.assertTrue(self.nfe_pdf.exists(), "Fixture nfe_sample.pdf não encontrada.")
        text = extract_text_raw(self.nfe_pdf)
        
        self.assertGreater(len(text), 1000, f"Texto extraído ({len(text)} chars) menor que 1000 chars.")
        self.assertIn("DANFE", text)
        self.assertIn("000362", text)

    def test_extract_text_raw_com_bytesio(self):
        with open(self.nfe_pdf, "rb") as f:
            buf = io.BytesIO(f.read())
        text = extract_text_raw(buf)
        self.assertIn("DANFE", text)

    def test_read_file_bytes_com_diferentes_tipos(self):
        # 1. Path
        b1 = read_file_bytes(self.nfe_pdf)
        self.assertTrue(b1.startswith(b"%PDF-"))

        # 2. BytesIO (cursor preservado)
        buf = io.BytesIO(b"teste_bytes_io")
        b2 = read_file_bytes(buf)
        self.assertEqual(b2, b"teste_bytes_io")
        self.assertEqual(buf.tell(), 0)

        # 3. Bytes direto
        b3 = read_file_bytes(b"bytes_diretos")
        self.assertEqual(b3, b"bytes_diretos")

    @patch("estoque.pdf_import.ocr.get_tesseract_cmd", return_value="")
    def test_ensure_tesseract_levanta_runtime_error_quando_nao_encontrado(self, mock_cmd):
        with self.assertRaises(RuntimeError) as ctx:
            ensure_tesseract()
        self.assertIn("Tesseract-OCR não foi encontrado", str(ctx.exception))
