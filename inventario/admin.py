from django.contrib import admin
from .models import ContaContabil, CicloInventario, ItemInventario


@admin.register(ContaContabil)
class ContaContabilAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome')
    search_fields = ('codigo', 'nome')


@admin.register(CicloInventario)
class CicloInventarioAdmin(admin.ModelAdmin):
    list_display = ('termo_numero', 'titulo', 'ano', 'semestre', 'status', 'total_itens', 'total_valor', 'criado_em')
    list_filter = ('ano', 'semestre', 'status')
    search_fields = ('termo_numero', 'titulo', 'detentor_executivo')


@admin.register(ItemInventario)
class ItemInventarioAdmin(admin.ModelAdmin):
    list_display = ('patrimonio', 'tipo_material', 'secao_subunidade', 'conta_contabil', 'situacao_material', 'valor', 'conferido')
    list_filter = ('conferido', 'situacao_fisica_conferida', 'conta_contabil', 'secao_subunidade')
    search_fields = ('patrimonio', 'numero_serie', 'tipo_material', 'secao_subunidade')
