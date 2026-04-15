from django.contrib import admin
from .models import CategoriaPatrimonio, BemPatrimonial, ItemPatrimonial, MovimentacaoPatrimonio

@admin.register(CategoriaPatrimonio)
class CategoriaPatrimonioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo')

@admin.register(BemPatrimonial)
class BemPatrimonialAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'marca', 'ativo')
    list_filter = ('categoria', 'ativo')
    search_fields = ('nome', 'marca')

@admin.register(ItemPatrimonial)
class ItemPatrimonialAdmin(admin.ModelAdmin):
    list_display = ('numero_patrimonio', 'bem', 'status', 'estado_conservacao', 'localizacao', 'responsavel_atual')
    list_filter = ('status', 'estado_conservacao', 'bem__categoria')
    search_fields = ('numero_patrimonio', 'numero_serie', 'bem__nome')

@admin.register(MovimentacaoPatrimonio)
class MovimentacaoPatrimonioAdmin(admin.ModelAdmin):
    list_display = ('item', 'tipo', 'data_hora', 'policial', 'registrado_por')
    list_filter = ('tipo', 'data_hora')
    search_fields = ('item__numero_patrimonio', 'policial__qra')
