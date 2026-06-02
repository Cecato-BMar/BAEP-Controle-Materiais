from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('municoes', '0002_registrodisparomunicao_sindicancia'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='lotemunicao',
            name='quantidade_estojos',
            field=models.PositiveIntegerField(default=0, verbose_name='Quantidade de Estojos em Cautela'),
        ),
        migrations.AddField(
            model_name='registrodisparomunicao',
            name='quantidade_estojos',
            field=models.PositiveIntegerField(default=0, verbose_name='Quantidade de Estojos Devolvidos'),
        ),
        migrations.CreateModel(
            name='DevolucaoCPI',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_item', models.CharField(choices=[('CARTUCHO', 'Cartucho intacto'), ('ESTOJO', 'Estojo vazio')], max_length=20, verbose_name='Tipo do Item')),
                ('quantidade', models.PositiveIntegerField(verbose_name='Quantidade')),
                ('documento_referencia', models.CharField(blank=True, max_length=100, null=True, verbose_name='Documento / Recibo')),
                ('observacoes', models.TextField(blank=True, null=True, verbose_name='Observações')),
                ('data_hora', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Data e Hora')),
                ('lote', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='devolucoes_cpi', to='municoes.lotemunicao', verbose_name='Lote de Munição')),
                ('registrado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='devolucoes_cpi_registradas', to=settings.AUTH_USER_MODEL, verbose_name='Registrado por')),
            ],
            options={
                'verbose_name': 'Devolução ao CPI',
                'verbose_name_plural': 'Devoluções ao CPI',
                'ordering': ['-data_hora'],
            },
        ),
    ]
