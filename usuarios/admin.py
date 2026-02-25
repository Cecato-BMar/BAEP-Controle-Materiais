from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Perfil

class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    verbose_name_plural = 'Perfil'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (PerfilInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_nivel_acesso')
    list_select_related = ('perfil', )

    def get_nivel_acesso(self, instance):
        return instance.perfil.get_nivel_acesso_display()
    get_nivel_acesso.short_description = 'Nível de Acesso'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

# Desregistra o UserAdmin padrão
admin.site.unregister(User)
# Registra o CustomUserAdmin
admin.site.register(User, CustomUserAdmin)

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'nivel_acesso', 'policial', 'telefone', 'data_ultimo_acesso')
    list_filter = ('nivel_acesso',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'policial__nome', 'policial__re')
    readonly_fields = ('data_ultimo_acesso',)
