from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User


class ContaContabil(models.Model):
    codigo = models.CharField(_('Código da Conta Contábil'), max_length=20, unique=True)
    nome = models.CharField(_('Nome / Descrição da Conta'), max_length=150)
    descricao = models.TextField(_('Descrição Detalhada'), blank=True, null=True)

    class Meta:
        verbose_name = _('Conta Contábil')
        verbose_name_plural = _('Contas Contábeis')
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class CicloInventario(models.Model):
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('EM_PREPARACAO', 'Em preparação'),
        ('EM_ANDAMENTO', 'Em Andamento / Conferência'),
        ('EM_ANALISE', 'Em análise de divergências'),
        ('AGUARDANDO_APROVACAO', 'Aguardando aprovação'),
        ('CONCLUIDO', 'Concluído'),
        ('HOMOLOGADO', 'Homologado'),
        ('ARQUIVADO', 'Arquivado'),
    ]

    SEMESTRE_CHOICES = [
        (1, '1º Semestre'),
        (2, '2º Semestre'),
    ]

    titulo = models.CharField(_('Título do Inventário'), max_length=200)
    termo_numero = models.CharField(_('Número do Termo'), max_length=100, help_text=_('Ex: 2BAEP - 001/40/2026'))
    ano = models.PositiveIntegerField(_('Ano de Exercício'), default=timezone.now().year)
    semestre = models.PositiveSmallIntegerField(_('Semestre'), choices=SEMESTRE_CHOICES, default=1)
    data_referencia = models.DateField(_('Data do Inventário'), default=timezone.now)
    detentor_executivo = models.CharField(_('Detentor Executivo (Responsável)'), max_length=150, blank=True, null=True)
    opm_codigos = models.CharField(_('Códigos OPM'), max_length=150, blank=True, null=True, default='606020000, 606028000, 606028400')
    status = models.CharField(_('Status'), max_length=24, choices=STATUS_CHOICES, default='EM_ANDAMENTO')
    observacoes = models.TextField(_('Observações / Notas do Inventário'), blank=True, null=True)
    arquivo_origem = models.FileField(_('Planilha de Origem (.xlsx)'), upload_to='inventarios/planilhas/', blank=True, null=True)
    
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventarios_criados')
    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Última atualização'), auto_now=True)

    class Meta:
        verbose_name = _('Ciclo de Inventário Semestral')
        verbose_name_plural = _('Ciclos de Inventário Semestral')
        ordering = ['-ano', '-semestre', '-criado_em']

    def __str__(self):
        return f"{self.titulo} ({self.termo_numero})"

    TRANSICOES_PERMITIDAS = {
        'RASCUNHO': {'EM_PREPARACAO'},
        'EM_PREPARACAO': {'RASCUNHO', 'EM_ANDAMENTO'},
        'EM_ANDAMENTO': {'EM_PREPARACAO', 'EM_ANALISE'},
        'EM_ANALISE': {'EM_ANDAMENTO', 'AGUARDANDO_APROVACAO'},
        'AGUARDANDO_APROVACAO': {'EM_ANALISE', 'CONCLUIDO'},
        'CONCLUIDO': {'AGUARDANDO_APROVACAO', 'HOMOLOGADO'},
        'HOMOLOGADO': {'ARQUIVADO'},
        'ARQUIVADO': set(),
    }

    @property
    def bloqueado_para_edicao(self):
        return self.status in {'HOMOLOGADO', 'ARQUIVADO'}

    def pode_transicionar_para(self, novo_status):
        return novo_status in self.TRANSICOES_PERMITIDAS.get(self.status, set())

    def transicionar_para(self, novo_status, usuario, justificativa=''):
        if not self.pode_transicionar_para(novo_status):
            raise ValueError(f'Transição inválida: {self.status} para {novo_status}.')

        HistoricoCicloInventario.objects.create(
            ciclo=self,
            status_anterior=self.status,
            status_novo=novo_status,
            justificativa=justificativa,
            realizado_por=usuario,
        )
        self.status = novo_status
        self.save(update_fields=['status', 'atualizado_em'])

    @property
    def total_itens(self):
        return self.itens.count()

    @property
    def total_valor(self):
        return self.itens.aggregate(total=models.Sum('valor'))['total'] or 0.0

    @property
    def total_conferidos(self):
        return self.itens.filter(conferido=True).count()

    @property
    def progresso_conferencia(self):
        tot = self.total_itens
        if tot == 0:
            return 0
        return round((self.total_conferidos / tot) * 100, 1)

    @property
    def total_em_exclusao(self):
        return self.itens.filter(situacao_material__icontains='EXCLUSÃO').count()


class ItemInventario(models.Model):
    SITUACAO_FISICA_CHOICES = [
        ('CONFORME', 'Conforme / Em Uso'),
        ('AVARIADO', 'Avariado / Danificado'),
        ('NAO_LOCALIZADO', 'Não Localizado / Divergente'),
        ('EM_EXCLUSAO', 'Processo de Exclusão'),
    ]

    ciclo = models.ForeignKey(
        CicloInventario,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name=_('Ciclo de Inventário')
    )
    conta_contabil = models.ForeignKey(
        ContaContabil,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens',
        verbose_name=_('Conta Contábil')
    )
    secao_subunidade = models.CharField(_('Seção / Subunidade'), max_length=150, help_text=_('Ex: 606028400 - P/4'))
    patrimonio = models.CharField(_('Patrimônio / Tombo'), max_length=100, db_index=True)
    numero_serie = models.CharField(_('Número de Série'), max_length=100, blank=True, null=True)
    tipo_material = models.CharField(_('Tipo de Material / Descrição'), max_length=200)
    situacao_material = models.CharField(_('Situação do Material'), max_length=150, default='EM USO')
    valor = models.DecimalField(_('Valor Contábil (R$)'), max_digits=12, decimal_places=2, default=0.00)
    
    # Controle de conferência física
    conferido = models.BooleanField(_('Conferido Fisiocamente'), default=False)
    situacao_fisica_conferida = models.CharField(
        _('Situação Física Conferida'),
        max_length=20,
        choices=SITUACAO_FISICA_CHOICES,
        default='CONFORME'
    )
    data_conferencia = models.DateTimeField(_('Data da Conferência'), blank=True, null=True)
    conferido_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_inventario_conferidos',
        verbose_name=_('Conferido Por')
    )
    observacoes_conferencia = models.TextField(_('Observações da Conferência'), blank=True, null=True)

    class Meta:
        verbose_name = _('Item do Inventário')
        verbose_name_plural = _('Itens do Inventário')
        ordering = ['conta_contabil__codigo', 'secao_subunidade', 'patrimonio']

    def __str__(self):
        return f"{self.patrimonio} - {self.tipo_material} ({self.secao_subunidade})"


class MembroComissaoInventario(models.Model):
    PAPEL_CHOICES = [
        ('PRESIDENTE', 'Presidente da comissão'),
        ('MEMBRO', 'Membro da comissão'),
        ('CONFERENTE', 'Conferente'),
        ('SUPERVISOR', 'Supervisor de seção'),
        ('HOMOLOGADOR', 'Homologador'),
    ]

    ciclo = models.ForeignKey(CicloInventario, on_delete=models.CASCADE, related_name='comissao')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='designacoes_inventario')
    papel = models.CharField(max_length=20, choices=PAPEL_CHOICES)
    secao_subunidade = models.CharField(max_length=150, blank=True)
    ativo = models.BooleanField(default=True)
    designado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Membro da Comissão de Inventário')
        verbose_name_plural = _('Membros da Comissão de Inventário')
        constraints = [
            models.UniqueConstraint(fields=['ciclo', 'usuario', 'papel'], name='inventario_membro_papel_unico'),
        ]

    def __str__(self):
        return f'{self.usuario} — {self.get_papel_display()} ({self.ciclo})'


class ConferenciaInventario(models.Model):
    RESULTADO_CHOICES = [
        ('CONFIRMADO', 'Confirmado conforme base'),
        ('COM_RESSALVA', 'Confirmado com ressalva'),
        ('NAO_LOCALIZADO', 'Não localizado'),
        ('OUTRA_SECAO', 'Localizado em outra seção'),
        ('EXCEDENTE', 'Bem excedente'),
        ('AVARIADO', 'Avariado / inservível'),
        ('EM_BAIXA', 'Em processo de baixa'),
        ('SERIE_DIVERGENTE', 'Número de série divergente'),
    ]

    item = models.ForeignKey(ItemInventario, on_delete=models.CASCADE, related_name='conferencias')
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES)
    situacao_fisica = models.CharField(max_length=20, choices=ItemInventario.SITUACAO_FISICA_CHOICES, default='CONFORME')
    localizacao_encontrada = models.CharField(max_length=200, blank=True)
    numero_serie_encontrado = models.CharField(max_length=100, blank=True)
    observacoes = models.TextField(blank=True)
    evidencia = models.FileField(upload_to='inventarios/evidencias/%Y/%m/', blank=True, null=True)
    conferido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='conferencias_inventario')
    conferido_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _('Conferência de Inventário')
        verbose_name_plural = _('Conferências de Inventário')
        ordering = ['-conferido_em']


class DivergenciaInventario(models.Model):
    TIPO_CHOICES = [
        ('NAO_LOCALIZADO', 'Falta física'),
        ('EXCEDENTE', 'Sobra física'),
        ('OUTRA_SECAO', 'Localização divergente'),
        ('SERIE_DIVERGENTE', 'Número de série divergente'),
        ('AVARIADO', 'Bem avariado'),
        ('EM_BAIXA', 'Bem em processo de baixa'),
        ('CONTA_DIVERGENTE', 'Conta contábil divergente'),
        ('DUPLICIDADE', 'Duplicidade de patrimônio'),
    ]
    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'),
        ('EM_APURACAO', 'Em apuração'),
        ('AGUARDANDO_DOCUMENTO', 'Aguardando documento'),
        ('REGULARIZADA', 'Regularizada'),
        ('CONFIRMADA_PARA_BAIXA', 'Confirmada para baixa'),
        ('IMPROCEDENTE', 'Improcedente'),
    ]

    item = models.ForeignKey(ItemInventario, on_delete=models.CASCADE, related_name='divergencias')
    conferencia_origem = models.ForeignKey(ConferenciaInventario, on_delete=models.SET_NULL, null=True, blank=True, related_name='divergencias')
    tipo = models.CharField(max_length=24, choices=TIPO_CHOICES)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default='ABERTA')
    descricao = models.TextField()
    providencia = models.TextField(blank=True)
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='divergencias_inventario_responsavel')
    prazo = models.DateField(null=True, blank=True)
    resolucao = models.TextField(blank=True)
    resolvido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='divergencias_inventario_resolvidas')
    resolvido_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Divergência de Inventário')
        verbose_name_plural = _('Divergências de Inventário')
        ordering = ['status', '-criado_em']


class HistoricoCicloInventario(models.Model):
    ciclo = models.ForeignKey(CicloInventario, on_delete=models.CASCADE, related_name='historico')
    status_anterior = models.CharField(max_length=24, blank=True)
    status_novo = models.CharField(max_length=24)
    justificativa = models.TextField(blank=True)
    realizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='historicos_ciclo_inventario')
    realizado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Histórico do Ciclo de Inventário')
        verbose_name_plural = _('Históricos do Ciclo de Inventário')
        ordering = ['-realizado_em']
