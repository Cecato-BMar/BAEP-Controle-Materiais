from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User

class Relatorio(models.Model):
    TIPO_CHOICES = [
        ('SITUACAO_ATUAL', 'Reserva: Situação Atual'),
        ('MATERIAIS_EM_USO', 'Reserva: Materiais em Uso'),
        ('MATERIAIS_DISPONIVEIS', 'Reserva: Materiais Disponíveis'),
        ('MOVIMENTACOES_PERIODO', 'Reserva: Movimentações por Período'),
        ('ESTOQUE_INVENTARIO', 'Estoque: Inventário Geral'),
        ('ESTOQUE_CRITICO', 'Estoque: Reposição Crítica'),
        ('ESTOQUE_MOVIMENTACOES', 'Estoque: Histórico de Movimentações'),
        ('PATRIMONIO_INVENTARIO', 'Patrimônio: Inventário Geral'),
        ('PATRIMONIO_MOVIMENTACOES', 'Patrimônio: Histórico de Movimentações'),
        ('FROTA_GERAL', 'Frota: Relatório Geral de Viaturas'),
        ('FROTA_ABASTECIMENTO', 'Frota: Relatório de Abastecimentos'),
        ('FROTA_MANUTENCAO', 'Frota: Histórico de Manutenções'),
    ]
    
    titulo = models.CharField(_('Título'), max_length=100)
    tipo = models.CharField(_('Tipo'), max_length=30, choices=TIPO_CHOICES)
    modulo = models.CharField(_('Módulo'), max_length=20, choices=[
        ('RESERVA', 'Reserva de Armas'),
        ('ESTOQUE', 'Almoxarifado/Estoque'),
        ('PATRIMONIO', 'Patrimônio'),
        ('FROTA', 'Frota de Viaturas'),
    ], default='RESERVA')
    data_geracao = models.DateTimeField(_('Data de Geração'), default=timezone.now)
    periodo_inicio = models.DateTimeField(_('Período - Início'), blank=True, null=True)
    periodo_fim = models.DateTimeField(_('Período - Fim'), blank=True, null=True)
    gerado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='relatorios_gerados', verbose_name=_('Gerado por'))
    arquivo_pdf = models.FileField(_('Arquivo PDF'), upload_to='relatorios/', blank=True, null=True)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('Relatório')
        verbose_name_plural = _('Relatórios')
        ordering = ['-data_geracao']
    
    def __str__(self):
        return f"{self.titulo} - {self.get_tipo_display()} - {self.data_geracao.strftime('%d/%m/%Y %H:%M')}"
