import io
from pathlib import Path
from django.test import TestCase
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from estoque.pdf_import.detectors import detect_pdf_type, TYPE_NFE, TYPE_EMPENHO, TYPE_UNKNOWN

class DetectorsTests(TestCase):
    def setUp(self):
        self.fixture_dir = Path(__file__).resolve().parent / "fixtures"
        self.nfe_pdf = self.fixture_dir / "nfe_sample.pdf"
        self.empenho_pdf = self.fixture_dir / "empenho_sample.pdf"

    def test_detecta_nfe(self):
        self.assertTrue(self.nfe_pdf.exists(), "nfe_sample.pdf não encontrado")
        tipo = detect_pdf_type(self.nfe_pdf)
        self.assertEqual(tipo, TYPE_NFE)

    def test_detecta_empenho(self):
        self.assertTrue(self.empenho_pdf.exists(), "empenho_sample.pdf não encontrado")
        tipo = detect_pdf_type(self.empenho_pdf)
        self.assertEqual(tipo, TYPE_EMPENHO)

    def test_detecta_unknown_para_documento_generico(self):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        c.drawString(100, 750, "Relatório Geral do Batalhão de Ações Especiais")
        c.save()
        buf.seek(0)
        
        tipo = detect_pdf_type(buf)
        self.assertEqual(tipo, TYPE_UNKNOWN)

    def test_detecta_unknown_para_bytes_invalidos(self):
        tipo = detect_pdf_type(b"conteudo_invalido_que_nao_e_pdf")
        self.assertEqual(tipo, TYPE_UNKNOWN)
