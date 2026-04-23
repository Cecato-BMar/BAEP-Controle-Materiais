"""
Models for reserva app - Armas, Policiais and Cautelas
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from apps.core.models import AuditableModel, SoftDeleteModel, ActiveModel


class Policial(ActiveModel):
    """Policial - efetivo da reserva"""
    
    TIPO_POSTO = [
        ('soldado', 'Soldado'),
        ('cb', 'Cabo'),
        ('sgt', 'Sargento'),
        ('tenente', 'Tenente'),
        ('capitao', 'Capitão'),
    ]
    
    re = models.CharField(_('RE'), max_length=20, unique=True)
    nome_guerra = models.CharField(_('Nome de Guerra'), max_length=50)
    nome_completo = models.CharField(_('Nome Completo'), max_length=200)
    cpf = models.CharField(_('CPF'), max_length=14, unique=True)
    rg = models.CharField(_('RG'), max_length=20)
    tipo_posto = models.CharField(_('Posto'), max_length=20, choices=TIPO_POSTO)
    funcao = models.CharField(_('Função'), max_length=100, blank=True)
    telefone = models.CharField(_('Telefone'), max_length=20, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    foto = models.ImageField(_('Foto'), upload_to='policiais/', blank=True, null=True)
    observacoes = models.TextField(_('Observações'), blank=True)
    
    class Meta:
        verbose_name = _('Policial')
        verbose_name_plural = _('Policiais')
        ordering = ['nome_guerra']
        indexes = [
            models.Index(fields=['re']),
            models.Index(fields=['nome_guerra']),
        ]
    
    def __str__(self):
        return f"{self.re} - {self.nome_guerra}"


class LocalizacaoFisica(ActiveModel):
    """Localização física para armas"""
    nome = models.CharField(_('Nome'), max_length=100, unique=True)
    descricao = models.TextField(_('Descrição'), blank=True)
    
    class Meta:
        verbose_name = _('Localização')
        verbose_name_plural = _('Localizações')
        ordering = ['nome']
    
    def __str__(self):
        return self.nome


class Material(AuditableModel, ActiveModel):
    """Material/Arma da reserva"""
    
    TIPO = [
        ('ARMA', 'Arma'),
        ('MUNICAO', 'Munição'),
        ('COLETE', 'Colete'),
        ('RADIO', 'Rádio'),
        ('ALGEMA', 'Algema'),
        ('OUTROS', 'Outros'),
    ]
    
    ESTADO = [
        ('NOVO', 'Novo'),
        ('BOM', 'Bom'),
        ('REGULAR', 'Regular'),
        ('RUIM', 'Ruim'),
    ]
    
    STATUS = [
        ('DISPONIVEL', 'Disponível'),
        ('EM_USO', 'Em Uso'),
        ('MANUTENCAO', 'Manutenção'),
        ('APREENDIDO', 'Apreendido'),
        ('BAIXADO', 'Baixado'),
    ]
    
    tipo = models.CharField(_('Tipo'), max_length=20, choices=TIPO)
    categoria = models.CharField(_('Categoria'), max_length=30, blank=True)
    nome = models.CharField(_('Nome'), max_length=100)
    numero = models.CharField(_('Número'), max_length=50, unique=True)
    quantidade = models.PositiveIntegerField(_('Quantidade'), default=1)
    quantidade_disponivel = models.PositiveIntegerField(_('Disponível'), default=1)
    quantidade_em_uso = models.PositiveIntegerField(_('Em Uso'), default=0)
    estado = models.CharField(_('Estado'), max_length=20, choices=ESTADO)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS, default='DISPONIVEL')
    observacoes = models.TextField(_('Observações'), blank=True)
    imagem = models.ImageField(_('Imagem'), upload_to='materiais/', blank=True, null=True)
    localizacao = models.ForeignKey(
        LocalizacaoFisica, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name=_('Localização')
    )
    
    class Meta:
        verbose_name = _('Material')
        verbose_name_plural = _('Materiais')
        ordering = ['tipo', 'nome']
        indexes = [
            models.Index(fields=['numero']),
            models.Index(fields=['status', 'tipo']),
            models.Index(fields=['localizacao', 'status']),
        ]
    
    def __str__(self):
        return f"{self.nome} ({self.numero})"
    
    @property
    def identificacao(self):
        return f"{self.nome} ({self.numero})"


class Cautela(SoftDeleteModel):
    """Cautela - retirada/devolução de materiais"""
    
    STATUS = [
        ('ATIVA', 'Ativa'),
        ('DEVOLVIDA', 'Devolvida'),
        ('EXTRAVIADA', 'Extraviada'),
    ]
    
    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name='cautelas')
    policial = models.ForeignKey(Policial, on_delete=models.PROTECT, related_name='cautelas')
    data_retirada = models.DateTimeField(_('Data Retirada'), auto_now_add=True)
    data_devolucao = models.DateTimeField(_('Data Devolução'), blank=True, null=True)
    qtde_retirada = models.PositiveIntegerField(_('Qtd Retirada'), default=1)
    qtde_devolvida = models.PositiveIntegerField(_('Qtd Devolvida'), blank=True, null=True)
    obs_retirada = models.TextField(_('Obs Saída'), blank=True)
    obs_devolucao = models.TextField(_('Obs Retorno'), blank=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS, default='ATIVA')
    registro_por = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='cautelas_registradas'
    )
    
    class Meta:
        verbose_name = _('Cautela')
        verbose_name_plural = _('Cautelas')
        ordering = ['-data_retirada']
        indexes = [
            models.Index(fields=['policial', 'status']),
            models.Index(fields=['material', 'status']),
            models.Index(fields=['data_retirada']),
        ]
    
    def __str__(self):
        return f"Cautela {self.material} - {self.policial}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update material quantity
        if self.status == 'ATIVA':
            self.material.status = 'EM_USO'
            self.material.quantidade_em_uso += self.qtde_retirada
            self.material.quantidade_disponivel -= self.qtde_retirada
            self.material.save()
        elif self.status in ['DEVOLVIDA', 'EXTRAVIADA'] and self.qtde_devolvida:
            self.material.status = 'DISPONIVEL'
            self.material.quantidade_em_uso -= self.qtde_devolvida
            self.material.quantidade_disponivel += self.qtde_devolvida
            self.material.save()