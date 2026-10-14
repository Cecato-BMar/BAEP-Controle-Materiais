from django.contrib import admin
from django.utils import timezone
from simple_history.admin import SimpleHistoryAdmin
from .models import TipoUniforme, EntregaUniforme, AlertaUniforme


@admin.register(TipoUniforme)
class TipoUniformeAdmin(SimpleHistoryAdmin):
    list_display = ('nome', 'prazo_meses', 'dias_alerta', 'ativo', 'criado_em')
    list_filter = ('ativo',)
    search_fields = ('nome',)
    ordering = ('nome',)


@admin.register(EntregaUniforme)
class EntregaUniformeAdmin(SimpleHistoryAdmin):
    list_display = (
        'policial',
        'tipo_uniforme',
        'quantidade',
        'data_entrega',
        'data_vencimento_calc',
        'ativa',
    )
    list_filter = ('ativa', 'tipo_uniforme', 'data_entrega')
    search_fields = ('policial__nome', 'policial__re')
    date_hierarchy = 'data_entrega'
    readonly_fields = ('data_vencimento_calc',)
    ordering = ('-data_entrega', '-criado_em')
    list_select_related = ('policial', 'tipo_uniforme')


@admin.register(AlertaUniforme)
class AlertaUniformeAdmin(admin.ModelAdmin):
    list_display = ('entrega', 'criado_em', 'lido', 'lido_em', 'lido_por')
    list_filter = ('lido',)
    search_fields = ('entrega__policial__nome', 'entrega__policial__re', 'entrega__tipo_uniforme__nome')
    ordering = ('-criado_em',)
    actions = ['marcar_como_lido_action']
    list_select_related = ('entrega__policial', 'entrega__tipo_uniforme', 'lido_por')

    @admin.action(description="Marcar alertas selecionados como lidos")
    def marcar_como_lido_action(self, request, queryset):
        agora = timezone.now()
        atualizados = queryset.filter(lido=False).update(
            lido=True,
            lido_em=agora,
            lido_por=request.user
        )
        self.message_user(request, f"{atualizados} alerta(s) marcado(s) como lido(s).")
