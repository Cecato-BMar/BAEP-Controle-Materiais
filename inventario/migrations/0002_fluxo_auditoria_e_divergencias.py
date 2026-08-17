# Generated manually for the isolated inventory workflow branch.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='cicloinventario',
            name='status',
            field=models.CharField(
                choices=[
                    ('RASCUNHO', 'Rascunho'),
                    ('EM_PREPARACAO', 'Em preparação'),
                    ('EM_ANDAMENTO', 'Em Andamento / Conferência'),
                    ('EM_ANALISE', 'Em análise de divergências'),
                    ('AGUARDANDO_APROVACAO', 'Aguardando aprovação'),
                    ('CONCLUIDO', 'Concluído'),
                    ('HOMOLOGADO', 'Homologado'),
                    ('ARQUIVADO', 'Arquivado'),
                ],
                default='EM_ANDAMENTO',
                max_length=24,
                verbose_name='Status',
            ),
        ),
        migrations.CreateModel(
            name='MembroComissaoInventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('papel', models.CharField(choices=[('PRESIDENTE', 'Presidente da comissão'), ('MEMBRO', 'Membro da comissão'), ('CONFERENTE', 'Conferente'), ('SUPERVISOR', 'Supervisor de seção'), ('HOMOLOGADOR', 'Homologador')], max_length=20)),
                ('secao_subunidade', models.CharField(blank=True, max_length=150)),
                ('ativo', models.BooleanField(default=True)),
                ('designado_em', models.DateTimeField(auto_now_add=True)),
                ('ciclo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comissao', to='inventario.cicloinventario')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='designacoes_inventario', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Membro da Comissão de Inventário',
                'verbose_name_plural': 'Membros da Comissão de Inventário',
            },
        ),
        migrations.CreateModel(
            name='HistoricoCicloInventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status_anterior', models.CharField(blank=True, max_length=24)),
                ('status_novo', models.CharField(max_length=24)),
                ('justificativa', models.TextField(blank=True)),
                ('realizado_em', models.DateTimeField(auto_now_add=True)),
                ('ciclo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historico', to='inventario.cicloinventario')),
                ('realizado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historicos_ciclo_inventario', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Histórico do Ciclo de Inventário',
                'verbose_name_plural': 'Históricos do Ciclo de Inventário',
                'ordering': ['-realizado_em'],
            },
        ),
        migrations.CreateModel(
            name='ConferenciaInventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resultado', models.CharField(choices=[('CONFIRMADO', 'Confirmado conforme base'), ('COM_RESSALVA', 'Confirmado com ressalva'), ('NAO_LOCALIZADO', 'Não localizado'), ('OUTRA_SECAO', 'Localizado em outra seção'), ('EXCEDENTE', 'Bem excedente'), ('AVARIADO', 'Avariado / inservível'), ('EM_BAIXA', 'Em processo de baixa'), ('SERIE_DIVERGENTE', 'Número de série divergente')], max_length=20)),
                ('situacao_fisica', models.CharField(choices=[('CONFORME', 'Conforme / Em Uso'), ('AVARIADO', 'Avariado / Danificado'), ('NAO_LOCALIZADO', 'Não Localizado / Divergente'), ('EM_EXCLUSAO', 'Processo de Exclusão')], default='CONFORME', max_length=20)),
                ('localizacao_encontrada', models.CharField(blank=True, max_length=200)),
                ('numero_serie_encontrado', models.CharField(blank=True, max_length=100)),
                ('observacoes', models.TextField(blank=True)),
                ('evidencia', models.FileField(blank=True, null=True, upload_to='inventarios/evidencias/%Y/%m/')),
                ('conferido_em', models.DateTimeField(default=django.utils.timezone.now)),
                ('conferido_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conferencias_inventario', to=settings.AUTH_USER_MODEL)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conferencias', to='inventario.iteminventario')),
            ],
            options={
                'verbose_name': 'Conferência de Inventário',
                'verbose_name_plural': 'Conferências de Inventário',
                'ordering': ['-conferido_em'],
            },
        ),
        migrations.CreateModel(
            name='DivergenciaInventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('NAO_LOCALIZADO', 'Falta física'), ('EXCEDENTE', 'Sobra física'), ('OUTRA_SECAO', 'Localização divergente'), ('SERIE_DIVERGENTE', 'Número de série divergente'), ('AVARIADO', 'Bem avariado'), ('EM_BAIXA', 'Bem em processo de baixa'), ('CONTA_DIVERGENTE', 'Conta contábil divergente'), ('DUPLICIDADE', 'Duplicidade de patrimônio')], max_length=24)),
                ('status', models.CharField(choices=[('ABERTA', 'Aberta'), ('EM_APURACAO', 'Em apuração'), ('AGUARDANDO_DOCUMENTO', 'Aguardando documento'), ('REGULARIZADA', 'Regularizada'), ('CONFIRMADA_PARA_BAIXA', 'Confirmada para baixa'), ('IMPROCEDENTE', 'Improcedente')], default='ABERTA', max_length=24)),
                ('descricao', models.TextField()),
                ('providencia', models.TextField(blank=True)),
                ('prazo', models.DateField(blank=True, null=True)),
                ('resolucao', models.TextField(blank=True)),
                ('resolvido_em', models.DateTimeField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('conferencia_origem', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='divergencias', to='inventario.conferenciainventario')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='divergencias', to='inventario.iteminventario')),
                ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='divergencias_inventario_responsavel', to=settings.AUTH_USER_MODEL)),
                ('resolvido_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='divergencias_inventario_resolvidas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Divergência de Inventário',
                'verbose_name_plural': 'Divergências de Inventário',
                'ordering': ['status', '-criado_em'],
            },
        ),
        migrations.AddConstraint(
            model_name='membrocomissaoinventario',
            constraint=models.UniqueConstraint(fields=('ciclo', 'usuario', 'papel'), name='inventario_membro_papel_unico'),
        ),
    ]
