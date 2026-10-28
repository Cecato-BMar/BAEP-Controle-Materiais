import datetime
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from licenciamento.license_core import LicenseManager
from licenciamento.models import LicenseRecord


class ExtrairPdfsViewTests(TestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.url = reverse("estoque:extrair_pdfs")

        # Garante licença ativa para os testes HTTP (LicenseCheckMiddleware)
        token = LicenseManager.generate_token('baep-teste', '2º BAEP Testes', 365)
        is_valid, payload = LicenseManager.verify_token(token)
        expires_at = datetime.datetime.fromtimestamp(payload['exp'], tz=datetime.timezone.utc)
        issued_at = datetime.datetime.fromtimestamp(payload['iat'], tz=datetime.timezone.utc)
        LicenseRecord.objects.create(
            client_id='baep-teste',
            client_name='2º BAEP Testes',
            token_base64=token,
            issued_at=issued_at,
            expires_at=expires_at,
            is_active=True
        )

        # Usuário autorizado no módulo materiais
        self.user_autorizado = User.objects.create_user(
            username="operador_estoque", password="password123"
        )
        self.grupo_materiais, _ = Group.objects.get_or_create(name="materiais")
        self.user_autorizado.groups.add(self.grupo_materiais)

        # Usuário sem grupo de permissão
        self.user_sem_permissao = User.objects.create_user(
            username="usuario_sem_permissao", password="password123"
        )

        self.fixtures_dir = (
            Path(__file__).resolve().parent.parent / "pdf_import" / "tests" / "fixtures"
        )

    def test_rejeita_sem_login(self):
        # Requisição não autenticada deve redirecionar para tela de login
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 302)

    def test_rejeita_sem_permissao(self):
        # Usuário logado mas sem pertencer ao grupo 'estoque' recebe 403 Forbidden
        self.client.force_login(self.user_sem_permissao)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 403)

    def test_rejeita_sem_nenhum_pdf(self):
        self.client.force_login(self.user_autorizado)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("Envie a NFe", data["error"])

    def test_rejeita_arquivo_nao_pdf(self):
        self.client.force_login(self.user_autorizado)
        txt_file = SimpleUploadedFile("nota.txt", b"Texto simples", content_type="text/plain")
        pdf_file = SimpleUploadedFile("empenho.pdf", b"%PDF-1.4 teste", content_type="application/pdf")
        response = self.client.post(
            self.url,
            {"nfe_pdf": txt_file, "empenho_pdf": pdf_file},
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("inválido", data["error"].lower())

    def test_rejeita_arquivo_maior_10mb(self):
        self.client.force_login(self.user_autorizado)
        # 11 MB
        large_content = b"%PDF-" + (b"A" * (11 * 1024 * 1024))
        large_pdf = SimpleUploadedFile("grande.pdf", large_content, content_type="application/pdf")
        normal_pdf = SimpleUploadedFile("empenho.pdf", b"%PDF-1.4 teste", content_type="application/pdf")
        response = self.client.post(
            self.url,
            {"nfe_pdf": large_pdf, "empenho_pdf": normal_pdf},
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("10 MB", data["error"])

    def test_sucesso_retorna_200_com_json(self):
        self.client.force_login(self.user_autorizado)
        nfe_path = self.fixtures_dir / "nfe_sample.pdf"
        empenho_path = self.fixtures_dir / "empenho_sample.pdf"

        with open(nfe_path, "rb") as f_nfe, open(empenho_path, "rb") as f_emp:
            nfe_upload = SimpleUploadedFile(
                "nfe_sample.pdf", f_nfe.read(), content_type="application/pdf"
            )
            emp_upload = SimpleUploadedFile(
                "empenho_sample.pdf", f_emp.read(), content_type="application/pdf"
            )

        response = self.client.post(
            self.url,
            {"nfe_pdf": nfe_upload, "empenho_pdf": emp_upload},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Valida que o JSON possui a estrutura de retorno completa
        self.assertIn("nfe", data)
        self.assertIn("empenho", data)
        self.assertIn("validation", data)
        self.assertIn("matches", data)
        self.assertIn("header_suggestions", data)
        self.assertEqual(data["header_suggestions"]["nota_fiscal"], "000362")
        self.assertEqual(data["header_suggestions"]["documento_referencia"], "2026NE01176")
        self.assertEqual(len(data["matches"]), 3)

    def test_aceita_apenas_nfe(self):
        self.client.force_login(self.user_autorizado)
        nfe_path = self.fixtures_dir / "nfe_sample.pdf"

        with open(nfe_path, "rb") as f_nfe:
            nfe_upload = SimpleUploadedFile(
                "nfe_sample.pdf", f_nfe.read(), content_type="application/pdf"
            )

        response = self.client.post(
            self.url,
            {"nfe_pdf": nfe_upload},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("nfe", data)
        self.assertEqual(data["empenho"], {})
        self.assertTrue(data["validation"]["valid"])
        self.assertEqual(len(data["matches"]), 3)
        self.assertEqual(data["header_suggestions"]["nota_fiscal"], "000362")
        self.assertEqual(data["header_suggestions"]["documento_referencia"], "2026NE01176")
