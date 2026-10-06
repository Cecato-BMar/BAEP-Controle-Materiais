from django.db import models


class SheetRowSnapshot(models.Model):
    """Estado da última leitura de cada linha da planilha."""

    model_name = models.CharField(max_length=64)
    lookup_key = models.CharField(max_length=64)
    lookup_value = models.CharField(max_length=128)
    row_number = models.IntegerField()
    content_hash = models.CharField(max_length=64)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("model_name", "lookup_value")]
        verbose_name = "Snapshot de linha do Sheets"
        verbose_name_plural = "Snapshots de linha do Sheets"

    def __str__(self) -> str:
        return f"{self.model_name}::{self.lookup_value} (linha {self.row_number})"


class SheetSyncState(models.Model):
    """Estado global da sincronização (singleton por key)."""

    key = models.CharField(max_length=32, unique=True)
    last_pull_at = models.DateTimeField(null=True, blank=True)
    last_push_at = models.DateTimeField(null=True, blank=True)
    last_pull_status = models.CharField(max_length=16, blank=True)
    last_push_status = models.CharField(max_length=16, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        verbose_name = "Estado de sincronização Sheets"
        verbose_name_plural = "Estados de sincronização Sheets"

    def __str__(self) -> str:
        return f"SheetSyncState({self.key})"


class SyncOperation(models.Model):
    """Registro mestre de cada execução de operação de sincronização ou importação."""

    OPERATION_TYPE_CHOICES = [
        ("IMPORT_LEGACY", "Importação Planilha Antiga"),
        ("SYNC_FULL", "Sincronização Completa"),
        ("PULL", "Pull (Sheets → Django)"),
        ("PUSH", "Push (Django → Sheets)"),
        ("SEED", "Seed Inicial Planilha Nova"),
    ]

    STATUS_CHOICES = [
        ("IN_PROGRESS", "Em Andamento"),
        ("SUCCESS", "Sucesso Total"),
        ("PARTIAL_SUCCESS", "Sucesso Parcial com Avisos"),
        ("FAILED", "Falhou"),
        ("REVERTED", "Revertido (Rollback)"),
    ]

    operation_type = models.CharField(max_length=32, choices=OPERATION_TYPE_CHOICES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="IN_PROGRESS")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    total_records = models.IntegerField(default=0)
    created_count = models.IntegerField(default=0)
    updated_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    backup_file_path = models.CharField(max_length=512, blank=True, null=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Operação de Sincronização"
        verbose_name_plural = "Operações de Sincronização"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"SyncOperation #{self.pk} [{self.get_operation_type_display()}] - {self.get_status_display()}"


class SyncOperationRecord(models.Model):
    """Registro individual de cada item afetado dentro de uma SyncOperation (audit log / rollback)."""

    ACTION_CHOICES = [
        ("CREATE", "Criação"),
        ("UPDATE", "Atualização"),
        ("DELETE", "Exclusão"),
        ("SKIP", "Ignorado"),
        ("ERROR", "Erro"),
    ]

    STATUS_CHOICES = [
        ("SUCCESS", "Sucesso"),
        ("WARNING", "Aviso"),
        ("ERROR", "Erro"),
    ]

    operation = models.ForeignKey(
        SyncOperation,
        on_delete=models.CASCADE,
        related_name="records"
    )
    model_name = models.CharField(max_length=64)
    lookup_key = models.CharField(max_length=64)
    lookup_value = models.CharField(max_length=128)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="SUCCESS")
    sheet_name = models.CharField(max_length=128, blank=True)
    row_number = models.IntegerField(null=True, blank=True)
    before_snapshot = models.JSONField(null=True, blank=True)
    after_snapshot = models.JSONField(null=True, blank=True)
    error_detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de Operação de Sincronização"
        verbose_name_plural = "Registros de Operação de Sincronização"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["operation", "model_name", "lookup_value"]),
        ]

    def __str__(self) -> str:
        return f"Record #{self.pk} [{self.model_name}:{self.lookup_value}] - {self.action} ({self.status})"
