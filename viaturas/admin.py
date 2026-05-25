from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import (
    MarcaViatura, ModeloViatura, Viatura, DespachoViatura, 
    Abastecimento, Manutencao, Oficina, ChecklistViatura,
    SolicitacaoBaixaViatura, PecaViatura, RetiradaPeca, RetiradaPecaItem,
    EvidenciaManutencao, PlanoManutencaoPreventiva
)


class EvidenciaInline(admin.TabularInline):
    model = EvidenciaManutencao
    extra = 0
    readonly_fields = ('data_upload', 'registrado_por')


@admin.register(ChecklistViatura)
class ChecklistViaturaAdmin(SimpleHistoryAdmin):
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
class ViaturaAdmin(SimpleHistoryAdmin):
    list_display = ('prefixo', 'placa', 'modelo', 'tipo', 'status', 'localizacao', 'odometro_atual')
    search_fields = ('prefixo', 'placa', 'chassi', 'renavam', 'modelo__nome')
    list_filter = ('status', 'modelo__tipo', 'tipo_combustivel', 'localizacao')
    autocomplete_fields = ['modelo']
    readonly_fields = ('data_cadastro', 'data_atualizacao')


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
class ManutencaoAdmin(SimpleHistoryAdmin):
    list_display = ('viatura', 'tipo', 'status', 'data_inicio', 'data_conclusao', 'oficina_fk', 'custo_total', 'aprovado_por')
    search_fields = ('viatura__prefixo', 'oficina', 'ordem_servico', 'descricao')
    list_filter = ('tipo', 'status', 'data_inicio', 'oficina_fk')
    autocomplete_fields = ['viatura', 'registrado_por']
    readonly_fields = (
        'data_criacao', 'data_atualizacao', 'registrado_por',
        'aprovado_por', 'data_aprovacao',
        'cancelado_por', 'data_cancelamento'
    )
    inlines = [EvidenciaInline]
    
    fieldsets = (
        ('Dados da Manutenção', {
            'fields': ('viatura', 'tipo', 'status', 'data_inicio', 'data_conclusao', 
                      'odometro', 'oficina_fk', 'oficina', 'ordem_servico', 'descricao')
        }),
        ('Custos', {
            'fields': ('custo_pecas', 'custo_mao_obra')
        }),
        ('Controle e Qualidade', {
            'fields': ('servicos_executados_corretamente', 'detalhamento_servicos',
                      'detalhamento_pecas_garantia', 'nota_fiscal', 'termo_garantia',
                      'data_validade_garantia', 'km_validade_garantia', 'retirada_pecas')
        }),
        ('Aprovação / Cancelamento', {
            'fields': ('aprovado_por', 'data_aprovacao', 'parecer_aprovacao',
                      'cancelado_por', 'data_cancelamento', 'motivo_cancelamento'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('registrado_por', 'data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Oficina)
class OficinaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'cidade', 'especialidade', 'ativo')
    search_fields = ('nome', 'cnpj', 'cidade')
    list_filter = ('ativo', 'cidade')


@admin.register(SolicitacaoBaixaViatura)
class SolicitacaoBaixaViaturaAdmin(admin.ModelAdmin):
    list_display = ('viatura', 'categoria_motivo', 'status', 'solicitante', 'data_solicitacao')
    search_fields = ('viatura__prefixo',)
    list_filter = ('status', 'categoria_motivo')
    readonly_fields = ('solicitante', 'data_solicitacao', 'analisado_por', 'data_analise')


@admin.register(PecaViatura)
class PecaViaturaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo', 'categoria', 'quantidade_estoque', 'limite_minimo', 'ativo')
    search_fields = ('nome', 'codigo', 'marca_fabricante')
    list_filter = ('categoria', 'ativo')


class RetiradaPecaItemInline(admin.TabularInline):
    model = RetiradaPecaItem
    extra = 0


@admin.register(RetiradaPeca)
class RetiradaPecaAdmin(admin.ModelAdmin):
    list_display = ('viatura', 'policial', 'data_retirada', 'registrado_por', 'assinado_eletronicamente')
    search_fields = ('viatura__prefixo',)
    list_filter = ('data_retirada', 'assinado_eletronicamente')
    readonly_fields = ('data_retirada', 'registrado_por')
    inlines = [RetiradaPecaItemInline]


@admin.register(EvidenciaManutencao)
class EvidenciaManutencaoAdmin(admin.ModelAdmin):
    list_display = ('manutencao', 'tipo', 'descricao', 'data_upload', 'registrado_por')
    list_filter = ('tipo', 'data_upload')
    readonly_fields = ('data_upload', 'registrado_por')


@admin.register(PlanoManutencaoPreventiva)
class PlanoManutencaoPreventivaAdmin(admin.ModelAdmin):
    list_display = ('modelo', 'descricao', 'intervalo_km', 'intervalo_dias', 'ativo')
    list_filter = ('ativo', 'modelo__marca')
    search_fields = ('descricao', 'modelo__nome')
