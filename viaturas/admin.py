from django.contrib import admin
from .models import MarcaViatura, ModeloViatura, Viatura, DespachoViatura, Abastecimento, Manutencao, ChecklistViatura

@admin.register(ChecklistViatura)
class ChecklistViaturaAdmin(admin.ModelAdmin):
    list_display = ('viatura', 'tipo', 'policial', 'data_hora', 'odometro')
    list_filter = ('tipo', 'data_hora', 'viatura')
    search_fields = ('viatura__prefixo', 'policial__nome_guerra')
    readonly_fields = ('data_hora', 'registrado_por')

@admin.register(MarcaViatura)
class MarcaViaturaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo')
    search_fields = ('nome',)
    list_filter = ('ativo',)

@admin.register(ModeloViatura)
class ModeloViaturaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'marca', 'tipo', 'ativo')
    search_fields = ('nome', 'marca__nome')
    list_filter = ('tipo', 'ativo')

@admin.register(Viatura)
class ViaturaAdmin(admin.ModelAdmin):
    list_display = ('prefixo', 'placa', 'modelo', 'tipo', 'status', 'odometro_atual')
    search_fields = ('prefixo', 'placa', 'chassi', 'renavam', 'modelo__nome')
    list_filter = ('status', 'modelo__tipo', 'tipo_combustivel')
    autocomplete_fields = ['modelo']

@admin.register(DespachoViatura)
class DespachoViaturaAdmin(admin.ModelAdmin):
    list_display = ('viatura', 'motorista', 'data_saida', 'km_saida', 'data_retorno', 'km_retorno')
    search_fields = ('viatura__prefixo', 'motorista__qra', 'motorista__re')
    list_filter = ('data_saida', 'data_retorno')
    autocomplete_fields = ['viatura', 'motorista', 'encarregado', 'registrado_por']

@admin.register(Abastecimento)
class AbastecimentoAdmin(admin.ModelAdmin):
    list_display = ('viatura', 'data_abastecimento', 'combustivel', 'quantidade_litros', 'valor_total', 'motorista')
    search_fields = ('viatura__prefixo', 'motorista__qra', 'cupom_fiscal')
    list_filter = ('combustivel', 'data_abastecimento')
    autocomplete_fields = ['viatura', 'motorista', 'registrado_por']

@admin.register(Manutencao)
class ManutencaoAdmin(admin.ModelAdmin):
    list_display = ('viatura', 'tipo', 'data_inicio', 'oficina', 'custo_total')
    search_fields = ('viatura__prefixo', 'oficina', 'ordem_servico')
    list_filter = ('tipo', 'data_inicio')
    autocomplete_fields = ['viatura', 'registrado_por']
