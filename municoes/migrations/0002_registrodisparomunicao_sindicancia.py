from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('municoes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='registrodisparomunicao',
            name='sindicancia',
            field=models.CharField(
                blank=True,
                help_text='Número da sindicância, procedimento ou referência de apuração da perda/extravio.',
                max_length=120,
                null=True,
                verbose_name='Sindicância / Apuração',
            ),
        ),
    ]
