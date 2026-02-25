from django.db import models
from django.utils.translation import gettext_lazy as _

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
    
    tipo = models.CharField(_('Tipo'), max_length=20, choices=TIPO_CHOICES)
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
