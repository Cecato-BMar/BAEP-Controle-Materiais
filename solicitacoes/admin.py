from django.contrib import admin
from .models import Solicitacao, ItemSolicitacao

class ItemSolicitacaoInline(admin.TabularInline):
    model = ItemSolicitacao
    extra = 1
    autocomplete_fields = ['produto']

@admin.register(Solicitacao)
class SolicitacaoAdmin(admin.ModelAdmin):
    list_display = ['id', 'solicitante', 'data_solicitacao', 'status', 'total_itens']
    list_filter = ['status', 'data_solicitacao']
    search_fields = ['solicitante__username', 'solicitante__first_name', 'solicitante__last_name']
    inlines = [ItemSolicitacaoInline]
    list_editable = ['status']
    readonly_fields = ['data_solicitacao', 'data_atualizacao']
    
    fieldsets = (
        ('Informações da Solicitação', {
            'fields': ('solicitante', 'status', 'data_solicitacao', 'data_atualizacao')
        }),
        ('Comunicações', {
            'fields': ('observacoes', 'notas_admin')
        }),
    )

    def total_itens(self, obj):
        return obj.itens.count()
    total_itens.short_description = 'Qtd. Itens'

@admin.register(ItemSolicitacao)
class ItemSolicitacaoAdmin(admin.ModelAdmin):
    list_display = ['solicitacao', 'produto', 'quantidade_solicitada', 'quantidade_atendida']
    list_filter = ['solicitacao__status']
    search_fields = ['produto__nome', 'solicitacao__id']
