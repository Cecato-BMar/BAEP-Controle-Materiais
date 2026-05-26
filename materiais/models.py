from django.db import models
from django.utils.translation import gettext_lazy as _
from django.apps import apps

class Material(models.Model):
    ESTADO_CHOICES = [
        ('NOVO', 'Novo'),
        ('BOM', 'Bom'),
        ('REGULAR', 'Regular'),
        ('RUIM', 'Ruim'),
        ('PESSIMO', 'Péssimo'),
    ]
    
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível'),
        ('EM_USO', 'Em Uso'),
        ('MANUTENCAO', 'Manutenção'),
        ('APREENDIDO', 'Apreendido'),
        ('BAIXADO', 'Baixado'),
    ]
    
    TIPO_CHOICES = [
        ('ARMA', 'Arma'),
        ('MUNICAO', 'Munição'),
        ('COLETE', 'Colete'),
        ('RADIO', 'Rádio'),
        ('ALGEMA', 'Algema'),
        ('OUTROS', 'Outros'),
    ]
    
    CATEGORIA_CHOICES = [
        ('PISTOLA', 'Pistola'),
        ('FUZIL', 'Fuzil'),
        ('CAL_12', 'Calibre 12'),
        ('SUBMETRALHADORA', 'Submetralhadora'),
        ('LANCADOR', 'Lançador'),
        ('CHOQUE', 'Menos que Letal / Choque'),
        ('OUTROS', 'Outros'),
    ]
    
    tipo = models.CharField(_('Tipo'), max_length=20, choices=TIPO_CHOICES)
    categoria = models.CharField(_('Categoria'), max_length=30, choices=CATEGORIA_CHOICES, default='OUTROS', blank=True, null=True)
    nome = models.CharField(_('Nome'), max_length=100)
    numero = models.CharField(_('Número'), max_length=50, unique=True)
    quantidade = models.PositiveIntegerField(_('Quantidade Total'))
    quantidade_disponivel = models.PositiveIntegerField(_('Quantidade Disponível'))
    quantidade_em_uso = models.PositiveIntegerField(_('Quantidade em Uso'), default=0)
    estado = models.CharField(_('Estado'), max_length=20, choices=ESTADO_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)
    imagem = models.ImageField(_('Imagem'), upload_to='materiais/', blank=True, null=True)
    localizacao_fisica = models.ForeignKey('estoque.LocalizacaoFisica', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Localização Física'))
    
    class Meta:
        verbose_name = _('Material')
        verbose_name_plural = _('Materiais')
        ordering = ['tipo', 'nome']
    
    def __str__(self):
        return f"{self.nome} ({self.numero})"
    
    @property
    def identificacao(self):
        """Retorna a identificação completa do material (nome + número)"""
        return f"{self.nome} ({self.numero})"
    
    def save(self, *args, **kwargs):
        # Se for um novo registro, inicializa quantidade disponível
        if not self.pk:
            self.quantidade_disponivel = self.quantidade
        super().save(*args, **kwargs)

class LoteMunicao(models.Model):
    TIPO_MUNICAO_CHOICES = [
        ('REAL', 'Real'),
        ('TREINAMENTO', 'Treinamento'),
        ('FESTIM', 'Festim'),
        ('ELASTOMERO', 'Elastômero'),
    ]

    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='lotes_municao', verbose_name=_('Material (Munição)'))
    calibre = models.CharField(_('Calibre'), max_length=50)
    marca = models.CharField(_('Marca/Fabricante'), max_length=50)
    numero_lote = models.CharField(_('Número do Lote'), max_length=100)
    tipo_municao = models.CharField(_('Tipo de Munição'), max_length=20, choices=TIPO_MUNICAO_CHOICES, default='REAL')
    data_fabricacao = models.DateField(_('Data de Fabricação'), blank=True, null=True)
    data_validade = models.DateField(_('Data de Validade'), blank=True, null=True)
    quantidade_inicial = models.PositiveIntegerField(_('Quantidade Inicial'))
    quantidade_atual = models.PositiveIntegerField(_('Quantidade Atual'))
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)

    class Meta:
        verbose_name = _('Lote de Munição')
        verbose_name_plural = _('Lotes de Munição')
        ordering = ['data_validade', 'numero_lote']
        unique_together = ['material', 'numero_lote']

    def __str__(self):
        return f"Lote: {self.numero_lote} | Calibre: {self.calibre} | Qtde: {self.quantidade_atual}"

    def save(self, *args, **kwargs):
        if not self.pk and self.quantidade_atual is None:
            self.quantidade_atual = self.quantidade_inicial
        super().save(*args, **kwargs)

    @property
    def vencido(self):
        from django.utils import timezone
        if self.data_validade:
            return self.data_validade < timezone.now().date()
        return False

