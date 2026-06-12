# Generated for DocumentoViatura (CRLV, Seguro, IPVA, etc.)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viaturas', '0017_historico_servicos_manutencao'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentoViatura',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(
                    choices=[
                        ('CRLV', 'CRLV (Certificado de Registro e Licenciamento)'),
                        ('SEGURO', 'Apólice de Seguro'),
                        ('IPVA', 'IPVA (Imposto sobre Propriedade)'),
                        ('DPVAT', 'DPVAT (Seguro Obrigatório)'),
                        ('VISTORIA', 'Laudo de Vistoria'),
                        ('OUTRO', 'Outro Documento'),
                    ],
                    max_length=20,
                    verbose_name='Tipo de Documento',
                )),
                ('numero_documento', models.CharField(
                    blank=True,
                    max_length=100,
                    verbose_name='Número do Documento',
                )),
                ('data_emissao', models.DateField(
                    blank=True,
                    null=True,
                    verbose_name='Data de Emissão',
                )),
                ('data_vencimento', models.DateField(
                    blank=True,
                    null=True,
                    verbose_name='Data de Vencimento',
                )),
                ('arquivo', models.FileField(
                    blank=True,
                    help_text='PDF ou imagem do documento',
                    null=True,
                    upload_to='viaturas/documentos/%Y/%m/',
                    verbose_name='Arquivo Digital',
                )),
                ('observacoes', models.TextField(
                    blank=True,
                    verbose_name='Observações',
                )),
                ('ativo', models.BooleanField(
                    default=True,
                    verbose_name='Ativo',
                )),
                ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('viatura', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documentos',
                    to='viaturas.viatura',
                )),
                ('registrado_por', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='documentos_registrados',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Registrado por',
                )),
            ],
            options={
                'verbose_name': 'Documento de Viatura',
                'verbose_name_plural': 'Documentos de Viatura',
                'ordering': ['tipo', 'data_vencimento'],
                'unique_together': {('viatura', 'tipo', 'numero_documento')},
            },
        ),
    ]
