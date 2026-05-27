from django.db import migrations

def adicionar_outra_unidade(apps, schema_editor):
    OrgaoRequisitante = apps.get_model('estoque', 'OrgaoRequisitante')
    OrgaoRequisitante.objects.get_or_create(
        sigla='OUTRA',
        defaults={'nome': 'Outra Unidade', 'ativo': True}
    )

def remover_outra_unidade(apps, schema_editor):
    OrgaoRequisitante = apps.get_model('estoque', 'OrgaoRequisitante')
    OrgaoRequisitante.objects.filter(sigla='OUTRA').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0014_produto_disponivel_solicitacao'),
    ]

    operations = [
        migrations.RunPython(adicionar_outra_unidade, remover_outra_unidade),
    ]
