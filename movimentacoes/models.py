from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from materiais.models import Material
from policiais.models import Policial
from django.contrib.auth.models import User

class Movimentacao(models.Model):
    TIPO_CHOICES = [
        ('RETIRADA', 'Retirada'),
        ('DEVOLUCAO', 'Devolução'),
    ]
    
    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name='movimentacoes', verbose_name=_('Material'))
    policial = models.ForeignKey(Policial, on_delete=models.PROTECT, related_name='movimentacoes', verbose_name=_('Policial'))
    quantidade = models.PositiveIntegerField(_('Quantidade'))
    tipo = models.CharField(_('Tipo'), max_length=10, choices=TIPO_CHOICES)
    data_hora = models.DateTimeField(_('Data e Hora'), default=timezone.now)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='movimentacoes_registradas', verbose_name=_('Registrado por'))
    
    class Meta:
        verbose_name = _('Movimentação')
        verbose_name_plural = _('Movimentações')
        ordering = ['-data_hora']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.material} - {self.policial} - {self.data_hora.strftime('%d/%m/%Y %H:%M')}"

class Retirada(models.Model):
    movimentacao = models.OneToOneField(Movimentacao, on_delete=models.CASCADE, related_name='retirada', verbose_name=_('Movimentação'))
    data_prevista_devolucao = models.DateTimeField(_('Data Prevista para Devolução'), blank=True, null=True)
    finalidade = models.CharField(_('Finalidade'), max_length=100)
    local_uso = models.CharField(_('Local de Uso'), max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = _('Retirada')
        verbose_name_plural = _('Retiradas')
        ordering = ['-movimentacao__data_hora']
    
    def __str__(self):
        return f"Retirada - {self.movimentacao.material} - {self.movimentacao.policial} - {self.movimentacao.data_hora.strftime('%d/%m/%Y %H:%M')}"

class Devolucao(models.Model):
    movimentacao = models.OneToOneField(Movimentacao, on_delete=models.CASCADE, related_name='devolucao', verbose_name=_('Movimentação'))
    retirada_referencia = models.ForeignKey(Retirada, on_delete=models.PROTECT, related_name='devolucoes', verbose_name=_('Retirada de Referência'))
    estado_devolucao = models.CharField(_('Estado na Devolução'), max_length=20, choices=Material.ESTADO_CHOICES)
    
    class Meta:
        verbose_name = _('Devolução')
        verbose_name_plural = _('Devoluções')
        ordering = ['-movimentacao__data_hora']
    
    def __str__(self):
        return f"Devolução - {self.movimentacao.material} - {self.movimentacao.policial} - {self.movimentacao.data_hora.strftime('%d/%m/%Y %H:%M')}"
