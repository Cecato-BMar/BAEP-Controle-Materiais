# Signals do módulo Material Bélico
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def setup_grupo_material_belico_e_master(sender, **kwargs):
    """Após migrate: cria grupo material_belico e promove master a superuser."""
    if sender.name != 'material_belico':
        return
    try:
        from django.contrib.auth.models import Group, User

        grupo, _ = Group.objects.get_or_create(name='material_belico')

        try:
            master = User.objects.get(username='master')
            if not master.is_superuser:
                master.is_superuser = True
                master.is_staff = True
                master.save(update_fields=['is_superuser', 'is_staff'])
                master.groups.add(grupo)
        except User.DoesNotExist:
            pass
    except Exception:
        pass
