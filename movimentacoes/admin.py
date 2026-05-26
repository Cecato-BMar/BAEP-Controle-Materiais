from django.contrib import admin
from .models import Movimentacao, Retirada, Devolucao, RegistroDisparoMunicao

class RetiradaInline(admin.StackedInline):
    model = Retirada
    can_delete = False
    verbose_name_plural = 'Retirada'
    fk_name = 'movimentacao'

class DevolucaoInline(admin.StackedInline):
    model = Devolucao
    can_delete = False
    verbose_name_plural = 'Devolução'
    fk_name = 'movimentacao'

@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'material', 'policial', 'quantidade', 'data_hora', 'registrado_por')
    list_filter = ('tipo', 'data_hora', 'registrado_por')
    search_fields = ('material__nome', 'material__numero', 'policial__nome', 'policial__re')
    readonly_fields = ('data_hora',)
    
    def get_inlines(self, request, obj=None):
        if obj:
            if obj.tipo == 'RETIRADA':
                return [RetiradaInline]
            elif obj.tipo == 'DEVOLUCAO':
                return [DevolucaoInline]
        return []

@admin.register(Retirada)
class RetiradaAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_material', 'get_policial', 'get_quantidade', 'get_data_hora', 'finalidade', 'data_prevista_devolucao')
    list_filter = ('movimentacao__data_hora', 'finalidade')
    search_fields = ('movimentacao__material__nome', 'movimentacao__material__numero', 'movimentacao__policial__nome', 'movimentacao__policial__re', 'finalidade')
    
    def get_material(self, obj):
        return obj.movimentacao.material
    get_material.short_description = 'Material'
    get_material.admin_order_field = 'movimentacao__material__nome'
    
    def get_policial(self, obj):
        return obj.movimentacao.policial
    get_policial.short_description = 'Policial'
    get_policial.admin_order_field = 'movimentacao__policial__nome'
    
    def get_quantidade(self, obj):
        return obj.movimentacao.quantidade
    get_quantidade.short_description = 'Quantidade'
    get_quantidade.admin_order_field = 'movimentacao__quantidade'
    
    def get_data_hora(self, obj):
        return obj.movimentacao.data_hora
    get_data_hora.short_description = 'Data/Hora'
    get_data_hora.admin_order_field = 'movimentacao__data_hora'

@admin.register(Devolucao)
class DevolucaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_material', 'get_policial', 'get_quantidade', 'get_data_hora', 'estado_devolucao')
    list_filter = ('movimentacao__data_hora', 'estado_devolucao')
    search_fields = ('movimentacao__material__nome', 'movimentacao__material__numero', 'movimentacao__policial__nome', 'movimentacao__policial__re')

    def get_material(self, obj):
        return obj.movimentacao.material
    get_material.short_description = 'Material'
    get_material.admin_order_field = 'movimentacao__material__nome'

    def get_policial(self, obj):
        return obj.movimentacao.policial
    get_policial.short_description = 'Policial'
    get_policial.admin_order_field = 'movimentacao__policial__nome'

    def get_quantidade(self, obj):
        return obj.movimentacao.quantidade
    get_quantidade.short_description = 'Quantidade'
    get_quantidade.admin_order_field = 'movimentacao__quantidade'

    def get_data_hora(self, obj):
        return obj.movimentacao.data_hora
    get_data_hora.short_description = 'Data/Hora'
    get_data_hora.admin_order_field = 'movimentacao__data_hora'


@admin.register(RegistroDisparoMunicao)
class RegistroDisparoMunicaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_devolucao_movimentacao', 'get_material', 'quantidade_disparada', 'quantidade_extraviada', 'boletim_ocorrencia', 'data_registro')
    search_fields = (
        'devolucao__movimentacao__material__nome',
        'devolucao__movimentacao__material__numero',
        'devolucao__movimentacao__policial__nome',
        'devolucao__movimentacao__policial__re',
        'boletim_ocorrencia',
    )
    list_filter = ('data_registro',)

    def get_devolucao_movimentacao(self, obj):
        return obj.devolucao.movimentacao
    get_devolucao_movimentacao.short_description = 'Movimentação de Devolução'

    def get_material(self, obj):
        return obj.devolucao.movimentacao.material
    get_material.short_description = 'Material'
