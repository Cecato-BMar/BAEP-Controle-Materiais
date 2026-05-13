from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'

    def ready(self):
        # Cria os grupos padrão após cada migrate, evitando queries durante o boot
        from django.db.models.signals import post_migrate
        post_migrate.connect(_criar_grupos_padrao, sender=self)


def _criar_grupos_padrao(sender, **kwargs):
    """
    Garante que todos os grupos de permissão do sistema existam.
    Executado automaticamente após cada 'manage.py migrate'.
    """
    try:
        from django.contrib.auth.models import Group
        grupos = [
            'reserva_armas',
            'logistica',
            'frota',
            'patrimonio',
            'telematica',
            'relatorios',
            'administracao',
        ]
        for nome in grupos:
            Group.objects.get_or_create(name=nome)
    except Exception:
        pass
