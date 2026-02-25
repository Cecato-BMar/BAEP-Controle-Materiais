from django.contrib import admin
from .models import Policial

@admin.register(Policial)
class PolicialAdmin(admin.ModelAdmin):
    list_display = ('re', 'posto', 'nome', 'situacao')
    list_filter = ('posto', 'situacao')
    search_fields = ('nome', 're')
    readonly_fields = ('data_cadastro', 'data_atualizacao')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('re', 'nome', 'posto', 'foto')
        }),
        ('Situação', {
            'fields': ('situacao',)
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Datas', {
            'fields': ('data_cadastro', 'data_atualizacao')
        }),
    )
