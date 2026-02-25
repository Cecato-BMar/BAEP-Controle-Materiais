from django.contrib import admin
from .models import Relatorio

@admin.register(Relatorio)
class RelatorioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'data_geracao', 'periodo_inicio', 'periodo_fim', 'gerado_por')
    list_filter = ('tipo', 'data_geracao', 'gerado_por')
    search_fields = ('titulo', 'observacoes')
    readonly_fields = ('data_geracao',)
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('titulo', 'tipo', 'data_geracao')
        }),
        ('Período', {
            'fields': ('periodo_inicio', 'periodo_fim')
        }),
        ('Arquivo', {
            'fields': ('arquivo_pdf',)
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Usuário', {
            'fields': ('gerado_por',)
        }),
    )
