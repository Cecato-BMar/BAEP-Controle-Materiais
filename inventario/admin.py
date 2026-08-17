from django.contrib import admin
from .models import (
    ContaContabil,
    CicloInventario,
    ConferenciaInventario,
    DivergenciaInventario,
    HistoricoCicloInventario,
    ItemInventario,
    MembroComissaoInventario,
)


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


@admin.register(MembroComissaoInventario)
class MembroComissaoInventarioAdmin(admin.ModelAdmin):
    list_display = ('ciclo', 'usuario', 'papel', 'secao_subunidade', 'ativo')
    list_filter = ('papel', 'ativo')
    search_fields = ('usuario__username', 'secao_subunidade', 'ciclo__termo_numero')


@admin.register(ConferenciaInventario)
class ConferenciaInventarioAdmin(admin.ModelAdmin):
    list_display = ('item', 'resultado', 'situacao_fisica', 'conferido_por', 'conferido_em')
    list_filter = ('resultado', 'situacao_fisica')
    search_fields = ('item__patrimonio', 'item__numero_serie', 'observacoes')
    readonly_fields = ('conferido_em',)


@admin.register(DivergenciaInventario)
class DivergenciaInventarioAdmin(admin.ModelAdmin):
    list_display = ('item', 'tipo', 'status', 'responsavel', 'prazo', 'criado_em')
    list_filter = ('tipo', 'status')
    search_fields = ('item__patrimonio', 'descricao', 'providencia')


@admin.register(HistoricoCicloInventario)
class HistoricoCicloInventarioAdmin(admin.ModelAdmin):
    list_display = ('ciclo', 'status_anterior', 'status_novo', 'realizado_por', 'realizado_em')
    list_filter = ('status_anterior', 'status_novo')
    readonly_fields = ('ciclo', 'status_anterior', 'status_novo', 'justificativa', 'realizado_por', 'realizado_em')
