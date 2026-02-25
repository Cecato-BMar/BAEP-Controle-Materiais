from django.contrib import admin
from .models import Material

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('numero', 'nome', 'tipo', 'quantidade', 'quantidade_disponivel', 'quantidade_em_uso', 'estado', 'status')
    list_filter = ('tipo', 'estado', 'status')
    search_fields = ('nome', 'numero')
    readonly_fields = ('data_cadastro', 'data_atualizacao')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('tipo', 'nome', 'numero', 'imagem')
        }),
        ('Quantidades', {
            'fields': ('quantidade', 'quantidade_disponivel', 'quantidade_em_uso')
        }),
        ('Estado e Status', {
            'fields': ('estado', 'status')
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Datas', {
            'fields': ('data_cadastro', 'data_atualizacao')
        }),
    )
