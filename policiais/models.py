from django.db import models
from django.utils.translation import gettext_lazy as _

class Policial(models.Model):
    POSTO_CHOICES = [
        ('SD_PM', 'Sd PM'),
        ('CB_PM', 'Cb PM'),
        ('3SGT_PM', '3º Sgt PM'),
        ('2SGT_PM', '2º Sgt PM'),
        ('1SGT_PM', '1º Sgt PM'),
        ('SUBTEN_PM', 'Subten PM'),
        ('STEN_PM', 'Sten PM'),
        ('2TEN_PM', '2º Ten PM'),
        ('1TEN_PM', '1º Ten PM'),
        ('CAP_PM', 'Cap PM'),
        ('MAJ_PM', 'Maj PM'),
        ('TENCEL_PM', 'Ten Cel PM'),
        ('CEL_PM', 'Cel PM'),
    ]
    
    SITUACAO_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
        ('AFASTADO', 'Afastado'),
        ('TRANSFERIDO', 'Transferido'),
    ]
    
    re = models.CharField(_('RE'), max_length=10, unique=True)
    nome = models.CharField(_('Nome'), max_length=100)
    posto = models.CharField(_('Posto'), max_length=20, choices=POSTO_CHOICES)
    situacao = models.CharField(_('Situação'), max_length=20, choices=SITUACAO_CHOICES, default='ATIVO')
    data_cadastro = models.DateTimeField(_('Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Atualização'), auto_now=True)
    observacoes = models.TextField(_('Obs'), blank=True, null=True)
    foto = models.ImageField(_('Foto'), upload_to='policiais/', blank=True, null=True)
    
    class Meta:
        verbose_name = _('Policial')
        verbose_name_plural = _('Policiais')
        ordering = ['posto', 'nome']
    
    def __str__(self):
        return f"{self.posto} {self.re} {self.nome}"
