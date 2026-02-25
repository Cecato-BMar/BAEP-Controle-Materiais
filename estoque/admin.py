from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Categoria, UnidadeMedida, Fornecedor, Produto, Lote, NumeroSerie,
    MovimentacaoEstoque, Inventario, ItemInventario, AjusteEstoque
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'categoria_pai', 'ativo', 'data_cadastro']
    list_filter = ['ativo', 'categoria_pai']
    search_fields = ['nome', 'codigo', 'descricao']
    ordering = ['codigo', 'nome']
    readonly_fields = ['data_cadastro', 'data_atualizacao']


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
    list_display = ['codigo', 'nome', 'categoria', 'tipo_produto', 'estoque_atual', 
                   'estoque_disponivel', 'valor_unitario', 'status']
    list_filter = ['tipo_produto', 'status', 'categoria', 'controla_validade', 'controla_numero_serie']
    search_fields = ['codigo', 'nome', 'descricao']
    ordering = ['codigo', 'nome']
    readonly_fields = ['valor_total', 'data_cadastro', 'data_atualizacao']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('codigo', 'codigo_barras', 'nome', 'descricao', 'categoria', 'unidade_medida', 'tipo_produto', 'status')
        }),
        ('Controle de Estoque', {
            'fields': ('estoque_minimo', 'estoque_maximo', 'estoque_atual', 'estoque_reservado', 'valor_unitario', 'valor_total')
        }),
        ('Controle Especial', {
            'fields': ('controla_validade', 'prazo_validade_meses', 'controla_numero_serie')
        }),
        ('Fornecedor', {
            'fields': ('fornecedor_padrao',)
        }),
        ('Mídia', {
            'fields': ('imagem',)
        }),
        ('Auditoria', {
            'fields': ('criado_por', 'data_cadastro', 'atualizado_por', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [LoteInline, NumeroSerieInline]
    
    def estoque_disponivel(self, obj):
        disponivel = obj.estoque_disponivel
        if disponivel <= obj.estoque_minimo:
            color = 'red'
        elif disponivel <= (obj.estoque_minimo * 1.5):
            color = 'orange'
        else:
            color = 'green'
        return format_html('<span style="color: {};">{}</span>', color, disponivel)
    estoque_disponivel.short_description = 'Estoque Disponível'

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
    ordering = ['-data_cadastro']
    readonly_fields = ['data_cadastro', 'data_atualizacao']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('produto', 'fornecedor')


@admin.register(NumeroSerie)
class NumeroSerieAdmin(admin.ModelAdmin):
    list_display = ['numero_serie', 'produto', 'patrimonio', 'status', 'localizacao', 'responsavel']
    list_filter = ['status', 'produto']
    search_fields = ['numero_serie', 'patrimonio', 'produto__nome']
    ordering = ['produto', 'numero_serie']
    readonly_fields = ['data_cadastro', 'data_atualizacao']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('produto', 'responsavel')


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ['data_hora', 'produto', 'tipo_movimentacao', 'quantidade', 'valor_total', 'usuario']
    list_filter = ['tipo_movimentacao', 'motivo', 'data_hora', 'produto__categoria']
    search_fields = ['produto__nome', 'documento_referencia', 'observacoes']
    ordering = ['-data_hora']
    readonly_fields = ['uuid', 'valor_total', 'data_hora', 'ip_address', 'user_agent']
    
    fieldsets = (
        ('Informações Gerais', {
            'fields': ('uuid', 'produto', 'lote', 'numero_serie', 'tipo_movimentacao', 'motivo')
        }),
        ('Quantidades e Valores', {
            'fields': ('quantidade', 'valor_unitario', 'valor_total')
        }),
        ('Referências', {
            'fields': ('documento_referencia', 'fornecedor', 'solicitante', 'destino_origem')
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Auditoria', {
            'fields': ('usuario', 'data_hora', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('produto', 'usuario', 'fornecedor', 'solicitante')


class ItemInventarioInline(admin.TabularInline):
    model = ItemInventario
    extra = 0
    fields = ['produto', 'quantidade_sistema', 'quantidade_contada', 'diferenca', 'status_contagem', 'contado_por']
    readonly_fields = ['diferenca']


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ['numero', 'tipo_inventario', 'status', 'data_inicio', 'data_fim', 'responsavel', 'percentual_conclusao']
    list_filter = ['tipo_inventario', 'status', 'data_inicio', 'data_fim']
    search_fields = ['numero', 'descricao']
    ordering = ['-data_cadastro']
    readonly_fields = ['data_cadastro', 'data_atualizacao', 'total_produtos', 'itens_contados', 'percentual_conclusao']
    
    fieldsets = (
        ('Informações Gerais', {
            'fields': ('numero', 'descricao', 'tipo_inventario', 'status')
        }),
        ('Datas', {
            'fields': ('data_inicio', 'data_fim', 'data_prevista_fim')
        }),
        ('Responsável', {
            'fields': ('responsavel',)
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
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
    
    def percentual_conclusao(self, obj):
        percentual = obj.percentual_conclusao
        if percentual >= 100:
            color = 'green'
        elif percentual >= 50:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, percentual)
    percentual_conclusao.short_description = 'Conclusão'


@admin.register(ItemInventario)
class ItemInventarioAdmin(admin.ModelAdmin):
    list_display = ['inventario', 'produto', 'quantidade_sistema', 'quantidade_contada', 'diferenca', 'status_contagem', 'contado_por']
    list_filter = ['status_contagem', 'inventario', 'produto__categoria']
    search_fields = ['produto__nome', 'inventario__numero']
    ordering = ['inventario', 'produto']
    readonly_fields = ['diferenca']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('inventario', 'produto', 'contado_por')


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
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Aprovação', {
            'fields': ('aprovado_por', 'data_aprovacao', 'ip_address')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('produto', 'aprovado_por', 'inventario')
