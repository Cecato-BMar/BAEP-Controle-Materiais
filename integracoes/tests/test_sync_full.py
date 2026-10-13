"""Testes para o serviço e comando de seed inicial e idempotência (Bloco 3)."""

from unittest.mock import MagicMock, patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from integracoes.mapping import NEW_SHEET_MAP
from integracoes.models import (
    SheetRowSnapshot,
    SheetSyncState,
    SyncOperation,
    SyncOperationRecord,
)
from integracoes.services.sync_full import seed_new_spreadsheet
from material_belico.models import PistolaGlock

ALL_TITLES = [conf["sheet"] for conf in NEW_SHEET_MAP.values()]


@override_settings(SHEETS_SYNC_ENABLED=True, NEW_SPREADSHEET_ID="test-new-sheet-123")
class SeedSpreadsheetIdempotencyTests(TestCase):
    """Testa o comportamento de idempotência, guard de já executado e clear+rewrite do seed."""

    def setUp(self):
        self.glock = PistolaGlock.objects.create(
            numero_serie="GLK-SEED-01",
            patrimonio="PAT-SEED-01",
            modelo="PISTOLA GLOCK G22 G5 .40",
            situacao_reserva="ok",
        )

    def test_seed_sem_force_com_snapshot_existente_levanta_runtime_error(self):
        # Cria um snapshot pré-existente
        SheetRowSnapshot.objects.create(
            model_name="PistolaGlock",
            lookup_key="numero_serie",
            lookup_value="GLK-OLD",
            row_number=2,
            content_hash="old-hash-123",
        )

        with self.assertRaises(RuntimeError) as ctx:
            seed_new_spreadsheet(dry_run=False, force=False)

        self.assertIn("Seed já foi executado", str(ctx.exception))
        self.assertIn("Use --force", str(ctx.exception))

    @patch("integracoes.services.sync_full.list_sheet_titles")
    @patch("integracoes.services.sync_full.clear")
    @patch("integracoes.services.sync_full.update_row")
    @patch("integracoes.services.sync_full.append_row")
    def test_seed_com_force_true_chama_clear_e_reescreve(
        self, mock_append, mock_update, mock_clear, mock_titles
    ):
        mock_titles.return_value = list(ALL_TITLES)
        mock_append.return_value = {"updates": {"updatedRange": "Pistolas_Glock!A2:H2"}}

        # Cria snapshot pré-existente
        SheetRowSnapshot.objects.create(
            model_name="PistolaGlock",
            lookup_key="numero_serie",
            lookup_value="GLK-SEED-01",
            row_number=99,
            content_hash="dummy",
        )

        summary = seed_new_spreadsheet(dry_run=False, force=True)

        self.assertEqual(summary["status"], "SUCCESS")
        # Deve ter chamado clear para as abas
        self.assertTrue(mock_clear.called)
        # Deve ter atualizado header na linha 1
        self.assertTrue(mock_update.called)
        # Deve ter feito append_row com as linhas
        self.assertTrue(mock_append.called)

        # Snapshot deve ter sido recriado
        snapshot = SheetRowSnapshot.objects.get(
            model_name="PistolaGlock", lookup_value=str(self.glock.pk)
        )
        self.assertEqual(snapshot.row_number, 2)

    @patch("integracoes.services.sync_full.batch_update")
    @patch("integracoes.services.sync_full.list_sheet_titles")
    @patch("integracoes.services.sync_full.read_all")
    @patch("integracoes.services.sync_full.update_row")
    @patch("integracoes.services.sync_full.append_row")
    def test_seed_em_planilha_limpa_funciona_normalmente(
        self, mock_append, mock_update, mock_read_all, mock_titles, mock_batch_update
    ):
        mock_titles.return_value = list(ALL_TITLES)
        mock_read_all.return_value = []
        mock_append.return_value = {"updates": {"updatedRange": "Pistolas_Glock!A2:H2"}}

        self.assertEqual(SheetRowSnapshot.objects.count(), 0)

        summary = seed_new_spreadsheet(dry_run=False, force=False)

        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["created"], 1)

        # Snapshots criados
        self.assertTrue(
            SheetRowSnapshot.objects.filter(model_name="PistolaGlock").exists()
        )
        self.assertTrue(
            SyncOperationRecord.objects.filter(model_name="PistolaGlock").exists()
        )

    @patch("integracoes.services.sync_full.list_sheet_titles")
    @patch("integracoes.services.sync_full.read_all")
    def test_seed_sem_force_com_conteudo_em_aba_mas_snapshot_vazio_aborta(
        self, mock_read_all, mock_titles
    ):
        mock_titles.return_value = list(ALL_TITLES)
        # Aba já possui dados na planilha
        mock_read_all.return_value = [["Header1", "Header2"], ["Val1", "Val2"]]

        self.assertEqual(SheetRowSnapshot.objects.count(), 0)

        with self.assertRaises(RuntimeError) as ctx:
            seed_new_spreadsheet(dry_run=False, force=False)

        self.assertIn("já possui conteúdo na planilha nova", str(ctx.exception))
        self.assertIn("Use --force", str(ctx.exception))

        # A operação deve ter sido registrada como FAILED
        last_op = SyncOperation.objects.filter(operation_type="SEED").latest("started_at")
        self.assertEqual(last_op.status, "FAILED")


@override_settings(SHEETS_SYNC_ENABLED=True, NEW_SPREADSHEET_ID="test-new-sheet-123")
class SyncFullSheetsCommandTests(TestCase):
    """Testa o management command sync_full_sheets com a flag --force e --seed."""

    @patch("integracoes.management.commands.sync_full_sheets.seed_new_spreadsheet")
    def test_command_seed_passes_force_and_dry_run_flags(self, mock_seed):
        mock_seed.return_value = {
            "status": "SUCCESS",
            "created": 10,
            "errors": 0,
            "operation_id": 1,
        }

        call_command("sync_full_sheets", "--seed", "--force", "--dry-run")
        mock_seed.assert_called_once_with(dry_run=True, force=True)

    @patch("integracoes.management.commands.sync_full_sheets.seed_new_spreadsheet")
    def test_command_seed_handles_failure_gracefully(self, mock_seed):
        mock_seed.side_effect = RuntimeError("Seed já foi executado")

        with self.assertRaises(CommandError) as ctx:
            call_command("sync_full_sheets", "--seed")

        self.assertIn("Falha ao executar seed_new_spreadsheet", str(ctx.exception))
