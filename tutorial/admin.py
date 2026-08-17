from django.contrib import admin
from .models import ModuloTutorial, SecaoTutorial


class SecaoTutorialInline(admin.TabularInline):
    model = SecaoTutorial
    extra = 0
    fields = ('titulo', 'tipo', 'ordem', 'publicado')


@admin.register(ModuloTutorial)
class ModuloTutorialAdmin(admin.ModelAdmin):
    list_display = ('ordem', 'nome', 'slug', 'grupo', 'publicado', 'total_secoes')
    list_display_links = ('nome',)
    list_editable = ('ordem', 'publicado')
    list_filter = ('grupo', 'publicado')
    search_fields = ('nome', 'descricao')
    prepopulated_fields = {'slug': ('nome',)}
    inlines = [SecaoTutorialInline]


@admin.register(SecaoTutorial)
class SecaoTutorialAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'modulo', 'tipo', 'ordem', 'publicado')
    list_editable = ('ordem', 'publicado')
    list_filter = ('tipo', 'modulo', 'publicado')
    search_fields = ('titulo', 'conteudo')