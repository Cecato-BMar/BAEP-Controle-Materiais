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
