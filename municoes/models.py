from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User
from materiais.models import Material
from policiais.models import Policial


class LoteMunicao(models.Model):
    TIPO_MUNICAO_CHOICES = [
        ('REAL', 'Real'),
        ('TREINAMENTO', 'Treinamento'),
        ('FESTIM', 'Festim'),
        ('ELASTOMERO', 'Elastômero'),
    ]

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='municao_lotes',
        limit_choices_to={'tipo': 'MUNICAO'},
        verbose_name=_('Material')
    )
    calibre = models.CharField(_('Calibre'), max_length=50)
    marca = models.CharField(_('Marca/Fabricante'), max_length=50, blank=True, null=True)
    numero_lote = models.CharField(_('Número do Lote'), max_length=100)
    tipo_municao = models.CharField(_('Tipo de Munição'), max_length=20, choices=TIPO_MUNICAO_CHOICES, default='REAL')
    data_fabricacao = models.DateField(_('Data de Fabricação'), blank=True, null=True)
    data_validade = models.DateField(_('Data de Validade'), blank=True, null=True)
    quantidade_inicial = models.PositiveIntegerField(_('Quantidade Inicial'))
    quantidade_atual = models.PositiveIntegerField(_('Quantidade Atual'))
    quantidade_estojos = models.PositiveIntegerField(_('Quantidade de Estojos em Cautela'), default=0)
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)

    class Meta:
        verbose_name = _('Lote de Munição')
        verbose_name_plural = _('Lotes de Munição')
        ordering = ['-data_validade', 'material', 'numero_lote']
        unique_together = ['material', 'numero_lote']

    def __str__(self):
        return f"{self.material.nome} - {self.numero_lote} ({self.calibre})"

    @property
    def vencido(self):
        if self.data_validade:
            return self.data_validade < timezone.now().date()
        return False


class RetiradaMunicao(models.Model):
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='retiradas_municao',
        verbose_name=_('Material')
    )
    lote = models.ForeignKey(
        LoteMunicao,
        on_delete=models.PROTECT,
        related_name='retiradas',
        verbose_name=_('Lote de Munição')
    )
    policial = models.ForeignKey(
        Policial,
        on_delete=models.PROTECT,
        related_name='retiradas_municao',
        verbose_name=_('Policial')
    )
    quantidade = models.PositiveIntegerField(_('Quantidade'))
    finalidade = models.CharField(_('Finalidade'), max_length=100)
    local_uso = models.CharField(_('Local de Uso'), max_length=100, blank=True, null=True)
    data_hora = models.DateTimeField(_('Data e Hora'), default=timezone.now)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='retiradas_municao_registradas', verbose_name=_('Registrado por'))

    class Meta:
        verbose_name = _('Retirada de Munição')
        verbose_name_plural = _('Retiradas de Munição')
        ordering = ['-data_hora']

    def __str__(self):
        return f"Retirada - {self.material} - {self.policial} - {self.data_hora.strftime('%d/%m/%Y %H:%M')}"

    @property
    def quantidade_devolvida(self):
        return sum(devolucao.quantidade for devolucao in self.devolucoes.all())

    @property
    def quantidade_pendente(self):
        return self.quantidade - self.quantidade_devolvida


class DevolucaoMunicao(models.Model):
    retirada = models.ForeignKey(
        RetiradaMunicao,
        on_delete=models.PROTECT,
        related_name='devolucoes',
        verbose_name=_('Retirada de Referência')
    )
    quantidade = models.PositiveIntegerField(_('Quantidade Devolvida'))
    estado_devolucao = models.CharField(_('Estado na Devolução'), max_length=20, choices=Material.ESTADO_CHOICES)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_hora = models.DateTimeField(_('Data e Hora'), default=timezone.now)

    class Meta:
        verbose_name = _('Devolução de Munição')
        verbose_name_plural = _('Devoluções de Munição')
        ordering = ['-data_hora']

    def __str__(self):
        return f"Devolução - {self.retirada.material} - {self.retirada.policial} - {self.data_hora.strftime('%d/%m/%Y %H:%M')}"


class RegistroDisparoMunicao(models.Model):
    devolucao = models.OneToOneField(
        DevolucaoMunicao,
        on_delete=models.CASCADE,
        related_name='registro_disparo',
        verbose_name=_('Devolução')
    )
    quantidade_disparada = models.PositiveIntegerField(_('Quantidade Disparada'), default=0)
    quantidade_estojos = models.PositiveIntegerField(_('Quantidade de Estojos Devolvidos'), default=0)
    quantidade_extraviada = models.PositiveIntegerField(_('Quantidade Extraviada'), default=0)
    justificativa = models.TextField(_('Justificativa'), blank=True, null=True)
    sindicancia = models.CharField(
        _('Sindicância / Apuração'),
        max_length=120,
        blank=True,
        null=True,
        help_text=_('Número da sindicância, procedimento ou referência de apuração da perda/extravio.')
    )
    boletim_ocorrencia = models.CharField(_('B.O. / Relatório'), max_length=100, blank=True, null=True)
    data_registro = models.DateTimeField(_('Data de Registro'), auto_now_add=True)

    class Meta:
        verbose_name = _('Registro de Disparo de Munição')
        verbose_name_plural = _('Registros de Disparo de Munição')
        ordering = ['-data_registro']

    def __str__(self):
        return f"Registro de Disparo - {self.devolucao.retirada.material} - {self.quantidade_disparada} disparadas / {self.quantidade_extraviada} extraviadas"


class DevolucaoCPI(models.Model):
    TIPO_ITEM_CHOICES = [
        ('CARTUCHO', 'Cartucho intacto'),
        ('ESTOJO', 'Estojo vazio'),
    ]

    lote = models.ForeignKey(
        LoteMunicao,
        on_delete=models.PROTECT,
        related_name='devolucoes_cpi',
        verbose_name=_('Lote de Munição')
    )
    tipo_item = models.CharField(_('Tipo do Item'), max_length=20, choices=TIPO_ITEM_CHOICES)
    quantidade = models.PositiveIntegerField(_('Quantidade'))
    documento_referencia = models.CharField(_('Documento / Recibo'), max_length=100, blank=True, null=True)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_hora = models.DateTimeField(_('Data e Hora'), default=timezone.now)
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='devolucoes_cpi_registradas',
        verbose_name=_('Registrado por')
    )

    class Meta:
        verbose_name = _('Devolução ao CPI')
        verbose_name_plural = _('Devoluções ao CPI')
        ordering = ['-data_hora']

    def __str__(self):
        return f"Devolução CPI - {self.lote.numero_lote} - {self.get_tipo_item_display()} ({self.quantidade})"
