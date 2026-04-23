"""
Models for frota app - Vehicles management
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from apps.core.models import AuditableModel, SoftDeleteModel, ActiveModel


class Marca(ActiveModel):
    """Vehicle brand"""
    nome = models.CharField(_('Nome'), max_length=50, unique=True)
    
    class Meta:
        verbose_name = _('Marca')
        verbose_name_plural = _('Marcas')
        ordering = ['nome']
    
    def __str__(self):
        return self.nome


class Modelo(ActiveModel):
    """Vehicle model"""
    TIPO = [
        ('4_RODAS', '4 Rodas'),
        ('MOTO', 'Motocicleta'),
        ('EMBARCACAO', 'Embarcação'),
        ('CAMINHAO', 'Caminhão'),
    ]
    
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT, related_name='modelos')
    nome = models.CharField(_('Nome'), max_length=100)
    tipo = models.CharField(_('Tipo'), max_length=20, choices=TIPO)
    
    class Meta:
        verbose_name = _('Modelo')
        verbose_name_plural = _('Modelos')
        ordering = ['marca__nome', 'nome']
        unique_together = ['marca', 'nome']
    
    def __str__(self):
        return f"{self.marca.nome} {self.nome}"


class Viatura(AuditableModel):
    """Vehicle"""
    
    STATUS = [
        ('DISPONIVEL', 'Disponível'),
        ('EM_USO', 'Em Uso'),
        ('MANUTENCAO', 'Manutenção'),
        ('BAIXADA', 'Baixada'),
    ]
    
    COMBUSTIVEL = [
        ('FLEX', 'Flex'),
        ('GASOLINA', 'Gasolina'),
        ('ALCOOL', 'Etanol'),
        ('DIESEL', 'Diesel'),
        ('ELETRICO', 'Elétrico'),
    ]
    
    prefixo = models.CharField(_('Prefixo'), max_length=20, unique=True)
    placa = models.CharField(_('Placa'), max_length=10, unique=True, blank=True)
    chassi = models.CharField(_('Chassi'), max_length=50, blank=True)
    renavam = models.CharField(_('RENAVAM'), max_length=30, blank=True)
    patrimonio = models.CharField(_('Patrimônio'), max_length=50, blank=True)
    modelo = models.ForeignKey(Modelo, on_delete=models.PROTECT, related_name='viaturas')
    ano = models.PositiveIntegerField(_('Ano'), blank=True, null=True)
    cor = models.CharField(_('Cor'), max_length=30, blank=True)
    combustivel = models.CharField(_('Combustível'), max_length=20, choices=COMBUSTIVEL, default='FLEX')
    capacidade_tanque = models.DecimalField(_('Tanque (L)'), max_digits=6, decimal_places=2, default=Decimal('0'))
    odometro = models.DecimalField(_('Odômetro'), max_digits=10, decimal_places=1, default=Decimal('0'))
    status = models.CharField(_('Status'), max_length=20, choices=STATUS, default='DISPONIVEL')
    observacoes = models.TextField(_('Observações'), blank=True)
    
    class Meta:
        verbose_name = _('Viatura')
        verbose_name_plural = _('Viaturas')
        ordering = ['prefixo']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['prefixo']),
        ]
    
    def __str__(self):
        return f"{self.prefixo} - {self.modelo.nome}"
    
    @property
    def dias_em_uso(self):
        """Days in use in current dispatch"""
        dispatch = self.despachos.filter(data_retorno__isnull=True).first()
        if dispatch:
            from django.utils import timezone
            return (timezone.now() - dispatch.data_saida).days
        return 0


class Oficina(ActiveModel):
    """Workshop/service center"""
    nome = models.CharField(_('Nome'), max_length=150)
    cnpj = models.CharField(_('CNPJ'), max_length=20, blank=True)
    telefone = models.CharField(_('Telefone'), max_length=20, blank=True)
    endereco = models.CharField(_('Endereço'), max_length=255, blank=True)
    
    class Meta:
        verbose_name = _('Oficina')
        verbose_name_plural = _('Oficinas')
        ordering = ['nome']
    
    def __str__(self):
        return self.nome


class Manutencao(SoftDeleteModel):
    """Vehicle maintenance"""
    
    TIPO = [
        ('PREVENTIVA', 'Preventiva'),
        ('CORRETIVA', 'Corretiva'),
    ]
    
    STATUS = [
        ('ABERTA', 'Aberta'),
        ('AGUARDANDO', 'Aguardando Peça'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    viatura = models.ForeignKey(Viatura, on_delete=models.PROTECT, related_name='manutencoes')
    tipo = models.CharField(_('Tipo'), max_length=20, choices=TIPO)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS, default='ABERTA')
    data_inicio = models.DateField(_('Data Início'))
    data_fim = models.DateField(_('Data Fim'), blank=True, null=True)
    odometro = models.DecimalField(_('Odômetro'), max_digits=10, decimal_places=1, blank=True, null=True)
    descricao = models.TextField(_('Descrição'))
    oficina = models.ForeignKey(Oficina, on_delete=models.SET_NULL, null=True, blank=True)
    custo_pecas = models.DecimalField(_('Custo Peças'), max_digits=10, decimal_places=2, default=Decimal('0'))
    custo_mao = models.DecimalField(_('Mão de Obra'), max_digits=10, decimal_places=2, default=Decimal('0'))
    registro_por = models.ForeignKey('core.User', on_delete=models.PROTECT)
    
    class Meta:
        verbose_name = _('Manutenção')
        verbose_name_plural = _('Manutenções')
        ordering = ['-data_inicio']
    
    def __str__(self):
        return f"{self.viatura.prefixo} - {self.get_tipo_display()}"
    
    @property
    def custo_total(self):
        return self.custo_pecas + self.custo_mao


class Abastecimento(SoftDeleteModel):
    """Fuel supply"""
    viatura = models.ForeignKey(Viatura, on_delete=models.PROTECT, related_name='abastecimentos')
    data = models.DateTimeField(_('Data'), auto_now_add=True)
    odometro = models.DecimalField(_('Odômetro'), max_digits=10, decimal_places=1)
    combustivel = models.CharField(_('Combustível'), max_length=20, choices=Viatura.COMBUSTIVEL)
    quantidade = models.DecimalField(_('Quantidade (L)'), max_digits=6, decimal_places=2)
    valor = models.DecimalField(_('Valor (R$)'), max_digits=10, decimal_places=2, blank=True, null=True)
    posto = models.CharField(_('Posto'), max_length=100, blank=True)
    cupom = models.CharField(_('Cupom'), max_length=50, blank=True)
    registro_por = models.ForeignKey('core.User', on_delete=models.PROTECT)
    
    class Meta:
        verbose_name = _('Abastecimento')
        verbose_name_plural = _('Abastecimentos')
        ordering = ['-data']
    
    def __str__(self):
        return f"{self.viatura.prefixo} - {self.data:%d/%m/%Y}"


class Despacho(SoftDeleteModel):
    """Vehicle dispatch"""
    
    STATUS = [
        ('ATIVO', 'Ativo'),
        ('CONCLUIDO', 'Concluído'),
    ]
    
    viatura = models.ForeignKey(Viatura, on_delete=models.PROTECT, related_name='despachos')
    policial = models.ForeignKey('reserva.Policial', on_delete=models.PROTECT, related_name='despachos')
    data_saida = models.DateTimeField(_('Data Saída'), auto_now_add=True)
    km_saida = models.DecimalField(_('Km Saída'), max_digits=10, decimal_places=1)
    data_retorno = models.DateTimeField(_('Data Retorno'), blank=True, null=True)
    km_retorno = models.DecimalField(_('Km Retorno'), max_digits=10, decimal_places=1, blank=True, null=True)
    obs_saida = models.TextField(_('Obs Saída'), blank=True)
    obs_retorno = models.TextField(_('Obs Retorno'), blank=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS, default='ATIVO')
    registro_por = models.ForeignKey('core.User', on_delete=models.PROTECT)
    
    class Meta:
        verbose_name = _('Despacho')
        verbose_name_plural = _('Despachos')
        ordering = ['-data_saida']
    
    def __str__(self):
        return f"{self.viatura.prefixo} - {self.data_saida:%d/%m/%Y}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update viatura
        if self.status == 'ATIVO':
            self.viatura.status = 'EM_USO'
        else:
            self.viatura.status = 'DISPONIVEL'
            if self.km_retorno and self.km_retorno > self.viatura.odometro:
                self.viatura.odometro = self.km_retorno
        self.viatura.save()