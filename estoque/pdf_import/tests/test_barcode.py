from pathlib import Path
from django.test import TestCase

from estoque.pdf_import.ocr import read_chave_from_barcode

class BarcodeTests(TestCase):
    def setUp(self):
        self.fixture_dir = Path(__file__).resolve().parent / "fixtures"
        self.nfe_pdf = self.fixture_dir / "nfe_sample.pdf"
        self.empenho_pdf = self.fixture_dir / "empenho_sample.pdf"

    def test_read_chave_from_barcode_nfe_sample(self):
        self.assertTrue(self.nfe_pdf.exists(), "Fixture nfe_sample.pdf não encontrada.")
        chave = read_chave_from_barcode(self.nfe_pdf)
        self.assertEqual(chave, "35261064490977000117550010000003621297599470")

    def test_read_chave_from_barcode_sem_barcode_retorna_none(self):
        chave = read_chave_from_barcode(self.empenho_pdf)
        self.assertIsNone(chave)

    def test_read_chave_from_barcode_arquivo_invalido_retorna_none(self):
        chave = read_chave_from_barcode(b"arquivo_nao_pdf_corrompido")
        self.assertIsNone(chave)
