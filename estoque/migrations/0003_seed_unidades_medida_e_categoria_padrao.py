from django.db import migrations


def _seed_data(apps, schema_editor):
    UnidadeMedida = apps.get_model('estoque', 'UnidadeMedida')
    Categoria = apps.get_model('estoque', 'Categoria')

    unidades = [
        ('UN', 'Unidade'),
        ('CX', 'Caixa'),
        ('PCT', 'Pacote'),
        ('KG', 'Quilograma'),
        ('G', 'Grama'),
        ('L', 'Litro'),
        ('ML', 'Mililitro'),
        ('M', 'Metro'),
        ('CM', 'Centímetro'),
    ]

    for sigla, nome in unidades:
        UnidadeMedida.objects.get_or_create(sigla=sigla, defaults={'nome': nome, 'ativo': True})

    Categoria.objects.get_or_create(
        codigo='GERAL',
        defaults={
            'nome': 'Geral',
            'descricao': 'Categoria padrão do sistema',
            'ativo': True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0002_produto_qr_code_imagem_produto_qr_code_token'),
    ]

    operations = [
        migrations.RunPython(_seed_data, migrations.RunPython.noop),
    ]
