from django.db import migrations


def criar_grupo_frota(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='frota')


def remover_grupo_frota(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='frota').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('viaturas', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(criar_grupo_frota, remover_grupo_frota),
    ]
