"""Testes para o serviço de importação da planilha antiga (import_legacy_sheet)."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from integracoes.backup import serialize_instance
from integracoes.exceptions import ImportDisabledError
from integracoes.models import SyncOperation, SyncOperationRecord
from integracoes.services.import_legacy import import_legacy_sheet
from materiais.sync_to_belico import is_syncing
from material_belico.models import PistolaGlock


@override_settings(IMPORT_ENABLED=True)
class ImportLegacyServiceTests(TestCase):
    """Testa a lógica do serviço import_legacy_sheet."""


    def setUp(self):
        self.mock_glock_data = [
            {
                "_row_number": 2,
                "patrimonio": "PAT-G01",
                "numero_serie": "BOPM99001",
                "modelo": "PISTOLA GLOCK G22 G5 .40",
                "cod_opm": "CPI-6",
                "unidade": "2.BAEP",
                "situacao_reserva": "OK",
                "observacoes": "Arma em bom estado",
            },
            {
                "_row_number": 3,
                "patrimonio": "PAT-G02",
                "numero_serie": "BOPM99002",
                "modelo": "PISTOLA GLOCK G22 G5 .40",
                "cod_opm": "CPI-6",
                "unidade": "2.BAEP",
                "situacao_reserva": "EM USO",
                "observacoes": "Em carga com operador",
            },
        ]

    def test_guard_without_confirm_raises_value_error(self):
        with self.assertRaises(ValueError):
            import_legacy_sheet(dry_run=False, confirm=False)

    @override_settings(IMPORT_ENABLED=False)
    def test_guard_with_import_disabled_raises_error(self):
        with self.assertRaises(ImportDisabledError):
            import_legacy_sheet(dry_run=False, confirm=True)

    @patch("integracoes.services.import_legacy.create_db_backup", return_value="dummy.sql.gz")
    @patch("integracoes.services.import_legacy.read_sheet_as_dicts")
    def test_dry_run_does_not_modify_database(self, mock_read, mock_backup):
        def side_effect(sheet_name, **kwargs):
            if sheet_name == "PISTOLAS GLOCK":
                return list(self.mock_glock_data)
            return []

        mock_read.side_effect = side_effect

        summary = import_legacy_sheet(dry_run=True)
        self.assertTrue(summary["dry_run"])
        self.assertEqual(summary["created"], 2)
        # Nenhuma arma criada no banco real
        self.assertEqual(PistolaGlock.objects.count(), 0)

    @patch("integracoes.services.import_legacy.create_db_backup", return_value="dummy.sql.gz")
    @patch("integracoes.services.import_legacy.read_sheet_as_dicts")
    def test_real_import_creates_and_updates_with_audit_trail(self, mock_read, mock_backup):
        def side_effect(sheet_name, **kwargs):
            if sheet_name == "PISTOLAS GLOCK":
                return [dict(d) for d in self.mock_glock_data]
            return []

        mock_read.side_effect = side_effect

        # 1. Primeira execução: criação
        summary1 = import_legacy_sheet(dry_run=False, confirm=True)
        self.assertEqual(summary1["created"], 2)
        self.assertEqual(summary1["updated"], 0)
        self.assertEqual(PistolaGlock.objects.count(), 2)

        op1 = SyncOperation.objects.get(pk=summary1["operation_id"])
        self.assertEqual(op1.status, "SUCCESS")
        self.assertEqual(op1.records.filter(action="CREATE").count(), 2)

        rec = op1.records.get(lookup_value="PAT-G01")
        self.assertIsNone(rec.before_snapshot)
        self.assertIsNotNone(rec.after_snapshot)
        self.assertEqual(rec.after_snapshot["numero_serie"], "BOPM99001")

        # 2. Segunda execução (idempotência / atualização):
        summary2 = import_legacy_sheet(dry_run=False, confirm=True)
        self.assertEqual(summary2["created"], 0)
        self.assertEqual(summary2["updated"], 2)
        self.assertEqual(PistolaGlock.objects.count(), 2)

        op2 = SyncOperation.objects.get(pk=summary2["operation_id"])
        self.assertEqual(op2.records.filter(action="UPDATE").count(), 2)
        rec_update = op2.records.get(lookup_value="PAT-G01")
        self.assertIsNotNone(rec_update.before_snapshot)
        self.assertIsNotNone(rec_update.after_snapshot)

    @patch("integracoes.services.import_legacy.create_db_backup", return_value="dummy.sql.gz")
    @patch("integracoes.services.import_legacy.read_sheet_as_dicts")
    def test_validation_error_is_recorded_as_error_and_does_not_abort_batch(self, mock_read, mock_backup):
        # Linha 1 válida, Linha 2 com número de série duplicado ou erro de banco
        corrupted_data = [
            {
                "_row_number": 2,
                "patrimonio": "PAT-OK",
                "numero_serie": "SERIE-OK",
                "modelo": "PISTOLA GLOCK G22 G5 .40",
                "cod_opm": "CPI-6",
                "unidade": "2.BAEP",
                "situacao_reserva": "ok",
            },
        ]
        # Cria pré-existente para simular colisão de unique
        PistolaGlock.objects.create(patrimonio="OUTRO", numero_serie="SERIE-OK")

        def side_effect(sheet_name, **kwargs):
            if sheet_name == "PISTOLAS GLOCK":
                return [dict(d) for d in corrupted_data]
            return []

        mock_read.side_effect = side_effect

        summary = import_legacy_sheet(dry_run=False, confirm=True)
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["status"], "FAILED")

        op = SyncOperation.objects.get(pk=summary["operation_id"])
        self.assertEqual(op.records.filter(status="ERROR").count(), 1)
        err_rec = op.records.get(status="ERROR")
        self.assertIn("UNIQUE", err_rec.error_detail.upper())

    def test_sync_lock_is_released_after_run(self):
        self.assertFalse(is_syncing())
        with patch("integracoes.services.import_legacy.read_sheet_as_dicts", return_value=[]):
            import_legacy_sheet(dry_run=True)
        self.assertFalse(is_syncing())


class ImportLegacyCommandTests(TestCase):
    """Testa o comando python manage.py import_legacy_sheet."""

    def test_command_requires_confirm_or_dry_run(self):
        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("import_legacy_sheet", stdout=out)
        self.assertIn("--confirm", str(ctx.exception))

    @patch("integracoes.services.import_legacy.create_db_backup", return_value="dummy.sql.gz")
    @patch("integracoes.services.import_legacy.read_sheet_as_dicts", return_value=[])
    def test_command_dry_run_executes_successfully(self, mock_read, mock_backup):
        out = StringIO()
        call_command("import_legacy_sheet", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("SIMULAÇÃO (DRY-RUN)", output)
        self.assertIn("Processamento da planilha legada concluido", output)
        self.assertIn("[OK]", output)
        self.assertIn("Status final: SUCCESS", output)
