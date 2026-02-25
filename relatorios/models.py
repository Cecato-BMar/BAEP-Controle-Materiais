from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User

class Relatorio(models.Model):
    TIPO_CHOICES = [
        ('SITUACAO_ATUAL', 'Situação Atual'),
        ('MATERIAIS_EM_USO', 'Materiais em Uso'),
        ('MATERIAIS_DISPONIVEIS', 'Materiais Disponíveis'),
        ('MOVIMENTACOES_DIA', 'Movimentações do Dia'),
        ('MOVIMENTACOES_PERIODO', 'Movimentações por Período'),
        ('MOVIMENTACOES_POLICIAL', 'Movimentações por Policial'),
        ('MOVIMENTACOES_MATERIAL', 'Movimentações por Material'),
    ]
    
    titulo = models.CharField(_('Título'), max_length=100)
    tipo = models.CharField(_('Tipo'), max_length=30, choices=TIPO_CHOICES)
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
