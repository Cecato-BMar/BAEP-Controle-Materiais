"""Testes para o serviço de PULL (Google Sheets → Django) e comando associado (Bloco 3)."""

from datetime import timedelta
from unittest.mock import MagicMock, patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from integracoes.exceptions import SheetsSyncDisabledError
from integracoes.mapping import NEW_SHEET_MAP
from integracoes.models import (
    SheetRowSnapshot,
    SheetSyncState,
    SyncOperation,
    SyncOperationRecord,
)
from integracoes.services.pull import pull_from_sheets
from integracoes.services.sync_full import compute_content_hash
from material_belico.models import PistolaGlock


@override_settings(SHEETS_SYNC_ENABLED=True, NEW_SPREADSHEET_ID="test-new-sheet-123")
class PullFromSheetsServiceTests(TestCase):
    """Testa regras de negócio, hash, Last Write Wins e integridade do pull_from_sheets."""

    def setUp(self):
        self.glock = PistolaGlock.objects.create(
            numero_serie="GLK-PULL-01",
            patrimonio="PAT-PULL-01",
            modelo="PISTOLA GLOCK G22 G5 .40",
            situacao_reserva="ok",
        )
        self.columns = NEW_SHEET_MAP["PistolaGlock"]["columns"]

    def test_guard_sheets_sync_disabled_raises_error(self):
        with override_settings(SHEETS_SYNC_ENABLED=False):
            with self.assertRaises(SheetsSyncDisabledError):
                pull_from_sheets(model_name="PistolaGlock")

    @patch("integracoes.services.pull.create_db_backup")
    @patch("integracoes.services.pull.read_all")
    def test_hash_igual_ignora_e_nao_toca_no_banco(self, mock_read_all, mock_backup):
        mock_backup.return_value = "/tmp/dummy.sql"

        # Linha na planilha idêntica ao banco
        row_dict = {
            "id": str(self.glock.pk),
            "patrimonio": "PAT-PULL-01",
            "numero_serie": "GLK-PULL-01",
            "modelo": "PISTOLA GLOCK G22 G5 .40",
            "cod_opm": "",
            "unidade": "2.BAEP",
            "situacao_reserva": "ok",
            "observacoes": "",
            "atualizado_em": self.glock.data_atualizacao.isoformat(),
        }
        # Monta matriz: linha 1 = header, linha 2 = valores
        row_values = [row_dict[col] for col in self.columns]
        mock_read_all.return_value = [self.columns, row_values]

        # Snapshot já registrado com o mesmo hash (sem read_only_columns)
        row_without_readonly = {k: v for k, v in row_dict.items() if k != "atualizado_em"}
        content_hash = compute_content_hash(row_without_readonly)

        SheetRowSnapshot.objects.create(
            model_name="PistolaGlock",
            lookup_key="id",
            lookup_value=str(self.glock.pk),
            row_number=2,
            content_hash=content_hash,
        )

        summary = pull_from_sheets(model_name="PistolaGlock", dry_run=False, force=False)

        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["updated"], 0)
        self.assertEqual(summary["created"], 0)

        # Objeto permanece inalterado
        self.glock.refresh_from_db()
        self.assertEqual(self.glock.situacao_reserva, "ok")

    @patch("integracoes.services.pull.create_db_backup")
    @patch("integracoes.services.pull.read_all")
    def test_hash_diferente_com_planilha_mais_recente_aplica_alteracao(
        self, mock_read_all, mock_backup
    ):
        mock_backup.return_value = "/tmp/dummy.sql"

        # Snapshot prévio com hash antigo
        SheetRowSnapshot.objects.create(
            model_name="PistolaGlock",
            lookup_key="id",
            lookup_value=str(self.glock.pk),
            row_number=2,
            content_hash="old-hash-antigo",
        )

        # Planilha com alteração e timestamp posterior ao Django
        future_dt = self.glock.data_atualizacao + timedelta(minutes=10)
        row_dict = {
            "id": str(self.glock.pk),
            "patrimonio": "PAT-PULL-01",
            "numero_serie": "GLK-PULL-01",
            "modelo": "PISTOLA GLOCK G22 G5 .40",
            "cod_opm": "",
            "unidade": "2.BAEP",
            "situacao_reserva": "EM_USO",
            "observacoes": "Atualizado via Sheets",
            "atualizado_em": future_dt.isoformat(),
        }
        row_values = [row_dict[col] for col in self.columns]
        mock_read_all.return_value = [self.columns, row_values]

        summary = pull_from_sheets(model_name="PistolaGlock", dry_run=False, force=False)

        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["updated"], 1)

        # Verifica alteração refletida no Django
        self.glock.refresh_from_db()
        self.assertEqual(self.glock.situacao_reserva, "EM_USO")
        self.assertEqual(self.glock.observacoes, "Atualizado via Sheets")

        # Snapshot atualizado com novo hash
        snapshot = SheetRowSnapshot.objects.get(
            model_name="PistolaGlock", lookup_value=str(self.glock.pk)
        )
        row_without_readonly = {k: v for k, v in row_dict.items() if k != "atualizado_em"}
        expected_hash = compute_content_hash(row_without_readonly)
        self.assertEqual(snapshot.content_hash, expected_hash)

    @patch("integracoes.services.pull.create_db_backup")
    @patch("integracoes.services.pull.update_row")
    @patch("integracoes.services.pull.read_all")
    def test_linha_sem_id_cria_objeto_e_escreve_id_de_volta(
        self, mock_read_all, mock_update, mock_backup
    ):
        mock_backup.return_value = "/tmp/dummy.sql"

        # Linha na planilha sem ID
        row_dict = {
            "id": "",
            "patrimonio": "PAT-NOVA-99",
            "numero_serie": "GLK-NOVA-99",
            "modelo": "PISTOLA GLOCK G22 G5 .40",
            "cod_opm": "",
            "unidade": "2.BAEP",
            "situacao_reserva": "ok",
            "observacoes": "",
            "atualizado_em": "",
        }
        row_values = [row_dict[col] for col in self.columns]
        mock_read_all.return_value = [self.columns, row_values]

        summary = pull_from_sheets(model_name="PistolaGlock", dry_run=False, force=False)

        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["created"], 1)

        # Objeto foi salvo no banco
        novo = PistolaGlock.objects.get(numero_serie="GLK-NOVA-99")
        self.assertEqual(novo.patrimonio, "PAT-NOVA-99")

        # update_row deve ter sido chamado para escrever o novo ID na linha 2 da aba
        mock_update.assert_called_once_with(
            "new",
            "'Pistolas_Glock'!A2",
            [[str(novo.pk)]],
        )

        # Snapshot criado
        self.assertTrue(
            SheetRowSnapshot.objects.filter(
                model_name="PistolaGlock", lookup_value=str(novo.pk)
            ).exists()
        )

    @patch("integracoes.services.pull.create_db_backup")
    @patch("integracoes.services.pull.read_all")
    def test_read_only_columns_respeitado_e_lww_django_mais_recente_nao_sobrescreve(
        self, mock_read_all, mock_backup
    ):
        mock_backup.return_value = "/tmp/dummy.sql"

        # Planilha com timestamp ANTERIOR ao do Django
        past_dt = self.glock.data_atualizacao - timedelta(minutes=30)
        row_dict = {
            "id": str(self.glock.pk),
            "patrimonio": "PAT-PULL-01",
            "numero_serie": "GLK-PULL-01",
            "modelo": "PISTOLA GLOCK G22 G5 .40",
            "cod_opm": "",
            "unidade": "2.BAEP",
            "situacao_reserva": "EM_USO",  # planilha tentaria mudar
            "observacoes": "Mudança antiga da planilha",
            "atualizado_em": past_dt.isoformat(),
        }
        row_values = [row_dict[col] for col in self.columns]
        mock_read_all.return_value = [self.columns, row_values]

        summary = pull_from_sheets(model_name="PistolaGlock", dry_run=False, force=False)

        # Como Django é mais recente, deve ignorar alteração
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["updated"], 0)

        self.glock.refresh_from_db()
        self.assertEqual(self.glock.situacao_reserva, "ok")  # não alterado

    @patch("integracoes.services.pull.create_db_backup")
    @patch("integracoes.services.pull.read_all")
    def test_campo_obrigatorio_vazio_nao_fabrica_dados_e_registra_erro(
        self, mock_read_all, mock_backup
    ):
        mock_backup.return_value = "/tmp/dummy.sql"

        # Linha nova sem numero_serie (campo obrigatório único no Django)
        row_dict = {
            "id": "",
            "patrimonio": "PAT-INV",
            "numero_serie": "",  # VAZIO!
            "modelo": "PISTOLA GLOCK G22 G5 .40",
            "cod_opm": "",
            "unidade": "2.BAEP",
            "situacao_reserva": "ok",
            "observacoes": "",
            "atualizado_em": "",
        }
        row_values = [row_dict[col] for col in self.columns]
        mock_read_all.return_value = [self.columns, row_values]

        summary = pull_from_sheets(model_name="PistolaGlock", dry_run=False, force=False)

        # Não deve fabricar valor e deve marcar erro
        self.assertEqual(summary["errors"], 1)
        self.assertTrue(
            SyncOperationRecord.objects.filter(
                status="ERROR", action="ERROR"
            ).exists()
        )


@override_settings(SHEETS_SYNC_ENABLED=True, NEW_SPREADSHEET_ID="test-new-sheet-123")
class PullFromSheetsCommandTests(TestCase):
    """Testa o management command pull_from_sheets."""

    def test_command_requires_confirm_or_dry_run(self):
        with self.assertRaises(CommandError) as ctx:
            call_command("pull_from_sheets")

        self.assertIn("requer --confirm", str(ctx.exception))

    @patch("integracoes.management.commands.pull_from_sheets.pull_from_sheets")
    def test_command_executes_with_confirm_flag(self, mock_pull):
        mock_pull.return_value = {
            "status": "SUCCESS",
            "total": 5,
            "created": 1,
            "updated": 2,
            "skipped": 2,
            "errors": 0,
            "operation_id": 1,
        }

        call_command("pull_from_sheets", "--confirm", "--model", "PistolaGlock")
        mock_pull.assert_called_once_with(
            model_name="PistolaGlock",
            dry_run=False,
            force=False,
        )

    @patch("integracoes.management.commands.pull_from_sheets.pull_from_sheets")
    def test_command_handles_failed_status_with_command_error(self, mock_pull):
        mock_pull.return_value = {
            "status": "FAILED",
            "total": 5,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 5,
            "operation_id": 2,
        }

        with self.assertRaises(CommandError) as ctx:
            call_command("pull_from_sheets", "--confirm")

        self.assertIn("[FALHA]", str(ctx.exception))
