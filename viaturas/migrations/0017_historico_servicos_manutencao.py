# Generated manually for histórico append-only de serviços

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def popular_historico_existente(apps, schema_editor):
    Manutencao = apps.get_model('viaturas', 'Manutencao')
    ServicoManutencao = apps.get_model('viaturas', 'ServicoManutencao')
    RegistroHistoricoManutencao = apps.get_model('viaturas', 'RegistroHistoricoManutencao')

    for man in Manutencao.objects.all().iterator():
        if RegistroHistoricoManutencao.objects.filter(manutencao=man).exists():
            continue
        usuario = man.registrado_por
        RegistroHistoricoManutencao.objects.create(
            manutencao=man,
            tipo='ABERTURA',
            titulo='Abertura da manutenção (migração)',
            descricao=man.descricao or 'Registro importado do sistema anterior.',
            registrado_por=usuario,
        )
        if man.detalhamento_servicos and str(man.detalhamento_servicos).strip():
            servico = ServicoManutencao.objects.create(
                manutencao=man,
                descricao=str(man.detalhamento_servicos).strip(),
                detalhamento=str(man.detalhamento_servicos).strip(),
                pecas_garantia=man.detalhamento_pecas_garantia,
                custo_pecas=man.custo_pecas,
                custo_mao_obra=man.custo_mao_obra,
                odometro=man.odometro,
                status_na_epoca=man.status,
                registrado_por=usuario,
            )
            RegistroHistoricoManutencao.objects.create(
                manutencao=man,
                tipo='SERVICO',
                titulo='Serviço registrado (migração)',
                descricao=servico.descricao,
                servico=servico,
                registrado_por=usuario,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('viaturas', '0016_manutencao_aprovado_por_manutencao_cancelado_por_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ServicoManutencao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.TextField(verbose_name='Descrição do Serviço')),
                ('detalhamento', models.TextField(blank=True, null=True, verbose_name='Detalhamento')),
                ('pecas_garantia', models.TextField(blank=True, null=True, verbose_name='Peças / Garantia')),
                ('custo_pecas', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Custo Peças (R$)')),
                ('custo_mao_obra', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Custo Mão de Obra (R$)')),
                ('odometro', models.DecimalField(blank=True, decimal_places=1, max_digits=10, null=True, verbose_name='Odômetro')),
                ('status_na_epoca', models.CharField(blank=True, choices=[('AGENDADA', 'Agendada (Futura)'), ('ABERTA', 'Em Aberto'), ('AGUARDANDO_PECA', 'Aguardando Peça'), ('CONCLUIDA', 'Concluída'), ('CANCELADA', 'Cancelada')], help_text='Snapshot do status da manutenção no momento do registro', max_length=20, verbose_name='Status na época')),
                ('data_registro', models.DateTimeField(auto_now_add=True, verbose_name='Data do Registro')),
                ('manutencao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='servicos', to='viaturas.manutencao', verbose_name='Manutenção')),
                ('registrado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='servicos_manutencao_registrados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Serviço de Manutenção',
                'verbose_name_plural': 'Serviços de Manutenção',
                'ordering': ['-data_registro'],
            },
        ),
        migrations.CreateModel(
            name='RegistroHistoricoManutencao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('ABERTURA', 'Abertura da Manutenção'), ('SERVICO', 'Serviço Registrado'), ('ATUALIZACAO', 'Atualização Administrativa'), ('STATUS', 'Mudança de Status'), ('CONCLUSAO', 'Conclusão'), ('CANCELAMENTO', 'Cancelamento'), ('EVIDENCIA', 'Evidência Anexada')], max_length=20, verbose_name='Tipo de Evento')),
                ('titulo', models.CharField(max_length=200, verbose_name='Título')),
                ('descricao', models.TextField(blank=True, verbose_name='Descrição')),
                ('metadados', models.JSONField(blank=True, help_text='Dados estruturados da alteração (campos, valores anteriores/novos)', null=True, verbose_name='Metadados')),
                ('data_registro', models.DateTimeField(auto_now_add=True, verbose_name='Data do Registro')),
                ('manutencao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registros_historico', to='viaturas.manutencao', verbose_name='Manutenção')),
                ('registrado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='historicos_manutencao_registrados', to=settings.AUTH_USER_MODEL)),
                ('servico', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eventos_historico', to='viaturas.servicomanutencao', verbose_name='Serviço vinculado')),
            ],
            options={
                'verbose_name': 'Registro de Histórico de Manutenção',
                'verbose_name_plural': 'Registros de Histórico de Manutenção',
                'ordering': ['-data_registro'],
            },
        ),
        migrations.RunPython(popular_historico_existente, migrations.RunPython.noop),
    ]
