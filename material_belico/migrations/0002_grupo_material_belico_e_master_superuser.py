"""Cria o grupo material_belico e promove master a superuser."""
from django.db import migrations


def criar_grupo_material_belico(apps, schema_editor):
    """Cria o grupo de permissão para o módulo Material Bélico."""
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='material_belico')


def promover_master_superuser(apps, schema_editor):
    """Torna o usuário 'master' superuser, se existir."""
    User = apps.get_model('auth', 'User')
    try:
        master = User.objects.get(username='master')
        master.is_superuser = True
        master.is_staff = True
        master.save()

        # Adiciona master ao grupo material_belico
        Group = apps.get_model('auth', 'Group')
        grupo, _ = Group.objects.get_or_create(name='material_belico')
        master.groups.add(grupo)
    except User.DoesNotExist:
        pass


def reverso(apps, schema_editor):
    """Reverso: remove grupo (não remove superuser do master por segurança)."""
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='material_belico').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('material_belico', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(criar_grupo_material_belico, reverso),
        migrations.RunPython(promover_master_superuser, migrations.RunPython.noop),
    ]
