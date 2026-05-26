from django.contrib import admin
from .models import Material, LoteMunicao

class LoteMunicaoInline(admin.TabularInline):
    model = LoteMunicao
    extra = 0
    fields = ('calibre', 'marca', 'numero_lote', 'tipo_municao', 'data_fabricacao', 'data_validade', 'quantidade_inicial', 'quantidade_atual', 'ativo')
    readonly_fields = ('quantidade_atual',)
    show_change_link = True

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    inlines = [LoteMunicaoInline]
    list_display = ('numero', 'nome', 'tipo', 'quantidade', 'quantidade_disponivel', 'quantidade_em_uso', 'estado', 'status')
    list_filter = ('tipo', 'estado', 'status')
    search_fields = ('nome', 'numero')
    readonly_fields = ('data_cadastro', 'data_atualizacao')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('tipo', 'nome', 'numero', 'imagem')
        }),
        ('Quantidades', {
            'fields': ('quantidade', 'quantidade_disponivel', 'quantidade_em_uso')
        }),
        ('Estado e Status', {
            'fields': ('estado', 'status')
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Datas', {
            'fields': ('data_cadastro', 'data_atualizacao')
        }),
    )


@admin.register(LoteMunicao)
class LoteMunicaoAdmin(admin.ModelAdmin):
    list_display = ('material', 'calibre', 'numero_lote', 'tipo_municao', 'quantidade_inicial', 'quantidade_atual', 'ativo')
    list_filter = ('tipo_municao', 'ativo', 'material__tipo')
    search_fields = ('material__nome', 'numero_lote', 'calibre', 'marca')
    readonly_fields = ('data_cadastro', 'data_atualizacao')
    fieldsets = (
        ('Lote de Munição', {
            'fields': ('material', 'calibre', 'marca', 'numero_lote', 'tipo_municao', 'data_fabricacao', 'data_validade', 'quantidade_inicial', 'quantidade_atual', 'ativo')
        }),
        ('Datas', {
            'fields': ('data_cadastro', 'data_atualizacao')
        }),
    )
