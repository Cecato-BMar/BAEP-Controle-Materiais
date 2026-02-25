from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
import uuid
from decimal import Decimal
from io import BytesIO


class Categoria(models.Model):
    """Categorias de materiais para organização do estoque"""
    nome = models.CharField(_('Nome'), max_length=100, unique=True)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    codigo = models.CharField(_('Código'), max_length=20, unique=True)
    categoria_pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                                       related_name='subcategorias', verbose_name=_('Categoria Pai'))
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)

    class Meta:
        verbose_name = _('Categoria')
        verbose_name_plural = _('Categorias')
        ordering = ['codigo', 'nome']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    @property
    def hierarquia(self):
        """Retorna a hierarquia completa da categoria"""
        if self.categoria_pai:
            return f"{self.categoria_pai.hierarquia} > {self.nome}"
        return self.nome


class UnidadeMedida(models.Model):
    """Unidades de medida para controle de estoque"""
    sigla = models.CharField(_('Sigla'), max_length=10, unique=True)
    nome = models.CharField(_('Nome'), max_length=50)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    ativo = models.BooleanField(_('Ativo'), default=True)

    class Meta:
        verbose_name = _('Unidade de Medida')
        verbose_name_plural = _('Unidades de Medida')
        ordering = ['sigla']

    def __str__(self):
        return f"{self.sigla} - {self.nome}"


class Fornecedor(models.Model):
    """Cadastro de fornecedores de materiais"""
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


class Produto(models.Model):
    """Cadastro de produtos do estoque"""
    TIPO_PRODUTO_CHOICES = [
        ('ARMAMENTO', 'Armamento'),
        ('MUNICAO', 'Munição'),
        ('EQUIPAMENTO', 'Equipamento'),
        ('VESTUARIO', 'Vestuário'),
        ('MATERIAL_EXPEDIENTE', 'Material de Expediente'),
        ('VEICULO', 'Veículo'),
        ('COMUNICACAO', 'Comunicação'),
        ('MEDICO', 'Material Médico'),
        ('OUTROS', 'Outros'),
    ]
    
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
        ('OBSOLETO', 'Obsoleto'),
        ('EM_DESENVOLVIMENTO', 'Em Desenvolvimento'),
    ]
    
    codigo = models.CharField(_('Código'), max_length=50, unique=True)
    codigo_barras = models.CharField(_('Número do Empenho'), max_length=50, blank=True, null=True, unique=True)
    nome = models.CharField(_('Nome'), max_length=200)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='produtos', verbose_name=_('Categoria'))
    unidade_medida = models.ForeignKey(UnidadeMedida, on_delete=models.PROTECT, verbose_name=_('Unidade de Medida'))
    tipo_produto = models.CharField(_('Tipo Produto'), max_length=20, choices=TIPO_PRODUTO_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='ATIVO')
    
    # Controle de estoque
    estoque_minimo = models.DecimalField(_('Estoque Mínimo'), max_digits=10, decimal_places=2, 
                                        validators=[MinValueValidator(Decimal('0.00'))])
    estoque_maximo = models.DecimalField(_('Estoque Máximo'), max_digits=10, decimal_places=2,
                                        validators=[MinValueValidator(Decimal('0.00'))])
    estoque_atual = models.DecimalField(_('Estoque Atual'), max_digits=10, decimal_places=2, default=0)
    estoque_reservado = models.DecimalField(_('Estoque Reservado'), max_digits=10, decimal_places=2, default=0)
    
    # Valores
    valor_unitario = models.DecimalField(_('Valor Unitário'), max_digits=10, decimal_places=2, default=0)
    valor_total = models.DecimalField(_('Valor Total'), max_digits=12, decimal_places=2, default=0, editable=False)
    
    # Controle de validade (para produtos com validade)
    controla_validade = models.BooleanField(_('Controla Validade'), default=False)
    prazo_validade_meses = models.PositiveIntegerField(_('Prazo Validade (meses)'), null=True, blank=True)
    
    # Controle por número de série (para equipamentos)
    controla_numero_serie = models.BooleanField(_('Controla Número de Série'), default=False)
    
    # Fornecedor padrão
    fornecedor_padrao = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True, 
                                        related_name='produtos_fornecidos', verbose_name=_('Fornecedor Padrão'))
    
    # Imagens
    imagem = models.ImageField(_('Imagem'), upload_to='produtos/', blank=True, null=True)

    # QR Code
    qr_code_token = models.UUIDField(_('Token QR Code'), default=uuid.uuid4, unique=True, editable=False)
    qr_code_imagem = models.ImageField(_('QR Code'), upload_to='produtos/qrcodes/', blank=True, null=True, editable=False)
    
    # Auditoria
    criado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='produtos_criados', verbose_name=_('Criado por'))
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)
    atualizado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='produtos_atualizados', 
                                      verbose_name=_('Atualizado por'), null=True, blank=True)

    class Meta:
        verbose_name = _('Produto')
        verbose_name_plural = _('Produtos')
        ordering = ['codigo', 'nome']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['nome']),
            models.Index(fields=['categoria']),
            models.Index(fields=['tipo_produto']),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    def save(self, *args, **kwargs):
        # Calcula valor total
        self.valor_total = self.estoque_atual * self.valor_unitario
        
        # Define usuário de atualização
        if hasattr(self, '_current_user'):
            self.atualizado_por = self._current_user
        
        super().save(*args, **kwargs)

        if not self.qr_code_imagem:
            try:
                import qrcode

                payload = str(self.qr_code_token)
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=10,
                    border=4,
                )
                qr.add_data(payload)
                qr.make(fit=True)
                img = qr.make_image(fill_color='black', back_color='white')

                buffer = BytesIO()
                img.save(buffer, format='PNG')
                filename = f"qr_{self.codigo}.png"
                self.qr_code_imagem.save(filename, ContentFile(buffer.getvalue()), save=False)

                super().save(update_fields=['qr_code_imagem'])
            except Exception:
                # Não falhar o cadastro caso a dependência do QR Code não esteja disponível
                pass

    @property
    def estoque_disponivel(self):
        """Retorna quantidade disponível para uso"""
        return self.estoque_atual - self.estoque_reservado

    @property
    def precisa_reposicao(self):
        """Verifica se precisa de reposição"""
        return self.estoque_disponivel <= self.estoque_minimo

    @property
    def estoque_critico(self):
        """Verifica se estoque está crítico"""
        return self.estoque_disponivel <= (self.estoque_minimo * Decimal('0.5'))


class Lote(models.Model):
    """Controle de lotes para produtos"""
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='lotes', verbose_name=_('Produto'))
    numero_lote = models.CharField(_('Número do Lote'), max_length=50)
    data_fabricacao = models.DateField(_('Data de Fabricação'), null=True, blank=True)
    data_validade = models.DateField(_('Data de Validade'), null=True, blank=True)
    quantidade_inicial = models.DecimalField(_('Quantidade Inicial'), max_digits=10, decimal_places=2)
    quantidade_atual = models.DecimalField(_('Quantidade Atual'), max_digits=10, decimal_places=2)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, verbose_name=_('Fornecedor'))
    nota_fiscal = models.CharField(_('Nota Fiscal'), max_length=50, blank=True, null=True)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)

    class Meta:
        verbose_name = _('Lote')
        verbose_name_plural = _('Lotes')
        ordering = ['-data_cadastro']
        unique_together = ['produto', 'numero_lote']

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.produto.nome}"

    @property
    def vencido(self):
        """Verifica se lote está vencido"""
        if self.data_validade:
            from django.utils import timezone
            return self.data_validade < timezone.now().date()
        return False

    @property
    def proximo_vencimento(self):
        """Verifica se lote está próximo do vencimento (30 dias)"""
        if self.data_validade:
            from django.utils import timezone
            dias_para_vencer = (self.data_validade - timezone.now().date()).days
            return 0 <= dias_para_vencer <= 30
        return False


class NumeroSerie(models.Model):
    """Controle de números de série para equipamentos"""
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='numeros_serie', verbose_name=_('Produto'))
    numero_serie = models.CharField(_('Número de Série'), max_length=100, unique=True)
    patrimonio = models.CharField(_('Patrimônio'), max_length=50, blank=True, null=True)
    status = models.CharField(_('Status'), max_length=20, choices=Produto.STATUS_CHOICES, default='ATIVO')
    localizacao = models.CharField(_('Localização'), max_length=100, blank=True, null=True)
    responsavel = models.ForeignKey('policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='equipamentos_responsaveis', verbose_name=_('Responsável'))
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)

    class Meta:
        verbose_name = _('Número de Série')
        verbose_name_plural = _('Números de Série')
        ordering = ['produto', 'numero_serie']

    def __str__(self):
        return f"{self.numero_serie} - {self.produto.nome}"


class MovimentacaoEstoque(models.Model):
    """Registro de movimentações de estoque"""
    TIPO_MOVIMENTACAO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
        ('TRANSFERENCIA', 'Transferência'),
        ('AJUSTE', 'Ajuste de Estoque'),
        ('PERDA', 'Perda'),
        ('DEVOLUCAO', 'Devolução'),
    ]
    
    MOTIVO_CHOICES = [
        ('COMPRA', 'Compra'),
        ('DOACAO', 'Doação'),
        ('TRANSFERENCIA', 'Transferência'),
        ('USO', 'Uso Operacional'),
        ('MANUTENCAO', 'Manutenção'),
        ('PERDA', 'Perda'),
        ('ROUBO', 'Roubo'),
        ('DANO', 'Dano'),
        ('AJUSTE_INVENTARIO', 'Ajuste de Inventário'),
        ('DEVOLUCAO_FORNECEDOR', 'Devolução ao Fornecedor'),
        ('OUTROS', 'Outros'),
    ]
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='movimentacoes', verbose_name=_('Produto'))
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentacoes', verbose_name=_('Lote'))
    numero_serie = models.ForeignKey(NumeroSerie, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='movimentacoes', verbose_name=_('Número de Série'))
    
    tipo_movimentacao = models.CharField(_('Tipo Movimentação'), max_length=20, choices=TIPO_MOVIMENTACAO_CHOICES)
    motivo = models.CharField(_('Motivo'), max_length=30, choices=MOTIVO_CHOICES)
    quantidade = models.DecimalField(_('Quantidade'), max_digits=10, decimal_places=2)
    valor_unitario = models.DecimalField(_('Valor Unitário'), max_digits=10, decimal_places=2, default=0)
    valor_total = models.DecimalField(_('Valor Total'), max_digits=12, decimal_places=2, default=0, editable=False)
    
    # Referências
    documento_referencia = models.CharField(_('Documento Referência'), max_length=100, blank=True, null=True)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='movimentacoes', verbose_name=_('Fornecedor'))
    solicitante = models.ForeignKey('policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='movimentacoes_solicitadas', verbose_name=_('Solicitante'))
    destino_origem = models.CharField(_('Destino/Origem'), max_length=200, blank=True, null=True)
    
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    
    # Auditoria
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='movimentacoes_estoque', verbose_name=_('Usuário'))
    data_hora = models.DateTimeField(_('Data e Hora'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True, null=True)

    class Meta:
        verbose_name = _('Movimentação de Estoque')
        verbose_name_plural = _('Movimentações de Estoque')
        ordering = ['-data_hora']
        indexes = [
            models.Index(fields=['produto', '-data_hora']),
            models.Index(fields=['tipo_movimentacao', '-data_hora']),
            models.Index(fields=['data_hora']),
        ]

    def __str__(self):
        return f"{self.get_tipo_movimentacao_display()} - {self.produto.nome} - {self.quantidade} - {self.data_hora.strftime('%d/%m/%Y %H:%M')}"

    def save(self, *args, **kwargs):
        # Calcula valor total
        self.valor_total = self.quantidade * self.valor_unitario
        
        # Captura IP e User Agent se disponível
        if hasattr(self, '_request'):
            self.ip_address = self._request.META.get('REMOTE_ADDR')
            self.user_agent = self._request.META.get('HTTP_USER_AGENT', '')[:500]
        
        super().save(*args, **kwargs)


class Inventario(models.Model):
    """Controle de inventários"""
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
    tipo_inventario = models.CharField(_('Tipo Inventário'), max_length=20, choices=TIPO_INVENTARIO_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='PLANEJADO')
    
    data_inicio = models.DateTimeField(_('Data Início'), null=True, blank=True)
    data_fim = models.DateTimeField(_('Data Fim'), null=True, blank=True)
    data_prevista_fim = models.DateTimeField(_('Data Prevista Fim'))
    
    responsavel = models.ForeignKey(User, on_delete=models.PROTECT, related_name='inventarios_responsaveis', 
                                  verbose_name=_('Responsável'))
    produtos = models.ManyToManyField(Produto, through='ItemInventario', verbose_name=_('Produtos'))
    
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)

    class Meta:
        verbose_name = _('Inventário')
        verbose_name_plural = _('Inventários')
        ordering = ['-data_cadastro']

    def __str__(self):
        return f"Inventário {self.numero} - {self.get_tipo_inventario_display()}"

    @property
    def total_produtos(self):
        """Retorna total de produtos no inventário"""
        return self.produtos.count()

    @property
    def itens_contados(self):
        """Retorna total de itens já contados"""
        return self.itens_inventario.filter(contado_em__isnull=False).count()

    @property
    def percentual_conclusao(self):
        """Retorna percentual de conclusão"""
        if self.total_produtos == 0:
            return 0
        return (self.itens_contados / self.total_produtos) * 100


class ItemInventario(models.Model):
    """Itens do inventário"""
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name='itens_inventario', verbose_name=_('Inventário'))
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='itens_inventario', verbose_name=_('Produto'))
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='itens_inventario', verbose_name=_('Lote'))
    numero_serie = models.ForeignKey(NumeroSerie, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='itens_inventario', verbose_name=_('Número de Série'))
    
    quantidade_sistema = models.DecimalField(_('Quantidade Sistema'), max_digits=10, decimal_places=2)
    quantidade_contada = models.DecimalField(_('Quantidade Contada'), max_digits=10, decimal_places=2, null=True, blank=True)
    diferenca = models.DecimalField(_('Diferença'), max_digits=10, decimal_places=2, null=True, blank=True, editable=False)
    
    status_contagem = models.CharField(_('Status Contagem'), max_length=20, 
                                       choices=[('PENDENTE', 'Pendente'), ('CONTRADO', 'Contado'), ('AJUSTADO', 'Ajustado')],
                                       default='PENDENTE')
    
    contado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='itens_contados', verbose_name=_('Contado por'))
    contado_em = models.DateTimeField(_('Contado em'), null=True, blank=True)
    
    observacoes = models.TextField(_('Observações'), blank=True, null=True)

    class Meta:
        verbose_name = _('Item de Inventário')
        verbose_name_plural = _('Itens de Inventário')
        unique_together = ['inventario', 'produto', 'lote', 'numero_serie']

    def __str__(self):
        return f"{self.inventario.numero} - {self.produto.nome}"

    def save(self, *args, **kwargs):
        # Calcula diferença
        if self.quantidade_contada is not None:
            self.diferenca = self.quantidade_contada - self.quantidade_sistema
        super().save(*args, **kwargs)


class AjusteEstoque(models.Model):
    """Registro de ajustes de estoque"""
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
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='ajustes', verbose_name=_('Produto'))
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='ajustes', verbose_name=_('Lote'))
    numero_serie = models.ForeignKey(NumeroSerie, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='ajustes', verbose_name=_('Número de Série'))
    
    tipo_ajuste = models.CharField(_('Tipo Ajuste'), max_length=20, choices=TIPO_AJUSTE_CHOICES)
    motivo = models.CharField(_('Motivo'), max_length=30, choices=MOTIVO_CHOICES)
    quantidade = models.DecimalField(_('Quantidade'), max_digits=10, decimal_places=2)
    valor_unitario = models.DecimalField(_('Valor Unitário'), max_digits=10, decimal_places=2, default=0)
    valor_total = models.DecimalField(_('Valor Total'), max_digits=12, decimal_places=2, default=0, editable=False)
    
    quantidade_antes = models.DecimalField(_('Quantidade Antes'), max_digits=10, decimal_places=2)
    quantidade_depois = models.DecimalField(_('Quantidade Depois'), max_digits=10, decimal_places=2)
    
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    
    # Auditoria
    aprovado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='ajustes_aprovados', 
                                    verbose_name=_('Aprovado por'))
    data_aprovacao = models.DateTimeField(_('Data Aprovação'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)

    class Meta:
        verbose_name = _('Ajuste de Estoque')
        verbose_name_plural = _('Ajustes de Estoque')
        ordering = ['-data_aprovacao']

    def __str__(self):
        return f"{self.get_tipo_ajuste_display()} - {self.produto.nome} - {self.quantidade}"

    def save(self, *args, **kwargs):
        # Calcula valor total
        self.valor_total = self.quantidade * self.valor_unitario
        super().save(*args, **kwargs)
