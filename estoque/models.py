from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
from decimal import Decimal
from io import BytesIO


# =============================================================================
# TABELAS DE PADRONIZAÇÃO (MATERIAL DE CONSUMO §1)
# =============================================================================

class Cor(models.Model):
    """Tabela de cores parametrizável (MATERIAL DE CONSUMO §1 - Cor)"""
    nome = models.CharField(_('Nome'), max_length=50, unique=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Cor')
        verbose_name_plural = _('Cores')
        ordering = ['nome']

    def __str__(self):
        return self.nome


class UnidadeFornecimento(models.Model):
    """Unidade de fornecimento (MATERIAL DE CONSUMO §1 — separada de UnidadeMedida para evitar confusão).
    Valor padrão: UNIDADE. Cadastro restrito a administradores."""
    nome = models.CharField(_('Nome'), max_length=100, unique=True)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    padrao = models.BooleanField(_('Padrão (Unidade)'), default=False,
                                  help_text=_('Marca esta unidade de fornecimento como padrão do sistema'))
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Unidade de Fornecimento')
        verbose_name_plural = _('Unidades de Fornecimento')
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @classmethod
    def get_padrao(cls):
        """Retorna a unidade de fornecimento padrão (UNIDADE)"""
        obj = cls.objects.filter(padrao=True, ativo=True).first()
        if not obj:
            obj = cls.objects.filter(ativo=True).first()
        return obj


class ContaPatrimonial(models.Model):
    """Conta patrimonial (MATERIAL DE CONSUMO §1)"""
    codigo = models.CharField(_('Código'), max_length=30, unique=True)
    descricao = models.CharField(_('Descrição'), max_length=200)
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Conta Patrimonial')
        verbose_name_plural = _('Contas Patrimoniais')
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} — {self.descricao}"


class OrgaoRequisitante(models.Model):
    """Órgão requisitante (MATERIAL DE CONSUMO §1)"""
    nome = models.CharField(_('Nome'), max_length=100, unique=True)
    sigla = models.CharField(_('Sigla'), max_length=20, blank=True, null=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Órgão Requisitante')
        verbose_name_plural = _('Órgãos Requisitantes')
        ordering = ['nome']

    def __str__(self):
        if self.sigla:
            return f"{self.sigla} — {self.nome}"
        return self.nome


class LocalizacaoFisica(models.Model):
    """Localização física no almoxarifado (MATERIAL DE CONSUMO §1)"""
    nome = models.CharField(_('Nome'), max_length=100, unique=True)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Localização Física')
        verbose_name_plural = _('Localizações Físicas')
        ordering = ['nome']

    def __str__(self):
        return self.nome


class MilitarRequisitante(models.Model):
    """Militar requisitante (MATERIAL DE CONSUMO §1 — RE + QRA com busca automática)"""
    re = models.CharField(_('RE'), max_length=20, unique=True)
    qra = models.CharField(_('QRA (Nome de Guerra)'), max_length=100)
    nome_completo = models.CharField(_('Nome Completo'), max_length=200, blank=True, null=True)
    orgao = models.ForeignKey(OrgaoRequisitante, on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name=_('Órgão'), related_name='militares')
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Militar Requisitante')
        verbose_name_plural = _('Militares Requisitantes')
        ordering = ['re']

    def __str__(self):
        return f"{self.re} — {self.qra}"


# =============================================================================
# CADASTROS EXISTENTES MANTIDOS / EXPANDIDOS
# =============================================================================

class Categoria(models.Model):
    """Categorias macro de materiais (ex: Papelaria, Limpeza, Informática)"""
    nome = models.CharField(_('Nome'), max_length=100, unique=True)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    codigo = models.CharField(_('Código'), max_length=20, unique=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)

    class Meta:
        verbose_name = _('Categoria')
        verbose_name_plural = _('Categorias')
        ordering = ['codigo', 'nome']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Subcategoria(models.Model):
    """Subcategorias vinculadas a uma Categoria (ex: Categoria: Papelaria -> Subcategoria: Canetas)"""
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='subcategorias', verbose_name=_('Categoria'))
    nome = models.CharField(_('Nome'), max_length=100)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    codigo = models.CharField(_('Código'), max_length=20, unique=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)

    class Meta:
        verbose_name = _('Subcategoria')
        verbose_name_plural = _('Subcategorias')
        ordering = ['nome']

    def __str__(self):
        return f"{self.categoria.nome} > {self.nome}"


class UnidadeMedida(models.Model):
    """Unidade de medida do item (MATERIAL DE CONSUMO §1 — ex: ml, kg, pacote 100g).
    Distinta de UnidadeFornecimento."""
    sigla = models.CharField(_('Sigla'), max_length=20, unique=True)
    nome = models.CharField(_('Nome'), max_length=100)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    ativo = models.BooleanField(_('Ativo'), default=True)

    class Meta:
        verbose_name = _('Unidade de Medida')
        verbose_name_plural = _('Unidades de Medida')
        ordering = ['sigla']

    def __str__(self):
        return f"{self.sigla} - {self.nome}"


class Fornecedor(models.Model):
    """Cadastro de fornecedores"""
    TIPO_PESSOA_CHOICES = [
        ('FISICA', 'Pessoa Física'),
        ('JURIDICA', 'Pessoa Jurídica'),
    ]

    nome = models.CharField(_('Nome/Razão Social'), max_length=200)
    tipo_pessoa = models.CharField(_('Tipo Pessoa'), max_length=10, choices=TIPO_PESSOA_CHOICES)
    documento = models.CharField(_('CPF/CNPJ'), max_length=20, unique=True)
    inscricao_estadual = models.CharField(_('Inscrição Estadual'), max_length=20, blank=True, null=True)
    telefone = models.CharField(_('Telefone'), max_length=20, blank=True, null=True)
    email = models.EmailField(_('E-mail'), blank=True, null=True)
    endereco = models.CharField(_('Endereço'), max_length=300, blank=True, null=True)
    cidade = models.CharField(_('Cidade'), max_length=100, blank=True, null=True)
    estado = models.CharField(_('Estado'), max_length=2, blank=True, null=True)
    cep = models.CharField(_('CEP'), max_length=10, blank=True, null=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)

    class Meta:
        verbose_name = _('Fornecedor')
        verbose_name_plural = _('Fornecedores')
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.documento})"


# =============================================================================
# MATERIAL DE CONSUMO (refatoração de Produto conforme MATERIAL DE CONSUMO §1)
# =============================================================================

class Produto(models.Model):
    """Material de Consumo — model central do estoque.
    Expandido with campos obrigatórios do MATERIAL DE CONSUMO §1 (Cadastro de Materiais de Consumo)."""

    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
        ('OBSOLETO', 'Obsoleto'),
        ('EM_DESENVOLVIMENTO', 'Em Desenvolvimento'),
    ]

    # --- Identificação (MATERIAL DE CONSUMO §1) ---
    codigo = models.CharField(_('Código Único'), max_length=50, unique=True,
                               help_text=_('Código único do material. Ex: MAT-001'))
    codigo_barras = models.CharField(_('Código de Barras'), max_length=100,
                                      blank=True, null=True, unique=True,
                                      help_text=_('Preparado para futura leitura por scanner'))
    nome = models.CharField(_('Nome do Material'), max_length=200,
                             help_text=_('Ex: Caneta Azul, Papel Sulfite A4'))
    descricao = models.TextField(_('Descrição'), blank=True, null=True,
                                  help_text=_('Conforme Termo de Referência'))

    # --- Classificação MATERIAL DE CONSUMO §1 ---
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='produtos',
                                   verbose_name=_('Categoria'))
    subcategoria = models.ForeignKey(Subcategoria, on_delete=models.PROTECT, related_name='produtos',
                                      verbose_name=_('Subcategoria'), null=True, blank=True)
    codigo_siafisico = models.CharField(_('Código SIAFÍSICO'), max_length=50, blank=True, null=True,
                                         help_text=_('Conforme Termo de Referência'))
    codigo_cat_mat = models.CharField(_('Código CAT MAT'), max_length=50, blank=True, null=True,
                                       help_text=_('Conforme Termo de Referência'))
    
    # --- Aquisição / Licitação MATERIAL DE CONSUMO §1 ---
    empenho = models.CharField(_('Nº de Empenho'), max_length=100, blank=True, null=True)
    preco_medio = models.DecimalField(_('Preço Médio'), max_digits=12, decimal_places=4,
                                       default=Decimal('0.00'),
                                       validators=[MinValueValidator(Decimal('0.00'))],
                                       help_text=_('Preço médio de aquisição'))
    data_cotacao = models.DateField(_('Data da Cotação'), null=True, blank=True,
                                     help_text=_('Alerta automático após 180 dias'))
    data_inicio_projeto = models.DateField(_('Data de Início do Projeto de Aquisição'),
                                            null=True, blank=True)
    tempo_reposicao = models.PositiveIntegerField(_('Tempo de Reposição (dias)'), default=0,
                                                   help_text=_('Em dias. Calculado ou informado manualmente.'))
    termo_referencia = models.CharField(_('Termo de Referência nº'), max_length=100,
                                         blank=True, null=True)
    processo_sei = models.CharField(_('Processo SEI nº'), max_length=100, blank=True, null=True)
    historico_subcategoria = models.TextField(_('Histórico / Observações da Subcategoria'),
                                               blank=True, null=True,
                                               help_text=_('Registrar atualizações da subcategoria'))

    # --- Unidades MATERIAL DE CONSUMO §1 ---
    unidade_medida = models.ForeignKey(UnidadeMedida, on_delete=models.PROTECT,
                                        verbose_name=_('Unidade de Medida do Item'),
                                        null=True, blank=True)
    unidade_fornecimento = models.ForeignKey(UnidadeFornecimento, on_delete=models.SET_NULL,
                                              null=True, blank=True,
                                              verbose_name=_('Unidade de Fornecimento Padrão'))

    # --- Controle de Estoque ---
    estoque_minimo = models.DecimalField(_('Estoque Mínimo'), max_digits=10, decimal_places=2,
                                         default=Decimal('0.00'),
                                         validators=[MinValueValidator(Decimal('0.00'))])
    estoque_maximo = models.DecimalField(_('Estoque Máximo'), max_digits=10, decimal_places=2,
                                         default=Decimal('0.00'),
                                         validators=[MinValueValidator(Decimal('0.00'))])
    # ATENÇÃO: estoque_atual é campo legado. Use saldo_calculado para lógica de negócio.
    estoque_atual = models.DecimalField(_('Estoque Atual (cache)'), max_digits=10, decimal_places=2,
                                         default=0,
                                         help_text=_('Cache — use saldo_calculado para operações'))
    estoque_reservado = models.DecimalField(_('Estoque Reservado'), max_digits=10, decimal_places=2,
                                             default=0)

    # --- Valores ---
    valor_unitario = models.DecimalField(_('Valor Unitário'), max_digits=12, decimal_places=4,
                                          default=0)
    valor_total = models.DecimalField(_('Valor Total'), max_digits=14, decimal_places=2,
                                       default=0, editable=False)

    # --- Controle por Validade / Série ---
    controla_validade = models.BooleanField(_('Controla Validade'), default=False)
    prazo_validade_meses = models.PositiveIntegerField(_('Prazo Validade (meses)'), null=True, blank=True)
    controla_numero_serie = models.BooleanField(_('Controla Número de Série'), default=False)
    disponivel_solicitacao = models.BooleanField(_('Disponível para Solicitação'), default=True)

    # --- Vínculos MATERIAL DE CONSUMO ---
    fornecedor_padrao = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='produtos_fornecidos',
                                           verbose_name=_('Fornecedor Padrão'))
    localizacao_fisica = models.ForeignKey(LocalizacaoFisica, on_delete=models.SET_NULL,
                                            null=True, blank=True,
                                            verbose_name=_('Localização Física'))
    conta_patrimonial = models.ForeignKey(ContaPatrimonial, on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           verbose_name=_('Conta Patrimonial'))

    # --- Status ---
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='ATIVO')

    # --- Imagem / QR Code ---
    imagem = models.ImageField(_('Imagem'), upload_to='produtos/', blank=True, null=True)
    qr_code_token = models.UUIDField(_('Token QR Code'), default=uuid.uuid4, unique=True, editable=False)
    qr_code_imagem = models.ImageField(_('QR Code'), upload_to='produtos/qrcodes/',
                                        blank=True, null=True, editable=False)

    # --- Auditoria ---
    criado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='produtos_criados',
                                    verbose_name=_('Criado por'))
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)
    atualizado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                        related_name='produtos_atualizados',
                                        verbose_name=_('Atualizado por'), null=True, blank=True)

    class Meta:
        verbose_name = _('Material de Consumo')
        verbose_name_plural = _('Materiais de Consumo')
        ordering = ['codigo', 'nome']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['nome']),
            models.Index(fields=['categoria']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    def save(self, *args, **kwargs):
        self.valor_total = self.estoque_atual * Decimal(str(self.valor_unitario or 0))
        if hasattr(self, '_current_user'):
            self.atualizado_por = self._current_user
        super().save(*args, **kwargs)
        if not self.qr_code_imagem:
            try:
                import qrcode
                payload = str(self.qr_code_token)
                qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M,
                                   box_size=10, border=4)
                qr.add_data(payload)
                qr.make(fit=True)
                img = qr.make_image(fill_color='black', back_color='white')
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                filename = f"qr_{self.codigo}.png"
                self.qr_code_imagem.save(filename, ContentFile(buffer.getvalue()), save=False)
                super().save(update_fields=['qr_code_imagem'])
            except Exception:
                pass

    # --- Properties de Negócio (MATERIAL DE CONSUMO §4) ---

    @property
    def saldo_calculado(self):
        """Saldo real: SOMA(entradas) - SOMA(saídas). MATERIAL DE CONSUMO §4.3"""
        from django.db.models import Sum, Q
        TIPOS_ENTRADA = ['COMPRA_NOVA', 'DEVOLUCAO_ENTRADA']
        TIPOS_SAIDA = ['REQUISICAO', 'DESCARTE']
        movs = self.movimentacoes_estoque.all()
        entradas = movs.filter(subtipo__in=TIPOS_ENTRADA).aggregate(
            total=Sum('quantidade'))['total'] or Decimal('0.00')
        saidas = movs.filter(subtipo__in=TIPOS_SAIDA).aggregate(
            total=Sum('quantidade'))['total'] or Decimal('0.00')
        # Incluir ajustes
        ajustes_acrescimo = self.ajustes.filter(tipo_ajuste='ACRESCIMO').aggregate(
            total=Sum('quantidade'))['total'] or Decimal('0.00')
        ajustes_debito = self.ajustes.filter(tipo_ajuste='DEBITO').aggregate(
            total=Sum('quantidade'))['total'] or Decimal('0.00')
        return entradas - saidas + ajustes_acrescimo - ajustes_debito

    @property
    def estoque_disponivel(self):
        return self.saldo_calculado - self.estoque_reservado

    @property
    def precisa_reposicao(self):
        return self.estoque_disponivel <= self.estoque_minimo

    @property
    def estoque_critico(self):
        return self.estoque_disponivel <= (self.estoque_minimo * Decimal('0.5'))

    @property
    def cotacao_vencida(self):
        """Alerta se cotação tem mais de 180 dias. MATERIAL DE CONSUMO §4.8"""
        if self.data_cotacao:
            return (timezone.now().date() - self.data_cotacao).days > 180
        return False

    @property
    def tempo_reposicao_calculado(self):
        """MATERIAL DE CONSUMO §4.8: Data Entrada - Data Início Projeto"""
        if self.data_inicio_projeto:
            # Busca a primeira entrada
            primeira_entrada = self.movimentacoes_estoque.filter(
                subtipo='COMPRA_NOVA').order_by('data_movimentacao').first()
            if primeira_entrada:
                delta = primeira_entrada.data_movimentacao - self.data_inicio_projeto
                return delta.days
        return self.tempo_reposicao

    def consumo_medio(self, data_inicio=None, data_fim=None):
        """MATERIAL DE CONSUMO §4.5: consumo médio no período (saídas / dias)"""
        from django.db.models import Sum
        qs = self.movimentacoes_estoque.filter(subtipo__in=['REQUISICAO', 'DESCARTE'])
        if data_inicio:
            qs = qs.filter(data_movimentacao__gte=data_inicio)
        if data_fim:
            qs = qs.filter(data_movimentacao__lte=data_fim)
        total_saidas = qs.aggregate(total=Sum('quantidade'))['total'] or Decimal('0.00')
        if data_inicio and data_fim:
            dias = (data_fim - data_inicio).days or 1
        else:
            # Calcula sobre todo o histórico
            primeira = qs.order_by('data_movimentacao').values_list(
                'data_movimentacao', flat=True).first()
            if primeira:
                dias = (timezone.now().date() - (primeira.date() if hasattr(primeira, 'date') else primeira)).days or 1
            else:
                return Decimal('0.00')
        return total_saidas / Decimal(str(dias))

    def autonomia(self, data_inicio=None, data_fim=None):
        """MATERIAL DE CONSUMO §4.6: quantidade / consumo médio"""
        cm = self.consumo_medio(data_inicio, data_fim)
        if cm == 0:
            return None  # Infinito / sem consumo
        return self.saldo_calculado / cm


# =============================================================================
# LOTES (PEPS — MATERIAL DE CONSUMO §1.3)
# =============================================================================

class Lote(models.Model):
    """Controle de lotes para rastreabilidade PEPS"""
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='lotes',
                                 verbose_name=_('Produto'))
    numero_lote = models.CharField(_('Número do Lote'), max_length=50)
    data_fabricacao = models.DateField(_('Data de Fabricação'), null=True, blank=True)
    data_validade = models.DateField(_('Data de Validade'), null=True, blank=True)
    quantidade_inicial = models.DecimalField(_('Quantidade Inicial'), max_digits=10, decimal_places=2)
    quantidade_atual = models.DecimalField(_('Quantidade Atual'), max_digits=10, decimal_places=2)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, verbose_name=_('Fornecedor'))
    nota_fiscal = models.CharField(_('Nota Fiscal'), max_length=50, blank=True, null=True)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Lote')
        verbose_name_plural = _('Lotes')
        ordering = ['data_cadastro']  # PEPS: mais antigo primeiro
        unique_together = ['produto', 'numero_lote']

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.produto.nome}"

    @property
    def vencido(self):
        if self.data_validade:
            return self.data_validade < timezone.now().date()
        return False

    @property
    def proximo_vencimento(self):
        if self.data_validade:
            dias = (self.data_validade - timezone.now().date()).days
            return 0 <= dias <= 30
        return False


class NumeroSerie(models.Model):
    """Controle de números de série para equipamentos"""
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='numeros_serie',
                                 verbose_name=_('Produto'))
    numero_serie = models.CharField(_('Número de Série'), max_length=100, unique=True)
    patrimonio = models.CharField(_('Patrimônio'), max_length=50, blank=True, null=True)
    status = models.CharField(_('Status'), max_length=20, choices=Produto.STATUS_CHOICES, default='ATIVO')
    localizacao = models.CharField(_('Localização'), max_length=100, blank=True, null=True)
    responsavel = models.ForeignKey('policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='equipamentos_responsaveis',
                                     verbose_name=_('Responsável'))
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Número de Série')
        verbose_name_plural = _('Números de Série')
        ordering = ['produto', 'numero_serie']

    def __str__(self):
        return f"{self.numero_serie} - {self.produto.nome}"


# =============================================================================
# MOVIMENTAÇÃO DE ESTOQUE (MATERIAL DE CONSUMO §2 Entrada / §3 Saída)
# =============================================================================

class MovimentacaoEstoque(models.Model):
    """Registro de movimentações. Saldo é sempre DERIVADO daqui — nunca atualizar
    estoque_atual diretamente. MATERIAL DE CONSUMO §1.2, §2, §3."""

    TIPO_MOVIMENTACAO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
        ('AJUSTE', 'Ajuste de Estoque'),
    ]

    # Subtipos MATERIAL DE CONSUMO §1 (não permitir cadastro manual além destes)
    SUBTIPO_CHOICES = [
        # Entradas
        ('COMPRA_NOVA', 'Compra Nova'),
        ('DEVOLUCAO_ENTRADA', 'Devolução'),
        # Saídas
        ('REQUISICAO', 'Requisição'),
        ('DESCARTE', 'Descarte'),
        # Legado / outros
        ('TRANSFERENCIA', 'Transferência'),
        ('AJUSTE_INVENTARIO', 'Ajuste de Inventário'),
        ('OUTROS', 'Outros'),
    ]

    SUBTIPOS_ENTRADA = ['COMPRA_NOVA', 'DEVOLUCAO_ENTRADA']
    SUBTIPOS_SAIDA = ['REQUISICAO', 'DESCARTE']

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE,
                                 related_name='movimentacoes_estoque',
                                 verbose_name=_('Material'))
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='movimentacoes', verbose_name=_('Lote'))
    numero_serie = models.ForeignKey(NumeroSerie, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='movimentacoes', verbose_name=_('Número de Série'))

    # Tipo e subtipo MATERIAL DE CONSUMO
    tipo_movimentacao = models.CharField(_('Tipo'), max_length=20, choices=TIPO_MOVIMENTACAO_CHOICES)
    subtipo = models.CharField(_('Subtipo'), max_length=30, choices=SUBTIPO_CHOICES,
                                help_text=_('Compra Nova / Devolução / Requisição / Descarte'))

    # Data (MATERIAL DE CONSUMO §2.3, §3 — calendário travado por padrão)
    data_movimentacao = models.DateField(_('Data da Movimentação'), default=timezone.now)

    # Campos de Entrada MATERIAL DE CONSUMO §2
    cor = models.ForeignKey(Cor, on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name=_('Cor'))
    unidade_medida = models.ForeignKey(UnidadeMedida, on_delete=models.SET_NULL,
                                        null=True, blank=True,
                                        verbose_name=_('Unidade de Medida do Item'))
    unidade_fornecimento = models.ForeignKey(UnidadeFornecimento, on_delete=models.SET_NULL,
                                              null=True, blank=True,
                                              verbose_name=_('Unidade de Fornecimento'))
    conta_patrimonial = models.ForeignKey(ContaPatrimonial, on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           verbose_name=_('Conta Patrimonial'))
    localizacao_fisica = models.ForeignKey(LocalizacaoFisica, on_delete=models.SET_NULL,
                                            null=True, blank=True,
                                            verbose_name=_('Localização Física'))
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='movimentacoes_estoque',
                                    verbose_name=_('Fornecedor'))

    # Campos de Saída MATERIAL DE CONSUMO §3
    orgao_requisitante = models.ForeignKey(OrgaoRequisitante, on_delete=models.SET_NULL,
                                            null=True, blank=True,
                                            verbose_name=_('Órgão Requisitante'))
    militar_requisitante = models.ForeignKey('policiais.Policial', on_delete=models.SET_NULL,
                                              null=True, blank=True,
                                              verbose_name=_('Policial do Efetivo (BAEP)'))
    militar_administrativo = models.ForeignKey(MilitarRequisitante, on_delete=models.SET_NULL,
                                                null=True, blank=True,
                                                verbose_name=_('Militar Cadastrado (Adm)'))

    # Quantidades e Valores
    quantidade = models.DecimalField(_('Quantidade'), max_digits=10, decimal_places=2,
                                      validators=[MinValueValidator(Decimal('0.01'))])
    valor_unitario = models.DecimalField(_('Valor Unitário'), max_digits=12, decimal_places=4, default=0)
    valor_total = models.DecimalField(_('Valor Total'), max_digits=14, decimal_places=2,
                                       default=0, editable=False)

    # Referências
    documento_referencia = models.CharField(_('Documento Referência'), max_length=100,
                                             blank=True, null=True)
    nota_fiscal = models.CharField(_('Nota Fiscal'), max_length=100, blank=True, null=True)

    # Auditoria
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT,
                                 related_name='movimentacoes_estoque_registradas',
                                 verbose_name=_('Registrado por'))
    data_hora = models.DateTimeField(_('Data/Hora do Registro'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)

    class Meta:
        verbose_name = _('Movimentação de Estoque')
        verbose_name_plural = _('Movimentações de Estoque')
        ordering = ['-data_hora']
        indexes = [
            models.Index(fields=['produto', '-data_movimentacao']),
            models.Index(fields=['subtipo', '-data_movimentacao']),
            models.Index(fields=['data_movimentacao']),
        ]

    def __str__(self):
        return (f"{self.get_subtipo_display()} — {self.produto.nome} — "
                f"{self.quantidade} — {self.data_movimentacao.strftime('%d/%m/%Y')}")

    def clean(self):
        """Validações de negócio (MATERIAL DE CONSUMO Observações)"""
        super().clean()
        # Subtipo deve ser coerente com tipo
        if self.subtipo in self.SUBTIPOS_ENTRADA and self.tipo_movimentacao != 'ENTRADA':
            raise ValidationError({'subtipo': _('Subtipo de entrada incompatível com tipo de movimentação.')})
        if self.subtipo in self.SUBTIPOS_SAIDA and self.tipo_movimentacao != 'SAIDA':
            raise ValidationError({'subtipo': _('Subtipo de saída incompatível com tipo de movimentação.')})

        # MATERIAL DE CONSUMO: Saída não pode ser maior que saldo disponível
        if self.subtipo in self.SUBTIPOS_SAIDA and self.produto_id:
            from django.db.models import Sum
            saldo = self.produto.saldo_calculado
            quantidade_nova = Decimal(str(self.quantidade or 0))
            if quantidade_nova > saldo:
                raise ValidationError({
                    'quantidade': _(
                        f'Quantidade de saída ({quantidade_nova}) é maior que o saldo disponível ({saldo}). '
                        f'Operação bloqueada conforme MATERIAL DE CONSUMO.'
                    )
                })

    def save(self, *args, **kwargs):
        # Deriva tipo a partir do subtipo
        if self.subtipo in self.SUBTIPOS_ENTRADA:
            self.tipo_movimentacao = 'ENTRADA'
        elif self.subtipo in self.SUBTIPOS_SAIDA:
            self.tipo_movimentacao = 'SAIDA'

        self.valor_total = Decimal(str(self.quantidade or 0)) * Decimal(str(self.valor_unitario or 0))

        if hasattr(self, '_request'):
            self.ip_address = self._request.META.get('REMOTE_ADDR')

        super().save(*args, **kwargs)

        # Atualiza cache de estoque_atual no produto
        try:
            self.produto.estoque_atual = self.produto.saldo_calculado
            Produto.objects.filter(pk=self.produto_id).update(
                estoque_atual=self.produto.estoque_atual)
        except Exception:
            pass


# =============================================================================
# INVENTÁRIO ROTATIVO (MATERIAL DE CONSUMO §1.5)
# =============================================================================

class Inventario(models.Model):
    """Controle de inventários rotativos mensais"""
    STATUS_CHOICES = [
        ('PLANEJADO', 'Planejado'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]
    TIPO_INVENTARIO_CHOICES = [
        ('COMPLETO', 'Completo'),
        ('PARCIAL', 'Parcial'),
        ('ROTATIVO', 'Rotativo'),
        ('SORTEIO', 'Por Sorteio'),
    ]

    numero = models.CharField(_('Número'), max_length=20, unique=True)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    tipo_inventario = models.CharField(_('Tipo'), max_length=20, choices=TIPO_INVENTARIO_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='PLANEJADO')
    data_inicio = models.DateTimeField(_('Data Início'), null=True, blank=True)
    data_fim = models.DateTimeField(_('Data Fim'), null=True, blank=True)
    data_prevista_fim = models.DateTimeField(_('Data Prevista Fim'))
    responsavel = models.ForeignKey(User, on_delete=models.PROTECT,
                                     related_name='inventarios_responsaveis',
                                     verbose_name=_('Responsável'))
    produtos = models.ManyToManyField(Produto, through='ItemInventario', verbose_name=_('Produtos'))
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Inventário')
        verbose_name_plural = _('Inventários')
        ordering = ['-data_cadastro']

    def __str__(self):
        return f"Inventário {self.numero} - {self.get_tipo_inventario_display()}"

    @property
    def total_produtos(self):
        return self.produtos.count()

    @property
    def itens_contados(self):
        return self.itens_inventario.filter(contado_em__isnull=False).count()

    @property
    def percentual_conclusao(self):
        if self.total_produtos == 0:
            return 0
        return (self.itens_contados / self.total_produtos) * 100


class ItemInventario(models.Model):
    """Itens do inventário com contagem física e divergência"""
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE,
                                    related_name='itens_inventario', verbose_name=_('Inventário'))
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE,
                                 related_name='itens_inventario', verbose_name=_('Produto'))
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='itens_inventario', verbose_name=_('Lote'))
    numero_serie = models.ForeignKey(NumeroSerie, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='itens_inventario', verbose_name=_('Número de Série'))

    quantidade_sistema = models.DecimalField(_('Quantidade Sistema'), max_digits=10, decimal_places=2)
    quantidade_contada = models.DecimalField(_('Quantidade Contada'), max_digits=10, decimal_places=2,
                                              null=True, blank=True)
    diferenca = models.DecimalField(_('Diferença'), max_digits=10, decimal_places=2,
                                     null=True, blank=True, editable=False)

    status_contagem = models.CharField(_('Status Contagem'), max_length=20,
                                        choices=[('PENDENTE', 'Pendente'),
                                                 ('CONTADO', 'Contado'),
                                                 ('AJUSTADO', 'Ajustado')],
                                        default='PENDENTE')

    contado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='itens_contados', verbose_name=_('Contado por'))
    contado_em = models.DateTimeField(_('Contado em'), null=True, blank=True)
    justificativa_divergencia = models.TextField(_('Justificativa da Divergência'), blank=True, null=True)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)

    class Meta:
        verbose_name = _('Item de Inventário')
        verbose_name_plural = _('Itens de Inventário')
        unique_together = ['inventario', 'produto', 'lote', 'numero_serie']

    def __str__(self):
        return f"{self.inventario.numero} - {self.produto.nome}"

    def save(self, *args, **kwargs):
        if self.quantidade_contada is not None:
            self.diferenca = self.quantidade_contada - self.quantidade_sistema
        super().save(*args, **kwargs)


class AjusteEstoque(models.Model):
    """Ajustes de estoque com justificativa obrigatória"""
    TIPO_AJUSTE_CHOICES = [
        ('ACRESCIMO', 'Acréscimo'),
        ('DEBITO', 'Débito'),
    ]
    MOTIVO_CHOICES = [
        ('INVENTARIO', 'Inventário'),
        ('PERDA', 'Perda'),
        ('DANO', 'Dano'),
        ('ERRO_OPERACIONAL', 'Erro Operacional'),
        ('DEVOLUCAO', 'Devolução'),
        ('OUTROS', 'Outros'),
    ]

    inventario = models.ForeignKey(Inventario, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='ajustes', verbose_name=_('Inventário'))
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE,
                                 related_name='ajustes', verbose_name=_('Produto'))
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='ajustes', verbose_name=_('Lote'))
    numero_serie = models.ForeignKey(NumeroSerie, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='ajustes', verbose_name=_('Número de Série'))

    tipo_ajuste = models.CharField(_('Tipo Ajuste'), max_length=20, choices=TIPO_AJUSTE_CHOICES)
    motivo = models.CharField(_('Motivo'), max_length=30, choices=MOTIVO_CHOICES)
    quantidade = models.DecimalField(_('Quantidade'), max_digits=10, decimal_places=2)
    valor_unitario = models.DecimalField(_('Valor Unitário'), max_digits=12, decimal_places=4, default=0)
    valor_total = models.DecimalField(_('Valor Total'), max_digits=14, decimal_places=2,
                                       default=0, editable=False)

    quantidade_antes = models.DecimalField(_('Quantidade Antes'), max_digits=10, decimal_places=2)
    quantidade_depois = models.DecimalField(_('Quantidade Depois'), max_digits=10, decimal_places=2)

    observacoes = models.TextField(_('Observações / Justificativa'), blank=True, null=True)

    aprovado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                      related_name='ajustes_aprovados',
                                      verbose_name=_('Aprovado por'))
    data_aprovacao = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = _('Ajuste de Estoque')
        verbose_name_plural = _('Ajustes de Estoque')
        ordering = ['-data_aprovacao']

    def __str__(self):
        return f"{self.get_tipo_ajuste_display()} - {self.produto.nome} - {self.quantidade}"

    def save(self, *args, **kwargs):
        self.valor_total = Decimal(str(self.quantidade)) * Decimal(str(self.valor_unitario or 0))
        super().save(*args, **kwargs)
        # Atualiza cache do produto
        try:
            Produto.objects.filter(pk=self.produto_id).update(
                estoque_atual=self.produto.saldo_calculado)
        except Exception:
            pass


class LogExclusaoMaterial(models.Model):
    """Log de exclusão de materiais de consumo"""
    codigo_material = models.CharField(_('Código'), max_length=50)
    nome_material = models.CharField(_('Nome'), max_length=200)
    categoria = models.CharField(_('Categoria'), max_length=100)
    saldo_na_exclusao = models.DecimalField(_('Saldo na Exclusão'), max_digits=10, decimal_places=2)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Usuário'))
    data_exclusao = models.DateTimeField(auto_now_add=True)
    motivo = models.TextField(_('Motivo / Justificativa'), blank=True, null=True)

    class Meta:
        verbose_name = _('Log de Exclusão de Material')
        verbose_name_plural = _('Logs de Exclusão de Materiais')
        ordering = ['-data_exclusao']

    def __str__(self):
        return f"{self.data_exclusao.strftime('%d/%m/%Y %H:%M')} - {self.nome_material}"


