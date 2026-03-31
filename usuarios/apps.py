from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'

    def ready(self):
        try:
            from django.contrib.auth.models import Group
            Group.objects.get_or_create(name='reserva_armas')
            Group.objects.get_or_create(name='materiais')
            Group.objects.get_or_create(name='administracao')
        except Exception:
            pass
