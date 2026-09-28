from django.contrib import admin

from .models import SheetRowSnapshot, SheetSyncState


@admin.register(SheetRowSnapshot)
class SheetRowSnapshotAdmin(admin.ModelAdmin):
    list_display = ("model_name", "lookup_value", "row_number", "last_seen_at")
    list_filter = ("model_name",)
    search_fields = ("lookup_value", "content_hash")
    readonly_fields = ("last_seen_at",)


@admin.register(SheetSyncState)
class SheetSyncStateAdmin(admin.ModelAdmin):
    list_display = ("key", "last_pull_at", "last_push_at", "last_pull_status", "last_push_status")
    readonly_fields = ("last_pull_at", "last_push_at")
