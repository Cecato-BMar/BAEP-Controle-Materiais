from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Categoria, Subcategoria, UnidadeMedida, UnidadeFornecimento, Cor, ContaPatrimonial,
    OrgaoRequisitante, LocalizacaoFisica, MilitarRequisitante,
    Fornecedor, Produto, Lote, NumeroSerie,
    MovimentacaoEstoque, Inventario, ItemInventario, AjusteEstoque
)


# =============================================================================
# CADASTROS MESTRES PAP
# =============================================================================

@admin.register(Cor)
class CorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo', 'data_cadastro']
    list_filter = ['ativo']
    search_fields = ['nome']


@admin.register(UnidadeFornecimento)
class UnidadeFornecimentoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'padrao', 'ativo', 'data_cadastro']
    list_filter = ['ativo', 'padrao']
    search_fields = ['nome']


@admin.register(ContaPatrimonial)
class ContaPatrimonialAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descricao', 'ativo']
    list_filter = ['ativo']
    search_fields = ['codigo', 'descricao']
    ordering = ['codigo']


@admin.register(OrgaoRequisitante)
class OrgaoRequisitanteAdmin(admin.ModelAdmin):
    list_display = ['sigla', 'nome', 'ativo']
    list_filter = ['ativo']
    search_fields = ['sigla', 'nome']
    ordering = ['nome']


@admin.register(LocalizacaoFisica)
class LocalizacaoFisicaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo', 'data_cadastro']
    list_filter = ['ativo']
    search_fields = ['nome']


@admin.register(MilitarRequisitante)
class MilitarRequisitanteAdmin(admin.ModelAdmin):
    list_display = ['re', 'qra', 'nome_completo', 'orgao', 'ativo']
    list_filter = ['ativo', 'orgao']
    search_fields = ['re', 'qra', 'nome_completo']
    ordering = ['re']


# =============================================================================
# CADASTROS EXISTENTES
# =============================================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'ativo', 'data_cadastro']
    list_filter = ['ativo']
    search_fields = ['nome', 'codigo', 'descricao']
    ordering = ['codigo', 'nome']
    readonly_fields = ['data_cadastro', 'data_atualizacao']


@admin.register(Subcategoria)
class SubcategoriaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'categoria', 'codigo', 'ativo', 'data_cadastro']
    list_filter = ['categoria', 'ativo']
    search_fields = ['nome', 'codigo', 'descricao']
    ordering = ['categoria', 'nome']


@admin.register(UnidadeMedida)
class UnidadeMedidaAdmin(admin.ModelAdmin):
    list_display = ['sigla', 'nome', 'ativo']
    list_filter = ['ativo']
    search_fields = ['sigla', 'nome', 'descricao']
    ordering = ['sigla']


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo_pessoa', 'documento', 'telefone', 'email', 'ativo']
    list_filter = ['tipo_pessoa', 'ativo', 'estado']
    search_fields = ['nome', 'documento', 'email']
    ordering = ['nome']
    readonly_fields = ['data_cadastro', 'data_atualizacao']


class LoteInline(admin.TabularInline):
    model = Lote
    extra = 0
    fields = ['numero_lote', 'quantidade_atual', 'data_validade', 'fornecedor', 'ativo']
    readonly_fields = ['data_cadastro', 'data_atualizacao']


class NumeroSerieInline(admin.TabularInline):
    model = NumeroSerie
    extra = 0
    fields = ['numero_serie', 'patrimonio', 'status', 'localizacao', 'responsavel']
    readonly_fields = ['data_cadastro', 'data_atualizacao']


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'categoria', 'subcategoria', 'saldo_display', 'estoque_minimo', 'valor_unitario', 'status']
    list_filter = ['status', 'categoria', 'subcategoria', 'controla_validade', 'controla_numero_serie']
    search_fields = ['codigo', 'nome', 'descricao', 'codigo_siafisico', 'codigo_cat_mat']
    ordering = ['codigo', 'nome']
    readonly_fields = ['valor_total', 'data_cadastro', 'data_atualizacao', 'saldo_display', 'cotacao_vencida']

    fieldsets = (
        ('Identificação', {
            'fields': ('codigo', 'codigo_barras', 'nome', 'descricao', 'categoria', 'subcategoria', 'status')
        }),
        ('Licitação / PAP', {
            'fields': ('empenho', 'codigo_siafisico', 'codigo_cat_mat', 'termo_referencia', 'processo_sei',
                       'preco_medio', 'data_cotacao', 'cotacao_vencida',
                       'data_inicio_projeto', 'tempo_reposicao', 'historico_subcategoria')
        }),
        ('Unidades e Vínculos', {
            'fields': ('unidade_medida', 'unidade_fornecimento', 'fornecedor_padrao',
                       'localizacao_fisica', 'conta_patrimonial')
        }),
        ('Controle de Estoque', {
            'fields': ('estoque_minimo', 'estoque_maximo', 'estoque_atual',
                       'estoque_reservado', 'valor_unitario', 'valor_total', 'saldo_display')
        }),
        ('Controle Especial', {
            'fields': ('controla_validade', 'prazo_validade_meses', 'controla_numero_serie')
        }),
        ('Auditoria', {
            'fields': ('criado_por', 'data_cadastro', 'atualizado_por', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )

    inlines = [LoteInline, NumeroSerieInline]

    def saldo_display(self, obj):
        saldo = obj.saldo_calculado
        if saldo <= obj.estoque_minimo:
            color = 'red'
        elif saldo <= (obj.estoque_minimo * 2):
            color = 'orange'
        else:
            color = 'green'
        return format_html('<span style="color: {}; font-weight:bold">{}</span>', color, saldo)
    saldo_display.short_description = 'Saldo'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.criado_por = request.user
        obj._current_user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ['numero_lote', 'produto', 'quantidade_atual', 'data_validade', 'fornecedor', 'ativo']
    list_filter = ['ativo', 'data_validade', 'fornecedor']
    search_fields = ['numero_lote', 'produto__nome', 'fornecedor__nome']
    ordering = ['data_cadastro']  # PEPS
    readonly_fields = ['data_cadastro', 'data_atualizacao']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('produto', 'fornecedor')


@admin.register(NumeroSerie)
class NumeroSerieAdmin(admin.ModelAdmin):
    list_display = ['numero_serie', 'produto', 'patrimonio', 'status', 'localizacao', 'responsavel']
    list_filter = ['status', 'produto']
    search_fields = ['numero_serie', 'patrimonio', 'produto__nome']
    ordering = ['produto', 'numero_serie']
    readonly_fields = ['data_cadastro', 'data_atualizacao']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('produto', 'responsavel')


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ['data_movimentacao', 'produto', 'subtipo', 'quantidade', 'valor_total', 'usuario']
    list_filter = ['tipo_movimentacao', 'subtipo', 'data_movimentacao', 'produto__categoria']
    search_fields = ['produto__nome', 'documento_referencia', 'observacoes']
    ordering = ['-data_hora']
    readonly_fields = ['uuid', 'valor_total', 'data_hora', 'ip_address', 'tipo_movimentacao']

    fieldsets = (
        ('Informações Gerais', {
            'fields': ('uuid', 'produto', 'lote', 'numero_serie', 'tipo_movimentacao', 'subtipo', 'data_movimentacao')
        }),
        ('Quantidades e Valores', {
            'fields': ('quantidade', 'valor_unitario', 'valor_total')
        }),
        ('Dados de Entrada (PAP §2)', {
            'fields': ('cor', 'unidade_medida', 'unidade_fornecimento',
                       'conta_patrimonial', 'localizacao_fisica', 'fornecedor',
                       'nota_fiscal', 'documento_referencia')
        }),
        ('Dados de Saída (PAP §3)', {
            'fields': ('orgao_requisitante', 'militar_requisitante')
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Auditoria', {
            'fields': ('usuario', 'data_hora', 'ip_address'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'produto', 'usuario', 'fornecedor', 'orgao_requisitante', 'militar_requisitante')


class ItemInventarioInline(admin.TabularInline):
    model = ItemInventario
    extra = 0
    fields = ['produto', 'quantidade_sistema', 'quantidade_contada', 'diferenca', 'status_contagem', 'contado_por']
    readonly_fields = ['diferenca']


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ['numero', 'tipo_inventario', 'status', 'data_inicio', 'data_fim', 'responsavel', 'percentual_display']
    list_filter = ['tipo_inventario', 'status', 'data_inicio']
    search_fields = ['numero', 'descricao']
    ordering = ['-data_cadastro']
    readonly_fields = ['data_cadastro', 'data_atualizacao', 'total_produtos', 'itens_contados', 'percentual_conclusao']

    fieldsets = (
        ('Informações Gerais', {'fields': ('numero', 'descricao', 'tipo_inventario', 'status')}),
        ('Datas', {'fields': ('data_inicio', 'data_fim', 'data_prevista_fim')}),
        ('Responsável', {'fields': ('responsavel',)}),
        ('Observações', {'fields': ('observacoes',)}),
        ('Resumo', {
            'fields': ('total_produtos', 'itens_contados', 'percentual_conclusao'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('data_cadastro', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ItemInventarioInline]

    def percentual_display(self, obj):
        p = obj.percentual_conclusao
        color = 'green' if p >= 100 else ('orange' if p >= 50 else 'red')
        return format_html('<span style="color: {};">{:.1f}%</span>', color, p)
    percentual_display.short_description = 'Conclusão'


@admin.register(ItemInventario)
class ItemInventarioAdmin(admin.ModelAdmin):
    list_display = ['inventario', 'produto', 'quantidade_sistema', 'quantidade_contada', 'diferenca', 'status_contagem', 'contado_por']
    list_filter = ['status_contagem', 'inventario', 'produto__categoria']
    search_fields = ['produto__nome', 'inventario__numero']
    ordering = ['inventario', 'produto']
    readonly_fields = ['diferenca']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('inventario', 'produto', 'contado_por')


@admin.register(AjusteEstoque)
class AjusteEstoqueAdmin(admin.ModelAdmin):
    list_display = ['data_aprovacao', 'produto', 'tipo_ajuste', 'quantidade', 'valor_total', 'aprovado_por', 'motivo']
    list_filter = ['tipo_ajuste', 'motivo', 'data_aprovacao', 'produto__categoria']
    search_fields = ['produto__nome', 'observacoes']
    ordering = ['-data_aprovacao']
    readonly_fields = ['valor_total', 'data_aprovacao', 'ip_address']

    fieldsets = (
        ('Informações Gerais', {
            'fields': ('inventario', 'produto', 'lote', 'numero_serie', 'tipo_ajuste', 'motivo')
        }),
        ('Ajuste', {
            'fields': ('quantidade', 'valor_unitario', 'valor_total', 'quantidade_antes', 'quantidade_depois')
        }),
        ('Observações', {'fields': ('observacoes',)}),
        ('Aprovação', {'fields': ('aprovado_por', 'data_aprovacao', 'ip_address')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('produto', 'aprovado_por', 'inventario')
