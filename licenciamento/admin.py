from django.contrib import admin
from .models import LicenseRecord

@admin.register(LicenseRecord)
class LicenseRecordAdmin(admin.ModelAdmin):
    list_display = ('client_id', 'client_name', 'issued_at', 'expires_at', 'last_verified', 'is_active')
    search_fields = ('client_id', 'client_name')
    list_filter = ('is_active', 'expires_at')
