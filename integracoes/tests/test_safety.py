"""Testes de segurança e isolamento para a integração com Google Sheets."""

from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings

from integracoes.exceptions import (
    GoogleSheetsAuthError,
    LegacySheetWriteForbidden,
)
from integracoes.google_client import (
    READONLY_SCOPES,
    FULL_SCOPES,
    _assert_write_allowed,
    append_row,
    append_sheet_values,
    batch_update,
    batch_update_spreadsheet,
    clear,
    clear_sheet_values,
    get_legacy_service,
    get_new_service,
    update_row,
    update_sheet_values,
)
from integracoes.models import SyncOperation, SyncOperationRecord


class GoogleClientSafetyTests(TestCase):
    """Garante que a planilha legada NUNCA possa ser alvo de operações de escrita.
    
    Os testes de barreira rodam contra o código REAL (sem mocks da barreira):
    a exceção LegacySheetWriteForbidden é disparada antes de qualquer chamada HTTP.
    """

    def setUp(self):
        self.legacy_id = "test-legacy-spreadsheet-id-12345"
        self.new_id = "test-new-spreadsheet-id-67890"

    def test_assert_write_allowed_blocks_keyword_legacy(self):
        with self.assertRaises(LegacySheetWriteForbidden):
            _assert_write_allowed("legacy")

    def test_assert_write_allowed_blocks_legacy_spreadsheet_id(self):
        with override_settings(LEGACY_SPREADSHEET_ID=self.legacy_id):
            with self.assertRaises(LegacySheetWriteForbidden):
                _assert_write_allowed(self.legacy_id)

    def test_assert_write_allowed_permits_new_target(self):
        with override_settings(NEW_SPREADSHEET_ID=self.new_id):
            resolved = _assert_write_allowed("new")
            self.assertEqual(resolved, self.new_id)

    def test_assert_write_allowed_permits_custom_new_id(self):
        with override_settings(LEGACY_SPREADSHEET_ID=self.legacy_id, NEW_SPREADSHEET_ID=self.new_id):
            resolved = _assert_write_allowed("custom-other-id")
            self.assertEqual(resolved, "custom-other-id")

    def test_update_row_raises_for_legacy(self):
        with override_settings(LEGACY_SPREADSHEET_ID=self.legacy_id):
            with self.assertRaises(LegacySheetWriteForbidden):
                update_row("legacy", "A1:B2", [["1", "2"]])

            with self.assertRaises(LegacySheetWriteForbidden):
                update_row(self.legacy_id, "A1:B2", [["1", "2"]])

            with self.assertRaises(LegacySheetWriteForbidden):
                update_sheet_values(self.legacy_id, "A1:B2", [["1", "2"]])

    def test_append_row_raises_for_legacy(self):
        with override_settings(LEGACY_SPREADSHEET_ID=self.legacy_id):
            with self.assertRaises(LegacySheetWriteForbidden):
                append_row("legacy", "A1:B2", [["1", "2"]])

            with self.assertRaises(LegacySheetWriteForbidden):
                append_row(self.legacy_id, "A1:B2", [["1", "2"]])

            with self.assertRaises(LegacySheetWriteForbidden):
                append_sheet_values(self.legacy_id, "A1:B2", [["1", "2"]])

    def test_clear_raises_for_legacy(self):
        with override_settings(LEGACY_SPREADSHEET_ID=self.legacy_id):
            with self.assertRaises(LegacySheetWriteForbidden):
                clear("legacy", "A1:B2")

            with self.assertRaises(LegacySheetWriteForbidden):
                clear(self.legacy_id, "A1:B2")

            with self.assertRaises(LegacySheetWriteForbidden):
                clear_sheet_values(self.legacy_id, "A1:B2")

    def test_batch_update_raises_for_legacy(self):
        with override_settings(LEGACY_SPREADSHEET_ID=self.legacy_id):
            with self.assertRaises(LegacySheetWriteForbidden):
                batch_update("legacy", [])

            with self.assertRaises(LegacySheetWriteForbidden):
                batch_update(self.legacy_id, [])

            with self.assertRaises(LegacySheetWriteForbidden):
                batch_update_spreadsheet(self.legacy_id, [])

    @override_settings(GOOGLE_SERVICE_ACCOUNT_INFO=None)
    def test_auth_error_raised_when_service_account_missing(self):
        with self.assertRaises(GoogleSheetsAuthError):
            get_legacy_service()

        with self.assertRaises(GoogleSheetsAuthError):
            get_new_service()

    @patch("integracoes.google_client.service_account.Credentials.from_service_account_info")
    @patch("integracoes.google_client.build")
    def test_services_use_correct_scopes(self, mock_build, mock_from_info):
        fake_sa = {"type": "service_account", "client_email": "test@baep.iam.gserviceaccount.com"}
        with override_settings(GOOGLE_SERVICE_ACCOUNT_INFO=fake_sa):
            get_legacy_service()
            mock_from_info.assert_called_with(fake_sa, scopes=READONLY_SCOPES)

            get_new_service()
            mock_from_info.assert_called_with(fake_sa, scopes=FULL_SCOPES)


class SyncOperationModelsTests(TestCase):
    """Testa a criação e integridade dos models SyncOperation e SyncOperationRecord."""

    def test_create_sync_operation_and_records(self):
        op = SyncOperation.objects.create(
            operation_type="IMPORT_LEGACY",
            status="IN_PROGRESS",
            total_records=10,
        )
        self.assertIsNotNone(op.pk)
        self.assertEqual(op.created_count, 0)
        self.assertEqual(op.status, "IN_PROGRESS")

        rec1 = SyncOperationRecord.objects.create(
            operation=op,
            model_name="PistolaGlock",
            lookup_key="numero_serie",
            lookup_value="BOPM12345",
            action="CREATE",
            status="SUCCESS",
            sheet_name="PISTOLAS GLOCK",
            row_number=2,
            after_snapshot={"numero_serie": "BOPM12345", "modelo": "G22"},
        )
        self.assertEqual(rec1.operation, op)
        self.assertEqual(op.records.count(), 1)

        # Atualiza a operação
        op.status = "SUCCESS"
        op.created_count = 1
        op.save()
        self.assertEqual(SyncOperation.objects.get(pk=op.pk).status, "SUCCESS")
