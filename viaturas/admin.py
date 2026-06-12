"""
viaturas/admin.py — Django Admin completo para o Módulo Frota

Configuração administrativa com:
  - list_display com campos computados e badges HTML
  - search_fields com busca textual ampla
  - list_filter com filtros estratégicos e date_range
  - actions para operações em lote
  - inlines para edição de filhos no formulário pai
  - fieldsets organizados por seção funcional
  - SimpleHistoryAdmin em models com auditoria
  - select_related para evitar N+1

Compatível com PostgreSQL e Django 5.x.
"""
from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    MarcaViatura, ModeloViatura, Viatura, DespachoViatura,
    Abastecimento, Manutencao, Oficina, ChecklistViatura,
    SolicitacaoBaixaViatura, PecaViatura, RetiradaPeca, RetiradaPecaItem,
    EvidenciaManutencao, PlanoManutencaoPreventiva, DocumentoViatura,
    ServicoManutencao, RegistroHistoricoManutencao,
    StatusViatura, StatusManutencao, StatusBaixa,
)


# ============================================================================
# INLINES
# ============================================================================
class ModeloViaturaInline(admin.TabularInline):
    model = ModeloViatura
    extra = 0
    fields = ('nome', 'tipo', 'ativo')
    show_change_link = True


class DocumentoViaturaInline(admin.TabularInline):
    model = DocumentoViatura
    extra = 0
    fields = ('tipo', 'numero_documento', 'data_vencimento', 'ativo')
    readonly_fields = ('data_cadastro',)
    show_change_link = True


class DespachoViaturaInline(admin.TabularInline):
    model = DespachoViatura
    extra = 0
    fields = ('data_saida', 'motorista', 'km_saida', 'data_retorno', 'km_retorno')
    readonly_fields = ('data_saida', 'registrado_por')
    show_change_link = True
    autocomplete_fields = ('motorista', 'encarregado')


class AbastecimentoInline(admin.TabularInline):
    model = Abastecimento
    extra = 0
    fields = ('data_abastecimento', 'combustivel', 'quantidade_litros', 'valor_total', 'odometro')
    readonly_fields = ('registrado_por',)
    show_change_link = True


class ManutencaoInline(admin.TabularInline):
    model = Manutencao
    extra = 0
    fields = ('tipo', 'status', 'data_inicio', 'data_conclusao', 'oficina_fk')
    readonly_fields = ('data_criacao',)
    show_change_link = True


class ChecklistViaturaInline(admin.TabularInline):
    model = ChecklistViatura
    extra = 0
    fields = ('tipo', 'data_hora', 'odometro', 'policial')
    readonly_fields = ('data_hora', 'registrado_por')
    show_change_link = True


class EvidenciaInline(admin.TabularInline):
    model = EvidenciaManutencao
    extra = 0
    readonly_fields = ('data_upload', 'registrado_por')
    show_change_link = True


class ServicoManutencaoInline(admin.TabularInline):
    model = ServicoManutencao
    extra = 0
    fields = ('descricao', 'custo_pecas', 'custo_mao_obra', 'odometro', 'data_registro')
    readonly_fields = ('data_registro', 'registrado_por', 'status_na_epoca')
    show_change_link = True


class RetiradaPecaItemInline(admin.TabularInline):
    model = RetiradaPecaItem
    extra = 0
    autocomplete_fields = ('peca',)
    show_change_link = True


class RegistroHistoricoInline(admin.TabularInline):
    model = RegistroHistoricoManutencao
    extra = 0
    fields = ('tipo', 'titulo', 'data_registro', 'registrado_por')
    readonly_fields = ('tipo', 'titulo', 'descricao', 'metadados', 'data_registro', 'registrado_por', 'servico')
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PlanoPreventivoInline(admin.TabularInline):
    model = PlanoManutencaoPreventiva
    extra = 0
    fields = ('descricao', 'intervalo_km', 'intervalo_dias', 'ativo')
    show_change_link = True


# ============================================================================
# HELPERS — badges HTML reutilizáveis
# ============================================================================
def _badge(text, color):
    """Retorna um badge Bootstrap para exibição no admin."""
    return format_html(
        '<span style="background:{}; color:#fff; padding:2px 8px; '
        'border-radius:4px; font-size:11px; font-weight:600;">{}</span>',
        color, text,
    )


_STATUS_COLORS = {
    'DISPONIVEL': '#27ae60',
    'EM_USO': '#f39c12',
    'MANUTENCAO': '#e74c3c',
    'VISTORIA': '#8e44ad',
    'PREGAO': '#95a5a6',
    'BAIXADA': '#2c3e50',
}


# ============================================================================
# MARCA
# ============================================================================
@admin.register(MarcaViatura)
class MarcaViaturaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo', 'total_modelos')
    search_fields = ('nome',)
    list_filter = ('ativo',)
    actions = ['ativar_selecionadas', 'desativar_selecionadas']
    inlines = [ModeloViaturaInline]

    @admin.display(description='Modelos', ordering='modelos_count')
    def total_modelos(self, obj):
        return obj.modelos_count if hasattr(obj, 'modelos_count') else obj.modelos.count()

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(modelos_count=Count('modelos'))

    @admin.action(description='Ativar marcas selecionadas')
    def ativar_selecionadas(self, request, queryset):
        n = queryset.update(ativo=True)
        self.message_user(request, f'{n} marca(s) ativada(s).', messages.SUCCESS)

    @admin.action(description='Desativar marcas selecionadas')
    def desativar_selecionadas(self, request, queryset):
        n = queryset.update(ativo=False)
        self.message_user(request, f'{n} marca(s) desativada(s).', messages.WARNING)


# ============================================================================
# MODELO
# ============================================================================
@admin.register(ModeloViatura)
class ModeloViaturaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'marca', 'tipo', 'ativo', 'total_viaturas')
    search_fields = ('nome', 'marca__nome')
    list_filter = ('tipo', 'ativo', 'marca')
    list_select_related = ('marca',)
    autocomplete_fields = ('marca',)
    actions = ['ativar_selecionados', 'desativar_selecionados']

    @admin.display(description='Viaturas', ordering='viaturas_count')
    def total_viaturas(self, obj):
        return obj.viaturas_count if hasattr(obj, 'viaturas_count') else obj.viaturas.count()

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(viaturas_count=Count('viaturas'))

    @admin.action(description='Ativar modelos selecionados')
    def ativar_selecionados(self, request, queryset):
        n = queryset.update(ativo=True)
        self.message_user(request, f'{n} modelo(s) ativado(s).', messages.SUCCESS)

    @admin.action(description='Desativar modelos selecionados')
    def desativar_selecionados(self, request, queryset):
        n = queryset.update(ativo=False)
        self.message_user(request, f'{n} modelo(s) desativado(s).', messages.WARNING)


# ============================================================================
# VIATURA
# ============================================================================
@admin.register(Viatura)
class ViaturaAdmin(SimpleHistoryAdmin):
    list_display = (
        'prefixo', 'placa', 'get_modelo', 'get_tipo',
        'status_badge', 'localizacao', 'odometro_atual',
        'ano_fabricacao',
    )
    search_fields = (
        'prefixo', 'placa', 'chassi', 'renavam',
        'numero_patrimonio', 'modelo__nome', 'modelo__marca__nome',
    )
    list_filter = (
        'status', 'modelo__tipo', 'tipo_combustivel',
        'localizacao', 'ano_fabricacao',
    )
    list_select_related = ('modelo', 'modelo__marca')
    autocomplete_fields = ('modelo',)
    readonly_fields = ('data_cadastro', 'data_atualizacao')
    actions = [
        'marcar_disponivel', 'marcar_manutencao', 'marcar_baixada',
        'exportar_prefixos',
    ]

    fieldsets = (
        ('Identificação', {
            'fields': ('prefixo', 'placa', 'chassi', 'renavam', 'numero_patrimonio'),
        }),
        ('Modelo e Aparência', {
            'fields': ('modelo', 'ano_fabricacao', 'cor'),
        }),
        ('Combustível e Rodagem', {
            'fields': ('tipo_combustivel', 'capacidade_tanque', 'odometro_atual'),
        }),
        ('Status e Localização', {
            'fields': ('status', 'localizacao'),
        }),
        ('Observações', {
            'fields': ('observacoes',),
        }),
        ('Auditoria', {
            'fields': ('data_cadastro', 'data_atualizacao'),
            'classes': ('collapse',),
        }),
    )

    inlines = [
        DocumentoViaturaInline, DespachoViaturaInline,
        ManutencaoInline, ChecklistViaturaInline,
    ]

    @admin.display(description='Modelo', ordering='modelo__nome')
    def get_modelo(self, obj):
        return f'{obj.modelo.marca.nome} {obj.modelo.nome}'

    @admin.display(description='Tipo')
    def get_tipo(self, obj):
        return obj.modelo.get_tipo_display()

    @admin.display(description='Status')
    def status_badge(self, obj):
        color = _STATUS_COLORS.get(obj.status, '#95a5a6')
        return _badge(obj.get_status_display(), color)

    # Actions
    @admin.action(description='Marcar como Disponível')
    def marcar_disponivel(self, request, queryset):
        n = queryset.update(status=StatusViatura.DISPONIVEL)
        self.message_user(request, f'{n} viatura(s) marcada(s) como Disponível.', messages.SUCCESS)

    @admin.action(description='Marcar como Em Manutenção')
    def marcar_manutencao(self, request, queryset):
        n = queryset.update(status=StatusViatura.MANUTENCAO, localizacao='OFICINA')
        self.message_user(request, f'{n} viatura(s) marcada(s) como Em Manutenção.', messages.WARNING)

    @admin.action(description='Marcar como Baixada')
    def marcar_baixada(self, request, queryset):
        n = queryset.update(status=StatusViatura.BAIXADA)
        self.message_user(request, f'{n} viatura(s) marcada(s) como Baixada.', messages.WARNING)

    @admin.action(description='Exportar lista de prefixos')
    def exportar_prefixos(self, request, queryset):
        prefixos = list(queryset.values_list('prefixo', flat=True))
        self.message_user(
            request,
            f'Prefixos ({len(prefixos)}): {", ".join(prefixos)}',
            messages.INFO,
        )


# ============================================================================
# DESPACHO
# ============================================================================
@admin.register(DespachoViatura)
class DespachoViaturaAdmin(admin.ModelAdmin):
    list_display = (
        'get_viatura', 'motorista', 'encarregado',
        'data_saida', 'km_saida', 'data_retorno', 'km_retorno',
        'status_despacho', 'registrado_por',
    )
    search_fields = (
        'viatura__prefixo', 'viatura__placa',
        'motorista__nome_guerra', 'motorista__re',
        'encarregado__nome_guerra',
    )
    list_filter = (
        'data_saida', 'data_retorno',
        'viatura__status', 'viatura__modelo__tipo',
    )
    list_select_related = ('viatura', 'viatura__modelo', 'motorista', 'encarregado', 'registrado_por')
    autocomplete_fields = ('viatura', 'motorista', 'encarregado', 'registrado_por')
    readonly_fields = ('data_saida',)
    date_hierarchy = 'data_saida'

    fieldsets = (
        ('Despacho', {
            'fields': ('viatura', 'motorista', 'encarregado', 'km_saida', 'observacoes_saida'),
        }),
        ('Retorno', {
            'fields': ('data_retorno', 'km_retorno', 'observacoes_retorno'),
        }),
        ('Registro', {
            'fields': ('registrado_por', 'data_saida'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Viatura', ordering='viatura__prefixo')
    def get_viatura(self, obj):
        return obj.viatura.prefixo

    @admin.display(description='Situação')
    def status_despacho(self, obj):
        if obj.data_retorno:
            return _badge('Retornou', '#27ae60')
        return _badge('Em Despacho', '#e74c3c')

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('viatura', 'viatura__modelo', 'motorista', 'encarregado', 'registrado_por')
        )


# ============================================================================
# ABASTECIMENTO
# ============================================================================
@admin.register(Abastecimento)
class AbastecimentoAdmin(admin.ModelAdmin):
    list_display = (
        'get_viatura', 'data_abastecimento', 'combustivel',
        'quantidade_litros', 'valor_total', 'odometro',
        'get_motorista', 'posto_fornecedor',
    )
    search_fields = (
        'viatura__prefixo', 'viatura__placa',
        'motorista__nome_guerra', 'cupom_fiscal', 'posto_fornecedor',
    )
    list_filter = ('combustivel', 'data_abastecimento', 'viatura__modelo__tipo')
    list_select_related = ('viatura', 'motorista')
    autocomplete_fields = ('viatura', 'motorista', 'registrado_por')
    date_hierarchy = 'data_abastecimento'

    @admin.display(description='Viatura', ordering='viatura__prefixo')
    def get_viatura(self, obj):
        return obj.viatura.prefixo

    @admin.display(description='Motorista', ordering='motorista__nome_guerra')
    def get_motorista(self, obj):
        return obj.motorista.nome_guerra if obj.motorista else '—'


# ============================================================================
# OFICINA
# ============================================================================
@admin.register(Oficina)
class OficinaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'cidade', 'especialidade', 'telefone', 'ativo', 'total_manutencoes')
    search_fields = ('nome', 'cnpj', 'cidade', 'especialidade', 'contato_responsavel')
    list_filter = ('ativo', 'cidade', 'especialidade')
    actions = ['ativar_selecionadas', 'desativar_selecionadas']

    fieldsets = (
        ('Dados da Oficina', {
            'fields': ('nome', 'cnpj', 'especialidade'),
        }),
        ('Contato', {
            'fields': ('endereco', 'cidade', 'telefone', 'contato_responsavel'),
        }),
        ('Status', {
            'fields': ('ativo',),
        }),
    )

    @admin.display(description='Manutenções')
    def total_manutencoes(self, obj):
        return obj.manutencoes.count()

    @admin.action(description='Ativar oficinas selecionadas')
    def ativar_selecionadas(self, request, queryset):
        n = queryset.update(ativo=True)
        self.message_user(request, f'{n} oficina(s) ativada(s).', messages.SUCCESS)

    @admin.action(description='Desativar oficinas selecionadas')
    def desativar_selecionadas(self, request, queryset):
        n = queryset.update(ativo=False)
        self.message_user(request, f'{n} oficina(s) desativada(s).', messages.WARNING)


# ============================================================================
# MANUTENÇÃO
# ============================================================================
@admin.register(Manutencao)
class ManutencaoAdmin(SimpleHistoryAdmin):
    list_display = (
        'get_viatura', 'tipo', 'status_badge', 'data_inicio',
        'data_conclusao', 'get_oficina', 'custo_total_display',
        'get_registrado_por',
    )
    search_fields = (
        'viatura__prefixo', 'viatura__placa',
        'oficina', 'ordem_servico', 'descricao',
        'oficina_fk__nome',
    )
    list_filter = (
        'tipo', 'status', 'data_inicio',
        'data_conclusao', 'oficina_fk',
        'viatura__modelo__tipo',
    )
    list_select_related = ('viatura', 'oficina_fk', 'registrado_por')
    autocomplete_fields = ('viatura', 'oficina_fk', 'registrado_por', 'retirada_pecas')
    date_hierarchy = 'data_inicio'
    inlines = [ServicoManutencaoInline, EvidenciaInline, RegistroHistoricoInline]

    readonly_fields = (
        'data_criacao', 'data_atualizacao',
    )

    fieldsets = (
        (_('Dados da Manutenção'), {
            'fields': (
                'viatura', 'tipo', 'status', 'data_inicio', 'data_conclusao',
                'odometro', 'oficina_fk', 'oficina', 'ordem_servico', 'descricao',
            ),
        }),
        (_('Custos'), {
            'fields': ('custo_pecas', 'custo_mao_obra'),
        }),
        (_('Controle e Qualidade'), {
            'fields': (
                'servicos_executados_corretamente', 'detalhamento_servicos',
                'detalhamento_pecas_garantia', 'nota_fiscal', 'termo_garantia',
                'data_validade_garantia', 'km_validade_garantia', 'retirada_pecas',
            ),
        }),
        (_('Aprovação / Cancelamento'), {
            'fields': (
                'aprovado_por', 'data_aprovacao', 'parecer_aprovacao',
                'cancelado_por', 'data_cancelamento', 'motivo_cancelamento',
            ),
            'classes': ('collapse',),
        }),
        (_('Auditoria'), {
            'fields': ('registrado_por', 'data_criacao', 'data_atualizacao'),
            'classes': ('collapse',),
        }),
    )

    actions = [
        'marcar_concluida', 'marcar_cancelada',
        'marcar_aguardando_peca', 'exportar_relatorio',
    ]

    @admin.display(description='Viatura', ordering='viatura__prefixo')
    def get_viatura(self, obj):
        return obj.viatura.prefixo

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'AGENDADA': '#3498db', 'ABERTA': '#e74c3c',
            'AGUARDANDO_PECA': '#f39c12', 'CONCLUIDA': '#27ae60',
            'CANCELADA': '#95a5a6',
        }
        return _badge(obj.get_status_display(), colors.get(obj.status, '#95a5a6'))

    @admin.display(description='Oficina', ordering='oficina_fk__nome')
    def get_oficina(self, obj):
        if obj.oficina_fk:
            return obj.oficina_fk.nome
        return obj.oficina or '—'

    @admin.display(description='Custo Total', ordering='custo_total_calc')
    def custo_total_display(self, obj):
        total = obj.custo_pecas + obj.custo_mao_obra
        return f'R$ {total:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

    @admin.display(description='Registrado por', ordering='registrado_por__username')
    def get_registrado_por(self, obj):
        return obj.registrado_por.get_short_name() if obj.registrado_por else '—'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            custo_total_calc=F('custo_pecas') + F('custo_mao_obra'),
        ).select_related('viatura', 'oficina_fk', 'registrado_por')

    # Actions
    @admin.action(description='Marcar como Concluída')
    def marcar_concluida(self, request, queryset):
        agora = timezone.now()
        n = queryset.filter(status__in=['ABERTA', 'AGUARDANDO_PECA', 'AGENDADA']).update(
            status=StatusManutencao.CONCLUIDA, data_conclusao=agora.date(),
        )
        self.message_user(request, f'{n} manutenção(ões) concluída(s).', messages.SUCCESS)

    @admin.action(description='Marcar como Cancelada')
    def marcar_cancelada(self, request, queryset):
        n = queryset.exclude(status='CANCELADA').update(status=StatusManutencao.CANCELADA)
        self.message_user(request, f'{n} manutenção(ões) cancelada(s).', messages.WARNING)

    @admin.action(description='Marcar como Aguardando Peça')
    def marcar_aguardando_peca(self, request, queryset):
        n = queryset.filter(status='ABERTA').update(status=StatusManutencao.AGUARDANDO_PECA)
        self.message_user(request, f'{n} manutenção(ões) → Aguardando Peça.', messages.INFO)

    @admin.action(description='Exportar resumo de custos')
    def exportar_relatorio(self, request, queryset):
        agg = queryset.aggregate(
            total_pecas=Sum('custo_pecas'),
            total_mao_obra=Sum('custo_mao_obra'),
            qtd=Count('id'),
        )
        tp = agg['total_pecas'] or Decimal('0')
        tm = agg['total_mao_obra'] or Decimal('0')
        self.message_user(
            request,
            f'{agg["qtd"]} manutenções | Peças: R$ {tp:,.2f} | '
            f'Mão de obra: R$ {tm:,.2f} | Total: R$ {tp + tm:,.2f}',
            messages.INFO,
        )


# ============================================================================
# SERVIÇO DE MANUTENÇÃO
# ============================================================================
@admin.register(ServicoManutencao)
class ServicoManutencaoAdmin(admin.ModelAdmin):
    list_display = (
        'get_viatura', 'descricao_curta', 'custo_pecas',
        'custo_mao_obra', 'custo_total_display', 'odometro',
        'status_na_epoca', 'data_registro',
    )
    search_fields = (
        'manutencao__viatura__prefixo', 'descricao', 'detalhamento',
    )
    list_filter = ('status_na_epoca', 'data_registro')
    list_select_related = ('manutencao', 'manutencao__viatura', 'registrado_por')
    readonly_fields = ('data_registro', 'registrado_por')
    date_hierarchy = 'data_registro'

    @admin.display(description='Viatura', ordering='manutencao__viatura__prefixo')
    def get_viatura(self, obj):
        return obj.manutencao.viatura.prefixo

    @admin.display(description='Descrição')
    def descricao_curta(self, obj):
        return obj.descricao[:80] + ('…' if len(obj.descricao) > 80 else '')

    @admin.display(description='Custo Total')
    def custo_total_display(self, obj):
        total = obj.custo_pecas + obj.custo_mao_obra
        return f'R$ {total:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


# ============================================================================
# EVIDÊNCIA DE MANUTENÇÃO
# ============================================================================
@admin.register(EvidenciaManutencao)
class EvidenciaManutencaoAdmin(admin.ModelAdmin):
    list_display = ('get_viatura', 'tipo', 'descricao', 'data_upload', 'registrado_por')
    search_fields = ('manutencao__viatura__prefixo', 'descricao')
    list_filter = ('tipo', 'data_upload')
    list_select_related = ('manutencao', 'manutencao__viatura', 'registrado_por')
    readonly_fields = ('data_upload', 'registrado_por')

    @admin.display(description='Viatura', ordering='manutencao__viatura__prefixo')
    def get_viatura(self, obj):
        return obj.manutencao.viatura.prefixo


# ============================================================================
# REGISTRO HISTÓRICO MANUTENÇÃO (append-only)
# ============================================================================
@admin.register(RegistroHistoricoManutencao)
class RegistroHistoricoManutencaoAdmin(admin.ModelAdmin):
    list_display = ('get_viatura', 'tipo', 'titulo', 'data_registro', 'registrado_por')
    search_fields = ('manutencao__viatura__prefixo', 'titulo', 'descricao')
    list_filter = ('tipo', 'data_registro')
    list_select_related = ('manutencao', 'manutencao__viatura', 'registrado_por')
    readonly_fields = (
        'manutencao', 'tipo', 'titulo', 'descricao',
        'servico', 'metadados', 'registrado_por', 'data_registro',
    )
    date_hierarchy = 'data_registro'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Viatura', ordering='manutencao__viatura__prefixo')
    def get_viatura(self, obj):
        return obj.manutencao.viatura.prefixo


# ============================================================================
# CHECKLIST
# ============================================================================
@admin.register(ChecklistViatura)
class ChecklistViaturaAdmin(SimpleHistoryAdmin):
    list_display = (
        'get_viatura', 'tipo', 'policial', 'data_hora',
        'odometro', 'resultado',
    )
    search_fields = (
        'viatura__prefixo', 'viatura__placa',
        'policial__nome_guerra', 'policial__re',
    )
    list_filter = ('tipo', 'data_hora', 'viatura__status')
    list_select_related = ('viatura', 'policial', 'registrado_por')
    readonly_fields = ('data_hora', 'registrado_por')
    date_hierarchy = 'data_hora'

    fieldsets = (
        ('Identificação', {
            'fields': ('viatura', 'policial', 'tipo', 'odometro'),
        }),
        ('Conservação e Limpeza', {
            'fields': ('limpeza_interna', 'limpeza_externa', 'conservacao_estofados'),
        }),
        ('Mecânica e Fluídos', {
            'fields': ('niveis_fluidos', 'pneus_condicoes', 'pneu_estepe', 'freio_estacionamento'),
        }),
        ('Elétrica e Sinalização', {
            'fields': ('farois_lanternas', 'setas_emergencia', 'giroflex_sirene', 'painel_instrumentos'),
        }),
        ('Equipamentos e Acessórios', {
            'fields': (
                'extintor_incendio', 'triangulo_macaco_chave', 'cones_sinalizacao',
                'documentacao_crlv', 'kit_primeiros_socorros',
            ),
        }),
        ('Danos e Observações', {
            'fields': ('avarias_lataria', 'observacoes_gerais'),
        }),
        ('Auditoria', {
            'fields': ('registrado_por', 'data_hora'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Viatura', ordering='viatura__prefixo')
    def get_viatura(self, obj):
        return obj.viatura.prefixo

    @admin.display(description='Resultado')
    def resultado(self, obj):
        checks = [
            obj.limpeza_interna, obj.limpeza_externa, obj.conservacao_estofados,
            obj.niveis_fluidos, obj.pneus_condicoes, obj.pneu_estepe,
            obj.freio_estacionamento, obj.farois_lanternas, obj.setas_emergencia,
            obj.giroflex_sirene, obj.painel_instrumentos, obj.extintor_incendio,
            obj.triangulo_macaco_chave, obj.cones_sinalizacao,
            obj.documentacao_crlv, obj.kit_primeiros_socorros,
        ]
        ok = sum(checks)
        total = len(checks)
        if ok == total:
            return _badge(f'{ok}/{total} OK', '#27ae60')
        return _badge(f'{ok}/{total} OK', '#e74c3c')


# ============================================================================
# SOLICITAÇÃO DE BAIXA
# ============================================================================
@admin.register(SolicitacaoBaixaViatura)
class SolicitacaoBaixaViaturaAdmin(admin.ModelAdmin):
    list_display = (
        'get_viatura', 'categoria_motivo', 'status_badge',
        'solicitante', 'motorista', 'data_solicitacao', 'analisado_por',
    )
    search_fields = (
        'viatura__prefixo', 'viatura__placa', 'motivo',
        'solicitante__username',
    )
    list_filter = ('status', 'categoria_motivo', 'data_solicitacao')
    list_select_related = ('viatura', 'solicitante', 'motorista', 'requisitante', 'analisado_por')
    readonly_fields = ('solicitante', 'data_solicitacao')
    date_hierarchy = 'data_solicitacao'
    actions = ['aprovar_baixa', 'negar_baixa']

    fieldsets = (
        ('Solicitação', {
            'fields': (
                'viatura', 'categoria_motivo', 'quilometragem_baixa',
                'motorista', 'requisitante', 'motivo',
            ),
        }),
        ('Análise', {
            'fields': ('status', 'observacoes_admin', 'analisado_por', 'data_analise'),
        }),
        ('Auditoria', {
            'fields': ('solicitante', 'data_solicitacao'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Viatura', ordering='viatura__prefixo')
    def get_viatura(self, obj):
        return obj.viatura.prefixo

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'PENDENTE': '#f39c12', 'NEGADA': '#e74c3c',
            'DESCARGA': '#2c3e50', 'PREGAO': '#95a5a6',
        }
        return _badge(obj.get_status_display(), colors.get(obj.status, '#3498db'))

    @admin.action(description='Aprovar baixa (Descarga Definitiva)')
    def aprovar_baixa(self, request, queryset):
        pendentes = queryset.filter(status=StatusBaixa.PENDENTE)
        n = pendentes.update(status=StatusBaixa.DESCARGA, analisado_por=request.user, data_analise=timezone.now())
        # Atualizar status das viaturas
        Viatura.objects.filter(
            solicitacoes_baixa__in=pendentes,
        ).update(status=StatusViatura.BAIXADA)
        self.message_user(request, f'{n} baixa(s) aprovada(s) como Descarga.', messages.SUCCESS)

    @admin.action(description='Negar solicitações de baixa')
    def negar_baixa(self, request, queryset):
        n = queryset.filter(status=StatusBaixa.PENDENTE).update(
            status=StatusBaixa.NEGADA, analisado_por=request.user, data_analise=timezone.now(),
        )
        self.message_user(request, f'{n} baixa(s) negada(s).', messages.WARNING)


# ============================================================================
# PEÇA
# ============================================================================
@admin.register(PecaViatura)
class PecaViaturaAdmin(admin.ModelAdmin):
    list_display = (
        'nome', 'codigo', 'categoria', 'marca_fabricante',
        'quantidade_estoque', 'limite_minimo', 'estoque_status',
        'valor_unitario', 'ativo',
    )
    search_fields = ('nome', 'codigo', 'marca_fabricante', 'aplicacao')
    list_filter = ('categoria', 'ativo', 'marca_fabricante')
    actions = ['ativar_selecionadas', 'desativar_selecionadas', 'exportar_estoque_baixo']

    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'codigo', 'categoria', 'marca_fabricante'),
        }),
        ('Aplicação', {
            'fields': ('aplicacao',),
        }),
        ('Estoque e Custos', {
            'fields': (
                'quantidade_estoque', 'limite_minimo',
                'localizacao_estoque', 'valor_unitario',
            ),
        }),
        ('Status', {
            'fields': ('ativo', 'observacoes'),
        }),
    )

    @admin.display(description='Estoque')
    def estoque_status(self, obj):
        if obj.quantidade_estoque <= 0:
            return _badge('Zerado', '#e74c3c')
        if obj.limite_minimo and obj.quantidade_estoque <= obj.limite_minimo:
            return _badge('Baixo', '#f39c12')
        return _badge('Normal', '#27ae60')

    @admin.action(description='Ativar peças selecionadas')
    def ativar_selecionadas(self, request, queryset):
        n = queryset.update(ativo=True)
        self.message_user(request, f'{n} peça(s) ativada(s).', messages.SUCCESS)

    @admin.action(description='Desativar peças selecionadas')
    def desativar_selecionadas(self, request, queryset):
        n = queryset.update(ativo=False)
        self.message_user(request, f'{n} peça(s) desativada(s).', messages.WARNING)

    @admin.action(description='Listar peças com estoque baixo')
    def exportar_estoque_baixo(self, request, queryset):
        baixas = queryset.filter(quantidade_estoque__lte=F('limite_minimo'), ativo=True)
        nomes = list(baixas.values_list('nome', flat=True)[:20])
        self.message_user(
            request,
            f'Peças com estoque baixo ({baixas.count()}): {", ".join(nomes)}',
            messages.WARNING,
        )


# ============================================================================
# RETIRADA DE PEÇA
# ============================================================================
@admin.register(RetiradaPeca)
class RetiradaPecaAdmin(admin.ModelAdmin):
    list_display = (
        'get_viatura', 'policial', 'data_retirada',
        'total_itens', 'assinado_eletronicamente', 'registrado_por',
    )
    search_fields = (
        'viatura__prefixo', 'viatura__placa',
        'policial__nome_guerra', 'policial__re',
    )
    list_filter = ('data_retirada', 'assinado_eletronicamente')
    list_select_related = ('viatura', 'policial', 'registrado_por')
    autocomplete_fields = ('viatura', 'policial', 'registrado_por')
    readonly_fields = ('data_retirada', 'registrado_por')
    inlines = [RetiradaPecaItemInline]
    date_hierarchy = 'data_retirada'

    @admin.display(description='Viatura', ordering='viatura__prefixo')
    def get_viatura(self, obj):
        return obj.viatura.prefixo

    @admin.display(description='Itens')
    def total_itens(self, obj):
        return obj.itens.count()

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('viatura', 'policial', 'registrado_por')
            .annotate(itens_count=Count('itens'))
        )


# ============================================================================
# PLANO DE MANUTENÇÃO PREVENTIVA
# ============================================================================
@admin.register(PlanoManutencaoPreventiva)
class PlanoManutencaoPreventivaAdmin(admin.ModelAdmin):
    list_display = (
        'get_modelo', 'descricao', 'intervalo_km',
        'intervalo_dias', 'ativo',
    )
    search_fields = ('descricao', 'modelo__nome', 'modelo__marca__nome')
    list_filter = ('ativo', 'modelo__marca', 'modelo__tipo')
    list_select_related = ('modelo', 'modelo__marca')
    autocomplete_fields = ('modelo',)
    actions = ['ativar_selecionados', 'desativar_selecionados']

    @admin.display(description='Modelo', ordering='modelo__nome')
    def get_modelo(self, obj):
        return f'{obj.modelo.marca.nome} {obj.modelo.nome}'

    @admin.action(description='Ativar planos selecionados')
    def ativar_selecionados(self, request, queryset):
        n = queryset.update(ativo=True)
        self.message_user(request, f'{n} plano(s) ativado(s).', messages.SUCCESS)

    @admin.action(description='Desativar planos selecionados')
    def desativar_selecionados(self, request, queryset):
        n = queryset.update(ativo=False)
        self.message_user(request, f'{n} plano(s) desativado(s).', messages.WARNING)


# ============================================================================
# DOCUMENTO DE VIATURA
# ============================================================================
@admin.register(DocumentoViatura)
class DocumentoViaturaAdmin(admin.ModelAdmin):
    list_display = (
        'get_viatura', 'tipo', 'numero_documento',
        'data_emissao', 'data_vencimento', 'vencimento_status', 'ativo',
    )
    search_fields = (
        'viatura__prefixo', 'viatura__placa',
        'numero_documento', 'observacoes',
    )
    list_filter = ('tipo', 'ativo', 'data_vencimento')
    list_select_related = ('viatura', 'registrado_por')
    autocomplete_fields = ('viatura',)
    readonly_fields = ('data_cadastro', 'data_atualizacao', 'registrado_por')
    date_hierarchy = 'data_vencimento'
    actions = ['renovar_selecionados', 'desativar_selecionados']

    @admin.display(description='Viatura', ordering='viatura__prefixo')
    def get_viatura(self, obj):
        return obj.viatura.prefixo

    @admin.display(description='Vencimento')
    def vencimento_status(self, obj):
        status = obj.status_vencimento
        colors = {
            'VIGENTE': '#27ae60', 'EXPIRANDO': '#f39c12',
            'VENCIDO': '#e74c3c', 'INDETERMINADO': '#95a5a6',
        }
        return _badge(status, colors.get(status, '#95a5a6'))

    @admin.action(description='Marcar como renovados (+1 ano)')
    def renovar_selecionados(self, request, queryset):
        from datetime import timedelta
        for doc in queryset.filter(data_vencimento__isnull=False):
            doc.data_vencimento = doc.data_vencimento + timedelta(days=365)
            doc.save(update_fields=['data_vencimento'])
        self.message_user(
            request,
            f'{queryset.count()} documento(s) renovido(s) (+1 ano).',
            messages.SUCCESS,
        )

    @admin.action(description='Desativar documentos selecionados')
    def desativar_selecionados(self, request, queryset):
        n = queryset.update(ativo=False)
        self.message_user(request, f'{n} documento(s) desativado(s).', messages.WARNING)
