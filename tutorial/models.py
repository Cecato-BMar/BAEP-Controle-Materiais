from django.db import models


class ModuloTutorial(models.Model):
    """Módulo do tutorial (um por área do sistema)."""

    icone = models.CharField(
        'Ícone (FontAwesome)', max_length=80, default='fa-solid fa-book-open',
        help_text='Classe FontAwesome, ex: "fa-solid fa-boxes"')
    nome = models.CharField('Nome do Módulo', max_length=120)
    slug = models.SlugField('Slug', max_length=140, unique=True)
    descricao = models.TextField('Descrição', blank=True)
    grupo = models.CharField(
        'Grupo de Acesso (permissão)', max_length=50, blank=True,
        help_text='Grupo do sistema que abre este módulo (ex: reserva_armas). '
                  'Vazio = aberto a todos os usuários logados.')
    ordem = models.PositiveIntegerField('Ordem', default=0)
    publicado = models.BooleanField('Publicado', default=True)

    class Meta:
        verbose_name = 'Módulo do Tutorial'
        verbose_name_plural = 'Módulos do Tutorial'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome

    @property
    def total_secoes(self):
        return self.secoes.filter(publicado=True).count()


class SecaoTutorial(models.Model):
    """Seção/lição dentro de um módulo do tutorial."""

    TIPO_CHOICES = [
        ('TEXTO', 'Texto'),
        ('PASSO', 'Passo a Passo'),
        ('DICA', 'Dica'),
        ('ALERTA', 'Alerta / Regra'),
        ('TABELA', 'Tabela'),
    ]

    modulo = models.ForeignKey(
        ModuloTutorial, on_delete=models.CASCADE, related_name='secoes')
    titulo = models.CharField('Título', max_length=160)
    conteudo = models.TextField('Conteúdo', help_text='HTML (tags básicas, '
                                'classes Bootstrap permitidas).')
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES,
                            default='TEXTO')
    ordem = models.PositiveIntegerField('Ordem', default=0)
    publicado = models.BooleanField('Publicado', default=True)

    class Meta:
        verbose_name = 'Seção do Tutorial'
        verbose_name_plural = 'Seções do Tutorial'
        ordering = ['modulo', 'ordem']
        unique_together = ['modulo', 'titulo']

    def __str__(self):
        return f"{self.modulo.nome} — {self.titulo}"