from django.contrib import admin
from .models import LoteMunicao, RetiradaMunicao, DevolucaoMunicao, RegistroDisparoMunicao


@admin.register(LoteMunicao)
class LoteMunicaoAdmin(admin.ModelAdmin):
    list_display = ('material', 'numero_lote', 'calibre', 'quantidade_atual', 'ativo', 'data_validade')
    list_filter = ('ativo', 'tipo_municao', 'material__tipo')
    search_fields = ('material__nome', 'numero_lote', 'calibre')


@admin.register(RetiradaMunicao)
class RetiradaMunicaoAdmin(admin.ModelAdmin):
    list_display = ('material', 'policial', 'quantidade', 'data_hora')
    search_fields = ('material__nome', 'policial__nome')


@admin.register(DevolucaoMunicao)
class DevolucaoMunicaoAdmin(admin.ModelAdmin):
    list_display = ('retirada', 'quantidade', 'estado_devolucao', 'data_hora')
    search_fields = ('retirada__material__nome', 'retirada__policial__nome')


@admin.register(RegistroDisparoMunicao)
class RegistroDisparoMunicaoAdmin(admin.ModelAdmin):
    list_display = ('devolucao', 'quantidade_disparada', 'quantidade_extraviada', 'data_registro')
    search_fields = ('devolucao__retirada__material__nome',)
