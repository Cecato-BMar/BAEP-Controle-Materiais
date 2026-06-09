# Signals do módulo Material Bélico
from django.db import connection
from django.db.models.signals import post_migrate
from django.dispatch import receiver


_setup_done = False


def _ensure_grupo_e_master():
    """Cria grupo material_belico e promove master a superuser (idempotente)."""
    global _setup_done
    if _setup_done:
        return
    _setup_done = True
    try:
        from django.contrib.auth.models import Group, User
        grupo, _ = Group.objects.get_or_create(name='material_belico')
        try:
            master = User.objects.get(username='master')
            changed = False
            if not master.is_superuser:
                master.is_superuser = True
                changed = True
            if not master.is_staff:
                master.is_staff = True
                changed = True
            if changed:
                master.save(update_fields=['is_superuser', 'is_staff'])
            master.groups.add(grupo)
        except User.DoesNotExist:
            pass
    except Exception:
        pass


@receiver(post_migrate, dispatch_uid='setup_material_belico_post_migrate')
def on_post_migrate(sender, **kwargs):
    """Roda após qualquer migrate."""
    _ensure_grupo_e_master()


def setup_on_startup():
    """Chamado pelo AppConfig.ready() para garantir setup mesmo sem migrations pendentes."""
    try:
        # Verifica se as tabelas existem antes de fazer queries
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        _ensure_grupo_e_master()
    except Exception:
        pass
