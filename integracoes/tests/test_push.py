"""Testes para o serviço de PUSH (Django → Google Sheets) e comando associado (Bloco 3)."""

from datetime import timedelta
from unittest.mock import MagicMock, patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from integracoes.exceptions import SheetsSyncDisabledError
from integracoes.models import (
    SheetRowSnapshot,
    SheetSyncState,
    SyncOperation,
    SyncOperationRecord,
)
from integracoes.services.push import push_to_sheets
from material_belico.models import PistolaGlock


@override_settings(SHEETS_SYNC_ENABLED=True, NEW_SPREADSHEET_ID="test-new-sheet-123")
class PushToSheetsServiceTests(TestCase):
    """Testa regras de negócio, marco temporal, batch_update e append_row do push_to_sheets."""

    def setUp(self):
        self.glock = PistolaGlock.objects.create(
            numero_serie="GLK-PUSH-01",
            patrimonio="PAT-PUSH-01",
            modelo="PISTOLA GLOCK G22 G5 .40",
            situacao_reserva="ok",
        )

    def test_guard_sheets_sync_disabled_raises_error(self):
        with override_settings(SHEETS_SYNC_ENABLED=False):
            with self.assertRaises(SheetsSyncDisabledError):
                push_to_sheets(model_name="PistolaGlock")

    @patch("integracoes.services.push.create_db_backup")
    @patch("integracoes.services.push.batch_update")
    @patch("integracoes.services.push.append_row")
    def test_so_envia_objetos_com_data_atualizacao_maior_que_marco(
        self, mock_append, mock_batch_update, mock_backup
    ):
        mock_backup.return_value = "/tmp/dummy.sql"

        # Define marco futuro em relação à glock existente
        future_marco = self.glock.data_atualizacao + timedelta(minutes=5)

        summary = push_to_sheets(
            model_name="PistolaGlock", dry_run=False, since=future_marco
        )

        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["created"], 0)
        self.assertEqual(summary["updated"], 0)
        self.assertFalse(mock_append.called)
        self.assertFalse(mock_batch_update.called)

    @patch("integracoes.services.push.create_db_backup")
    @patch("integracoes.services.push.append_row")
    def test_novo_objeto_sem_snapshot_chama_append_row_e_cria_snapshot(
        self, mock_append, mock_backup
    ):
        mock_backup.return_value = "/tmp/dummy.sql"
        mock_append.return_value = {"updates": {"updatedRange": "Pistolas_Glock!A5:I5"}}

        # Define marco no passado para capturar a glock criada no setUp
        past_marco = self.glock.data_atualizacao - timedelta(minutes=10)

        # Garante que não há snapshot prévio
        self.assertEqual(
            SheetRowSnapshot.objects.filter(
                model_name="PistolaGlock", lookup_value=str(self.glock.pk)
            ).count(),
            0,
        )

        summary = push_to_sheets(
            model_name="PistolaGlock", dry_run=False, since=past_marco
        )

        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["created"], 1)
        self.assertTrue(mock_append.called)

        # Snapshot deve ter sido criado com a linha extraída (linha 5)
        snapshot = SheetRowSnapshot.objects.get(
            model_name="PistolaGlock", lookup_value=str(self.glock.pk)
        )
        self.assertEqual(snapshot.row_number, 5)
        self.assertIsNotNone(snapshot.content_hash)

        # Registro de auditoria criado
        self.assertTrue(
            SyncOperationRecord.objects.filter(
                model_name="PistolaGlock", action="CREATE", status="SUCCESS"
            ).exists()
        )

    @patch("integracoes.services.push.create_db_backup")
    @patch("integracoes.services.push.batch_update")
    def test_objeto_com_snapshot_acumula_e_chama_batch_update(
        self, mock_batch_update, mock_backup
    ):
        mock_backup.return_value = "/tmp/dummy.sql"

        # Cria snapshot prévio indicando linha 3
        snapshot = SheetRowSnapshot.objects.create(
            model_name="PistolaGlock",
            lookup_key="id",
            lookup_value=str(self.glock.pk),
            row_number=3,
            content_hash="hash-antigo",
        )

        past_marco = self.glock.data_atualizacao - timedelta(minutes=10)

        summary = push_to_sheets(
            model_name="PistolaGlock", dry_run=False, since=past_marco
        )

        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["updated"], 1)
        self.assertTrue(mock_batch_update.called)

        # Verifica chamada com range explícito A3:I3
        args, kwargs = mock_batch_update.call_args
        self.assertEqual(args[0], "new")
        payload = args[1]
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["range"], "'Pistolas_Glock'!A3:I3")

        # Snapshot teve content_hash atualizado
        snapshot.refresh_from_db()
        self.assertNotEqual(snapshot.content_hash, "hash-antigo")


@override_settings(SHEETS_SYNC_ENABLED=True, NEW_SPREADSHEET_ID="test-new-sheet-123")
class PushToSheetsCommandTests(TestCase):
    """Testa o management command push_to_sheets."""

    def test_command_requires_confirm_or_dry_run(self):
        with self.assertRaises(CommandError) as ctx:
            call_command("push_to_sheets")

        self.assertIn("requer --confirm", str(ctx.exception))

    @patch("integracoes.management.commands.push_to_sheets.push_to_sheets")
    def test_command_executes_with_confirm_flag(self, mock_push):
        mock_push.return_value = {
            "status": "SUCCESS",
            "total": 3,
            "created": 1,
            "updated": 2,
            "skipped": 0,
            "errors": 0,
            "operation_id": 1,
        }

        call_command("push_to_sheets", "--confirm", "--model", "PistolaGlock")
        mock_push.assert_called_once_with(
            model_name="PistolaGlock",
            dry_run=False,
            since=None,
        )

    @patch("integracoes.management.commands.push_to_sheets.push_to_sheets")
    def test_command_handles_failed_status_with_command_error(self, mock_push):
        mock_push.return_value = {
            "status": "FAILED",
            "total": 3,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 3,
            "operation_id": 2,
        }

        with self.assertRaises(CommandError) as ctx:
            call_command("push_to_sheets", "--confirm")

        self.assertIn("[FALHA]", str(ctx.exception))
