"""
viaturas/models.py — Módulo Frota do SIS LOGÍSTICA 2º BAEP

Models, Enums, Constraints, Indexes e Validators para gestão completa da frota:
  - MarcaViatura, ModeloViatura, Viatura (cadastro)
  - DespachoViatura, Abastecimento (operação)
  - Manutencao, ServicoManutencao, EvidenciaManutencao (manutenção)
  - ChecklistViatura (inspeção)
  - SolicitacaoBaixaViatura (baixa)
  - PecaViatura, RetiradaPeca, RetiradaPecaItem (peças)
  - Oficina (cadastro auxiliar)
  - RegistroHistoricoManutencao (auditoria append-only)
  - PlanoManutencaoPreventiva (preventiva)
  - DocumentoViatura (documentos)

Compatível com PostgreSQL (CheckConstraint, Index, validators).
"""
import re
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


# ============================================================================
# CONSTANTES
# ============================================================================
ANO_MINIMO = 1950
ANO_MAXIMO = datetime.now().year + 2


# ============================================================================
# ENUMS (TextChoices) — valores de banco imutáveis
# ============================================================================
class TipoViatura(models.TextChoices):
    QUATRO_RODAS = '4_RODAS', 'Quatro Rodas (Carro/SUV/Pick-up)'
    MOTO = 'MOTO', 'Motocicleta'
    EMBARCACAO = 'EMBARCACAO', 'Embarcação'
    CAMINHAO = 'CAMINHAO', 'Caminhão/Micro-ônibus'


class StatusViatura(models.TextChoices):
    DISPONIVEL = 'DISPONIVEL', 'Disponível (Pronta para uso)'
    EM_USO = 'EM_USO', 'Em Serviço Administrativo'
    MANUTENCAO = 'MANUTENCAO', 'Em Manutenção/Oficina'
    VISTORIA = 'VISTORIA', 'Aguardando Vistoria'
    PREGAO = 'PREGAO', 'Para Pregão'
    BAIXADA = 'BAIXADA', 'Baixada/Inativa'


class Combustivel(models.TextChoices):
    FLEX = 'FLEX', 'Flex (Álcool/Gasolina)'
    GASOLINA = 'GASOLINA', 'Gasolina'
    ALCOOL = 'ALCOOL', 'Etanol'
    DIESEL = 'DIESEL', 'Diesel'
    ELETRICO = 'ELETRICO', 'Elétrico (kWh)'
    OUTRO = 'OUTRO', 'Outro'


class LocalizacaoViatura(models.TextChoices):
    PRIMEIRA_CIA = '1_CIA', '1ª CIA'
    SEGUNDA_CIA = '2_CIA', '2ª CIA'
    TERCEIRA_CIA = '3_CIA', '3ª CIA'
    QUARTA_CIA = '4_CIA', '4ª CIA'
    EM = 'EM', 'EM'
    P4 = 'P4', 'P4'
    MOTOMEC = 'MOTOMEC', 'MOTOMEC'
    OFICINA = 'OFICINA', 'Oficina'
    EM_USO = 'EM_USO', 'Em Serviço Administrativo'


class TipoManutencao(models.TextChoices):
    PREVENTIVA = 'PREVENTIVA', 'Preventiva (Revisão, Óleo, Pneus)'
    CORRETIVA = 'CORRETIVA', 'Corretiva (Quebra, Acidente)'


class StatusManutencao(models.TextChoices):
    AGENDADA = 'AGENDADA', 'Agendada (Futura)'
    ABERTA = 'ABERTA', 'Em Aberto'
    AGUARDANDO_PECA = 'AGUARDANDO_PECA', 'Aguardando Peça'
    CONCLUIDA = 'CONCLUIDA', 'Concluída'
    CANCELADA = 'CANCELADA', 'Cancelada'


class TipoChecklist(models.TextChoices):
    SAIDA = 'SAIDA', 'Saída de Serviço'
    RETORNO = 'RETORNO', 'Retorno de Serviço'
    ROTINA = 'ROTINA', 'Inspeção de Rotina/Semanal'


class StatusBaixa(models.TextChoices):
    PENDENTE = 'PENDENTE', 'Pendente (Aguardando Análise)'
    MANUTENCAO = 'MANUTENCAO', 'Encaminhar para Manutenção'
    OFICINA = 'OFICINA', 'Encaminhar para Oficina'
    AGUARDAR_VISTORIA = 'AGUARDAR_VISTORIA', 'Aguardar Vistoria'
    MOTOMEC = 'MOTOMEC', 'Encaminhar para MOTOMEC'
    PREGAO = 'PREGAO', 'Destinar para Pregão'
    DESCARGA = 'DESCARGA', 'Efetuar Descarga (Baixa Definitiva)'
    NEGADA = 'NEGADA', 'Negada/Cancelada'


class CategoriaBaixa(models.TextChoices):
    PREVENTIVA = 'PREVENTIVA', 'Manutenção Preventiva'
    SUBSTITUICAO = 'SUBSTITUICAO', 'Substituição de Peças'
    QUEBRA = 'QUEBRA', 'Quebra / Defeito Mecânico'
    ACIDENTE = 'ACIDENTE', 'Acidente / Sinistro'
    INSERVIVEL = 'INSERVIVEL', 'Inservível / Fim de Vida Útil'
    REPASSE = 'REPASSE', 'Repasse / Transferência'
    LEILAO = 'LEILAO', 'Destinação para Leilão'
    OUTROS = 'OUTROS', 'Outros Motivos'


class CategoriaPeca(models.TextChoices):
    MOTOR = 'MOTOR', 'Motor e Componentes'
    SUSPENSAO = 'SUSPENSAO', 'Suspensão e Direção'
    FREIOS = 'FREIOS', 'Freios'
    ELETRICA = 'ELETRICA', 'Elétrica e Iluminação'
    TRANSMISSAO = 'TRANSMISSAO', 'Transmissão e Embreagem'
    CARROCERIA = 'CARROCERIA', 'Carroceria e Acabamento'
    LUBRIFICANTES = 'LUBRIFICANTES', 'Fluidos e Lubrificantes'
    OUTROS = 'OUTROS', 'Outros/Geral'


class TipoEvidencia(models.TextChoices):
    FOTO_ANTES = 'FOTO_ANTES', 'Foto Antes do Serviço'
    FOTO_DEPOIS = 'FOTO_DEPOIS', 'Foto Após o Serviço'
    ORCAMENTO = 'ORCAMENTO', 'Orçamento'
    LAUDO = 'LAUDO', 'Laudo Técnico'
    OUTRO = 'OUTRO', 'Outro Documento'


class TipoEventoManutencao(models.TextChoices):
    ABERTURA = 'ABERTURA', 'Abertura da Manutenção'
    SERVICO = 'SERVICO', 'Serviço Registrado'
    ATUALIZACAO = 'ATUALIZACAO', 'Atualização Administrativa'
    STATUS = 'STATUS', 'Mudança de Status'
    CONCLUSAO = 'CONCLUSAO', 'Conclusão'
    CANCELAMENTO = 'CANCELAMENTO', 'Cancelamento'
    EVIDENCIA = 'EVIDENCIA', 'Evidência Anexada'


class TipoDocumento(models.TextChoices):
    CRLV = 'CRLV', 'CRLV (Certificado de Registro e Licenciamento)'
    SEGURO = 'SEGURO', 'Apólice de Seguro'
    IPVA = 'IPVA', 'IPVA (Imposto sobre Propriedade)'
    DPVAT = 'DPVAT', 'DPVAT (Seguro Obrigatório)'
    VISTORIA = 'VISTORIA', 'Laudo de Vistoria'
    OUTRO = 'OUTRO', 'Outro Documento'


# ============================================================================
# VALIDATORS
# ============================================================================
validate_placa_veiculo = RegexValidator(
    regex=r'^[A-Z]{3}\s?-?\s?[0-9][0-9A-Z][0-9]{2}$',
    message='Formato de placa inválido. Use ABC-1234 ou ABC1D23 (Mercosul).',
    code='placa_invalida',
)


def validate_ano_fabricacao(value):
    """Valida ano de fabricação entre 1950 e ano atual + 2."""
    if value is not None and (value < ANO_MINIMO or value > ANO_MAXIMO):
        raise ValidationError(
            f'Ano de fabricação deve estar entre {ANO_MINIMO} e {ANO_MAXIMO}.',
            code='ano_invalido',
        )


def validate_cnpj(value):
    """Validação básica de formato de CNPJ (apenas dígitos e tamanho)."""
    if value:
        cnpj_digits = re.sub(r'\D', '', value)
        if len(cnpj_digits) != 14:
            raise ValidationError(
                'CNPJ deve conter exatamente 14 dígitos.',
                code='cnpj_invalido',
            )


def validate_valor_positivo(value):
    """Garante que valores monetários sejam não-negativos."""
    if value is not None and value < Decimal('0'):
        raise ValidationError('O valor não pode ser negativo.', code='valor_negativo')


# ============================================================================
# MODELS
# ============================================================================
class MarcaViatura(models.Model):
    """Marcas de Viaturas (Ex: Toyota, Yamaha, Chevrolet)"""
    nome = models.CharField(_('Nome da Marca'), max_length=50, unique=True)
    ativo = models.BooleanField(_('Ativo'), default=True)

    class Meta:
        verbose_name = _('Marca')
        verbose_name_plural = _('Marcas')
        ordering = ['nome']
        indexes = [
            models.Index(fields=['ativo', 'nome'], name='idx_marca_ativo_nome'),
        ]

    def __str__(self):
        return self.nome


class ModeloViatura(models.Model):
    """Modelos atrelados às marcas (Ex: Hilux, XT 660)"""
    marca = models.ForeignKey(
        MarcaViatura, on_delete=models.PROTECT, related_name='modelos',
    )
    nome = models.CharField(_('Nome do Modelo'), max_length=100)
    tipo = models.CharField(
        _('Tipo de Viatura'), max_length=20, choices=TipoViatura.choices,
    )
    ativo = models.BooleanField(_('Ativo'), default=True)

    class Meta:
        verbose_name = _('Modelo')
        verbose_name_plural = _('Modelos')
        ordering = ['marca__nome', 'nome']
        indexes = [
            models.Index(fields=['tipo', 'ativo'], name='idx_modelo_tipo_ativo'),
            models.Index(fields=['marca', 'nome'], name='idx_modelo_marca_nome'),
        ]

    def __str__(self):
        return f"{self.marca.nome} {self.nome} ({self.get_tipo_display()})"


class Viatura(models.Model):
    """Cadastro principal da viatura física"""
    prefixo = models.CharField(
        _('Prefixo da Viatura'), max_length=20, unique=True,
        help_text="Ex: E-10201",
    )
    placa = models.CharField(
        _('Placa'), max_length=15, blank=True, null=True, unique=True,
        validators=[validate_placa_veiculo],
    )
    chassi = models.CharField(_('Chassi/Nº de Série'), max_length=100, blank=True, null=True)
    renavam = models.CharField(_('RENAVAM'), max_length=30, blank=True, null=True)
    numero_patrimonio = models.CharField(
        _('Nº Patrimônio'), max_length=50, blank=True, null=True, unique=True,
    )

    modelo = models.ForeignKey(
        ModeloViatura, on_delete=models.PROTECT, related_name='viaturas',
    )
    ano_fabricacao = models.PositiveIntegerField(
        _('Ano de Fabricação'), blank=True, null=True,
        validators=[validate_ano_fabricacao],
    )
    cor = models.CharField(_('Cor Predominante'), max_length=30, default="Cinza/PM")

    tipo_combustivel = models.CharField(
        _('Tipo de Combustível Padrão'), max_length=20,
        choices=Combustivel.choices, default=Combustivel.FLEX,
    )
    capacidade_tanque = models.DecimalField(
        _('Capacidade do Tanque (L)'), max_digits=6, decimal_places=2,
        default=0, validators=[MinValueValidator(Decimal('0'))],
    )

    # Controle de Rodagem
    odometro_atual = models.DecimalField(
        _('Odômetro/Horímetro Atual'), max_digits=10, decimal_places=1,
        default=0, help_text="Km ou Horas(embarcação)",
        validators=[MinValueValidator(Decimal('0'))],
    )

    status = models.CharField(
        _('Status Atual'), max_length=20,
        choices=StatusViatura.choices, default=StatusViatura.DISPONIVEL,
    )
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    localizacao = models.CharField(
        _('Localização Atual'), max_length=20,
        choices=LocalizacaoViatura.choices, default=LocalizacaoViatura.MOTOMEC,
    )

    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Viatura')
        verbose_name_plural = _('Viaturas')
        ordering = ['modelo__tipo', 'prefixo']
        constraints = [
            models.CheckConstraint(
                check=models.Q(ano_fabricacao__gte=ANO_MINIMO, ano_fabricacao__lte=ANO_MAXIMO)
                | models.Q(ano_fabricacao__isnull=True),
                name='ck_viatura_ano_fabricacao_valido',
            ),
            models.CheckConstraint(
                check=models.Q(capacidade_tanque__gte=0),
                name='ck_viatura_capacidade_tanque_positiva',
            ),
            models.CheckConstraint(
                check=models.Q(odometro_atual__gte=0),
                name='ck_viatura_odometro_nao_negativo',
            ),
        ]
        indexes = [
            models.Index(fields=['status'], name='idx_viatura_status'),
            models.Index(fields=['localizacao'], name='idx_viatura_localizacao'),
            models.Index(fields=['placa'], name='idx_viatura_placa'),
            models.Index(fields=['prefixo'], name='idx_viatura_prefixo'),
            models.Index(
                fields=['modelo', 'status'],
                name='idx_viatura_modelo_status',
            ),
        ]

    @property
    def tipo(self):
        return self.modelo.get_tipo_display()

    def __str__(self):
        return f"{self.prefixo} - {self.modelo.nome} [{self.get_status_display()}]"


class DespachoViatura(models.Model):
    """Controle de Saída (Despacho) e Retorno das Viaturas para o Policiamento"""
    viatura = models.ForeignKey(
        Viatura, on_delete=models.PROTECT, related_name='despachos',
    )
    motorista = models.ForeignKey(
        'policiais.Policial', on_delete=models.PROTECT,
        related_name='despachos_motorista', verbose_name="Motorista",
    )
    encarregado = models.ForeignKey(
        'policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='despachos_encarregado', verbose_name="Encarregado/Cmt Eqp",
    )

    data_saida = models.DateTimeField(_('Data/Hora de Saída'), auto_now_add=True)
    km_saida = models.DecimalField(
        _('Odômetro na Saída'), max_digits=10, decimal_places=1,
        validators=[MinValueValidator(Decimal('0'))],
    )

    data_retorno = models.DateTimeField(
        _('Data/Hora de Retorno'), blank=True, null=True,
    )
    km_retorno = models.DecimalField(
        _('Odômetro no Retorno'), max_digits=10, decimal_places=1,
        blank=True, null=True, validators=[MinValueValidator(Decimal('0'))],
    )

    observacoes_saida = models.TextField(_('Avarias/Obs na Saída'), blank=True, null=True)
    observacoes_retorno = models.TextField(_('Avarias/Obs no Retorno'), blank=True, null=True)

    registrado_por = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name="Despachante",
    )

    class Meta:
        verbose_name = _('Despacho de Viatura')
        verbose_name_plural = _('Despachos de Viaturas')
        ordering = ['-data_saida']
        constraints = [
            models.CheckConstraint(
                check=models.Q(km_saida__gte=0),
                name='ck_despacho_km_saida_positivo',
            ),
            models.CheckConstraint(
                check=models.Q(km_retorno__isnull=True) | models.Q(km_retorno__gte=0),
                name='ck_despacho_km_retorno_positivo',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(data_retorno__isnull=True)
                    | models.Q(data_retorno__gte=models.F('data_saida'))
                ),
                name='ck_despacho_retorno_apos_saida',
            ),
        ]
        indexes = [
            models.Index(fields=['viatura', '-data_saida'], name='idx_despacho_viat_data'),
            models.Index(fields=['-data_saida'], name='idx_despacho_data_saida'),
            models.Index(fields=['motorista'], name='idx_despacho_motorista'),
            models.Index(
                fields=['viatura', 'data_retorno'],
                name='idx_despacho_viat_retorno',
            ),
        ]

    def __str__(self):
        return f"Despacho {self.viatura.prefixo} em {self.data_saida.strftime('%d/%m/%Y %H:%M')}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Atualiza o status da Viatura
        if not self.data_retorno:
            if self.viatura.status == 'DISPONIVEL':
                self.viatura.status = 'EM_USO'
                self.viatura.localizacao = 'EM_USO'
                self.viatura.save(update_fields=['status', 'localizacao'])
        else:
            if self.viatura.status == 'EM_USO':
                self.viatura.status = 'DISPONIVEL'
                self.viatura.save(update_fields=['status'])

        # Atualiza o odômetro da Viatura
        km_atual = self.km_retorno if self.km_retorno else self.km_saida
        if km_atual and km_atual > self.viatura.odometro_atual:
            self.viatura.odometro_atual = km_atual
            self.viatura.save(update_fields=['odometro_atual'])


class Abastecimento(models.Model):
    """Registro de Abastecimento/Cotas"""
    viatura = models.ForeignKey(
        Viatura, on_delete=models.PROTECT, related_name='abastecimentos',
    )
    motorista = models.ForeignKey(
        'policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Quem abasteceu",
    )

    data_abastecimento = models.DateTimeField(_('Data e Hora'))
    odometro = models.DecimalField(
        _('Odômetro no momento'), max_digits=10, decimal_places=1,
        validators=[MinValueValidator(Decimal('0'))],
    )

    combustivel = models.CharField(
        _('Tipo Utilizado'), max_length=20, choices=Combustivel.choices,
    )
    quantidade_litros = models.DecimalField(
        _('Quantidade (Litros)'), max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    valor_total = models.DecimalField(
        _('Valor Total (R$)'), max_digits=10, decimal_places=2,
        blank=True, null=True, validators=[MinValueValidator(Decimal('0'))],
    )

    cupom_fiscal = models.CharField(
        _('Cupom Fiscal/Requisição'), max_length=50, blank=True, null=True,
    )
    posto_fornecedor = models.CharField(
        _('Posto/Fornecedor'), max_length=100, blank=True, null=True,
    )

    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _('Abastecimento')
        verbose_name_plural = _('Abastecimentos')
        ordering = ['-data_abastecimento']
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantidade_litros__gt=0),
                name='ck_abastecimento_litros_positivo',
            ),
            models.CheckConstraint(
                check=models.Q(odometro__gte=0),
                name='ck_abastecimento_odometro_positivo',
            ),
            models.CheckConstraint(
                check=models.Q(valor_total__isnull=True) | models.Q(valor_total__gte=0),
                name='ck_abastecimento_valor_positivo',
            ),
        ]
        indexes = [
            models.Index(
                fields=['viatura', '-data_abastecimento'],
                name='idx_abast_viat_data',
            ),
            models.Index(fields=['-data_abastecimento'], name='idx_abast_data'),
            models.Index(fields=['combustivel'], name='idx_abast_combustivel'),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.odometro and self.odometro > self.viatura.odometro_atual:
            self.viatura.odometro_atual = self.odometro
            self.viatura.save(update_fields=['odometro_atual'])


class Oficina(models.Model):
    """Cadastro de Oficinas e Oficinas Especializadas"""
    nome = models.CharField(_('Nome/Razão Social'), max_length=150)
    cnpj = models.CharField(
        _('CNPJ'), max_length=20, blank=True, null=True,
        validators=[validate_cnpj],
    )
    endereco = models.CharField(_('Endereço'), max_length=255, blank=True, null=True)
    cidade = models.CharField(_('Cidade'), max_length=100, default='Santos')
    telefone = models.CharField(_('Telefone/WhatsApp'), max_length=50, blank=True, null=True)
    contato_responsavel = models.CharField(
        _('Nome do Contato'), max_length=100, blank=True, null=True,
    )
    especialidade = models.CharField(
        _('Especialidade'), max_length=100, blank=True, null=True,
        help_text="Ex: Funilaria, Mecânica Diesel, Elétrica",
    )
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Oficina')
        verbose_name_plural = _('Oficinas')
        ordering = ['nome']
        indexes = [
            models.Index(fields=['ativo', 'nome'], name='idx_oficina_ativo_nome'),
        ]

    def __str__(self):
        return self.nome


class Manutencao(models.Model):
    """Controle de Manutenções Preventivas e Corretivas"""
    viatura = models.ForeignKey(
        Viatura, on_delete=models.PROTECT, related_name='manutencoes',
    )
    tipo = models.CharField(
        _('Tipo de Manutenção'), max_length=20, choices=TipoManutencao.choices,
    )
    status = models.CharField(
        _('Status'), max_length=20, choices=StatusManutencao.choices,
        default=StatusManutencao.ABERTA,
    )

    data_inicio = models.DateField(_('Data de Início'))
    data_conclusao = models.DateField(_('Data de Conclusão'), blank=True, null=True)

    odometro = models.DecimalField(
        _('Odômetro na Manutenção'), max_digits=10, decimal_places=1,
        validators=[MinValueValidator(Decimal('0'))],
    )

    descricao = models.TextField(_('Descrição dos Serviços/Peças'))
    oficina = models.CharField(_('Oficina (Texto)'), max_length=150, blank=True, null=True)
    oficina_fk = models.ForeignKey(
        Oficina, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencoes', verbose_name=_('Oficina (Cadastrada)'),
    )

    custo_pecas = models.DecimalField(
        _('Custo Peças (R$)'), max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    custo_mao_obra = models.DecimalField(
        _('Custo Mão de Obra (R$)'), max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )

    ordem_servico = models.CharField(_('O.S. Nº'), max_length=50, blank=True, null=True)

    # Controle e Auditoria da Manutenção
    servicos_executados_corretamente = models.BooleanField(
        _('Serviços executados corretamente?'), default=False,
        help_text='Marque após a verificação/teste da viatura',
    )
    detalhamento_servicos = models.TextField(
        _('Detalhamento dos Serviços (Pós-Manutenção)'), blank=True, null=True,
        help_text='O que foi efetivamente feito na oficina',
    )
    detalhamento_pecas_garantia = models.TextField(
        _('Peças Trocadas e Condições de Garantia'), blank=True, null=True,
    )

    # Anexos
    nota_fiscal = models.FileField(
        _('Nota Fiscal (Anexo)'), upload_to='viaturas/manutencao/notas/',
        blank=True, null=True,
    )
    termo_garantia = models.FileField(
        _('Termo de Garantia (Anexo)'), upload_to='viaturas/manutencao/garantias/',
        blank=True, null=True,
    )

    # Validades
    data_validade_garantia = models.DateField(
        _('Validade da Garantia (Data)'), blank=True, null=True,
    )
    km_validade_garantia = models.DecimalField(
        _('Validade da Garantia (Km)'), max_digits=10, decimal_places=1,
        blank=True, null=True,
    )

    registrado_por = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='manutencoes_registradas',
    )

    # Timestamps de Auditoria
    data_criacao = models.DateTimeField(_('Data de Criação'), auto_now_add=True, null=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True, null=True)

    # Controle de Aprovação (Fase 2)
    aprovado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencoes_aprovadas', verbose_name=_('Aprovado por'),
    )
    data_aprovacao = models.DateTimeField(
        _('Data de Aprovação'), null=True, blank=True,
    )
    parecer_aprovacao = models.TextField(
        _('Parecer de Aprovação/Conclusão'), blank=True, null=True,
    )

    # Controle de Cancelamento (Fase 2)
    motivo_cancelamento = models.TextField(
        _('Motivo do Cancelamento'), blank=True, null=True,
    )
    cancelado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencoes_canceladas', verbose_name=_('Cancelado por'),
    )
    data_cancelamento = models.DateTimeField(
        _('Data do Cancelamento'), null=True, blank=True,
    )

    # Vínculo com Retirada de Peças (Fase 3)
    retirada_pecas = models.ForeignKey(
        'RetiradaPeca', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencao_vinculada',
        verbose_name=_('Retirada de Peças Vinculada'),
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Manutenção')
        verbose_name_plural = _('Manutenções')
        ordering = ['-data_inicio']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(data_conclusao__isnull=True)
                    | models.Q(data_conclusao__gte=models.F('data_inicio'))
                ),
                name='ck_manutencao_conclusao_apos_inicio',
            ),
            models.CheckConstraint(
                check=models.Q(custo_pecas__gte=0),
                name='ck_manutencao_custo_pecas_positivo',
            ),
            models.CheckConstraint(
                check=models.Q(custo_mao_obra__gte=0),
                name='ck_manutencao_custo_mao_obra_positivo',
            ),
            models.CheckConstraint(
                check=models.Q(odometro__gte=0),
                name='ck_manutencao_odometro_positivo',
            ),
        ]
        indexes = [
            models.Index(
                fields=['viatura', 'status'],
                name='idx_manut_viat_status',
            ),
            models.Index(fields=['status'], name='idx_manut_status'),
            models.Index(fields=['-data_inicio'], name='idx_manut_data_inicio'),
            models.Index(fields=['tipo'], name='idx_manut_tipo'),
            models.Index(
                fields=['data_validade_garantia'],
                name='idx_manut_validade_garantia',
            ),
            models.Index(fields=['oficina_fk'], name='idx_manut_oficina'),
        ]

    @property
    def custo_total(self):
        return self.custo_pecas + self.custo_mao_obra

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Atualiza o status da Viatura
        if self.status in ['ABERTA', 'AGUARDANDO_PECA']:
            if self.viatura.status != 'MANUTENCAO':
                self.viatura.status = 'MANUTENCAO'
                self.viatura.localizacao = 'OFICINA'
                self.viatura.save(update_fields=['status', 'localizacao'])
        elif self.status in ['CONCLUIDA', 'CANCELADA']:
            if self.viatura.status == 'MANUTENCAO':
                outras_ativas = (
                    self.viatura.manutencoes
                    .filter(status__in=['ABERTA', 'AGUARDANDO_PECA'])
                    .exclude(pk=self.pk)
                    .exists()
                )
                if not outras_ativas:
                    self.viatura.status = 'DISPONIVEL'
                    self.viatura.localizacao = 'MOTOMEC'
                    self.viatura.save(update_fields=['status', 'localizacao'])

        # Atualiza odômetro
        if self.odometro and self.odometro > self.viatura.odometro_atual:
            self.viatura.odometro_atual = self.odometro
            self.viatura.save(update_fields=['odometro_atual'])


class ChecklistViatura(models.Model):
    """Checklist completo para avaliação da viatura (Inspeção Operacional)"""
    viatura = models.ForeignKey(
        Viatura, on_delete=models.CASCADE, related_name='checklists',
    )
    policial = models.ForeignKey(
        'policiais.Policial', on_delete=models.PROTECT, verbose_name="Avaliador",
    )
    tipo = models.CharField(
        _('Tipo de Checklist'), max_length=20,
        choices=TipoChecklist.choices, default=TipoChecklist.SAIDA,
    )
    data_hora = models.DateTimeField(auto_now_add=True)
    odometro = models.DecimalField(
        _('Odômetro Atual'), max_digits=10, decimal_places=1,
        validators=[MinValueValidator(Decimal('0'))],
    )

    # Conservação e Limpeza
    limpeza_interna = models.BooleanField(_('Limpeza Interna OK?'), default=True)
    limpeza_externa = models.BooleanField(_('Limpeza Externa OK?'), default=True)
    conservacao_estofados = models.BooleanField(_('Estofados/Bancos OK?'), default=True)

    # Mecânica e Fluídos
    niveis_fluidos = models.BooleanField(_('Níveis de Óleo/Água OK?'), default=True)
    pneus_condicoes = models.BooleanField(_('Pneus em boas condições?'), default=True)
    pneu_estepe = models.BooleanField(_('Pneu Estepe presente/cheio?'), default=True)
    freio_estacionamento = models.BooleanField(_('Freio de Mão OK?'), default=True)

    # Elétrica e Sinalização
    farois_lanternas = models.BooleanField(_('Faróis e Lanternas OK?'), default=True)
    setas_emergencia = models.BooleanField(_('Setas/Pisca-alerta OK?'), default=True)
    giroflex_sirene = models.BooleanField(_('Giroflex e Sirene OK?'), default=True)
    painel_instrumentos = models.BooleanField(_('Instrumentos do Painel OK?'), default=True)

    # Equipamentos e Acessórios
    extintor_incendio = models.BooleanField(_('Extintor (Carga/Validade) OK?'), default=True)
    triangulo_macaco_chave = models.BooleanField(
        _('Triângulo/Macaco/Chave Roda OK?'), default=True,
    )
    cones_sinalizacao = models.BooleanField(_('Cones de Sinalização OK?'), default=True)
    documentacao_crlv = models.BooleanField(_('Documentação (CRLV) OK?'), default=True)
    kit_primeiros_socorros = models.BooleanField(
        _('Kit Primeiros Socorros OK?'), default=True,
    )

    # Registro de Danos
    avarias_lataria = models.TextField(
        _('Avarias na Lataria/Pintura'), blank=True, null=True,
        help_text="Descreva riscos, mossas ou quebras",
    )
    observacoes_gerais = models.TextField(_('Observações Gerais'), blank=True, null=True)

    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Checklist de Viatura')
        verbose_name_plural = _('Checklists de Viaturas')
        ordering = ['-data_hora']
        constraints = [
            models.CheckConstraint(
                check=models.Q(odometro__gte=0),
                name='ck_checklist_odometro_positivo',
            ),
        ]
        indexes = [
            models.Index(
                fields=['viatura', '-data_hora'],
                name='idx_checklist_viat_data',
            ),
            models.Index(fields=['tipo'], name='idx_checklist_tipo'),
        ]

    def __str__(self):
        return (
            f"Checklist {self.viatura.prefixo} - {self.get_tipo_display()}"
            f" ({self.data_hora.strftime('%d/%m/%Y')})"
        )


class SolicitacaoBaixaViatura(models.Model):
    viatura = models.ForeignKey(
        Viatura, on_delete=models.CASCADE, related_name='solicitacoes_baixa',
    )
    solicitante = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='baixas_solicitadas',
        help_text="Usuário logado que registrou",
    )

    motorista = models.ForeignKey(
        'policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='baixas_como_motorista', verbose_name=_('Motorista Responsável'),
    )
    requisitante = models.ForeignKey(
        'policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='baixas_requisitadas', verbose_name=_('Policial Requisitante'),
    )

    categoria_motivo = models.CharField(
        _('Categoria da Baixa'), max_length=25,
        choices=CategoriaBaixa.choices, default=CategoriaBaixa.INSERVIVEL,
    )
    quilometragem_baixa = models.DecimalField(
        _('Quilometragem/Horímetro na Baixa'), max_digits=10, decimal_places=1,
        null=True, blank=True, validators=[MinValueValidator(Decimal('0'))],
    )

    motivo = models.TextField(_('Justificativa Detalhada'))
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        _('Status'), max_length=20,
        choices=StatusBaixa.choices, default=StatusBaixa.PENDENTE,
    )
    observacoes_admin = models.TextField(
        _('Observações/Parecer do Gestor'), blank=True, null=True,
    )
    analisado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='baixas_analisadas',
    )
    data_analise = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _('Solicitação de Baixa de Viatura')
        verbose_name_plural = _('Solicitações de Baixa de Viatura')
        ordering = ['-data_solicitacao']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(quilometragem_baixa__isnull=True)
                    | models.Q(quilometragem_baixa__gte=0)
                ),
                name='ck_baixa_km_positivo',
            ),
        ]
        indexes = [
            models.Index(
                fields=['viatura', 'status'],
                name='idx_baixa_viat_status',
            ),
            models.Index(fields=['status'], name='idx_baixa_status'),
            models.Index(fields=['-data_solicitacao'], name='idx_baixa_data_solic'),
        ]

    def __str__(self):
        return f"Baixa {self.viatura.prefixo} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Lógica de atualização movida para a view (múltiplas destinações)
        super().save(*args, **kwargs)


class PecaViatura(models.Model):
    """Cadastro de Peças para Viaturas"""
    nome = models.CharField(_('Nome da Peça'), max_length=150)
    codigo = models.CharField(_('Código/Part Number'), max_length=50, blank=True, null=True)
    categoria = models.CharField(
        _('Categoria/Sistema'), max_length=30,
        choices=CategoriaPeca.choices, default=CategoriaPeca.OUTROS,
    )
    marca_fabricante = models.CharField(
        _('Marca/Fabricante'), max_length=100, blank=True, null=True,
    )
    aplicacao = models.TextField(
        _('Aplicação (Modelos Compatíveis)'), blank=True, null=True,
    )

    quantidade_estoque = models.PositiveIntegerField(_('Quantidade em Estoque'), default=0)
    limite_minimo = models.PositiveIntegerField(_('Estoque Mínimo'), default=0)
    localizacao_estoque = models.CharField(
        _('Localização no Estoque'), max_length=100, blank=True, null=True,
        help_text="Ex: Prateleira 2, Gaveta A",
    )
    valor_unitario = models.DecimalField(
        _('Valor Unitário Estimado (R$)'), max_digits=10, decimal_places=2,
        blank=True, null=True, validators=[MinValueValidator(Decimal('0'))],
    )

    observacoes = models.TextField(_('Observações Gerais'), blank=True, null=True)
    ativo = models.BooleanField(_('Ativo'), default=True)

    class Meta:
        verbose_name = _('Peça de Viatura')
        verbose_name_plural = _('Peças de Viaturas')
        ordering = ['nome']
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantidade_estoque__gte=0),
                name='ck_peca_estoque_nao_negativo',
            ),
            models.CheckConstraint(
                check=models.Q(limite_minimo__gte=0),
                name='ck_peca_limite_minimo_positivo',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(valor_unitario__isnull=True)
                    | models.Q(valor_unitario__gte=0)
                ),
                name='ck_peca_valor_unitario_positivo',
            ),
        ]
        indexes = [
            models.Index(
                fields=['categoria', 'ativo'],
                name='idx_peca_categoria_ativo',
            ),
            models.Index(fields=['ativo', 'nome'], name='idx_peca_ativo_nome'),
            models.Index(fields=['codigo'], name='idx_peca_codigo'),
        ]

    def __str__(self):
        return f"{self.nome} ({self.quantidade_estoque} em estoque)"


class RetiradaPeca(models.Model):
    """Registro de Retirada de Peças para uso em Viatura"""
    viatura = models.ForeignKey(
        Viatura, on_delete=models.PROTECT, related_name='retiradas_pecas',
        verbose_name=_('Viatura de Destino'),
    )
    policial = models.ForeignKey(
        'policiais.Policial', on_delete=models.PROTECT,
        related_name='retiradas_pecas', verbose_name=_('Policial que Retirou'),
    )
    data_retirada = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(_('Observações/Justificativa'), blank=True, null=True)

    assinado_eletronicamente = models.BooleanField(
        _('Assinado Eletronicamente?'), default=False,
    )
    arquivo_recibo = models.FileField(
        _('Recibo de Retirada'), upload_to='viaturas/recibos_pecas/',
        null=True, blank=True,
    )

    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _('Retirada de Peça')
        verbose_name_plural = _('Retiradas de Peças')
        ordering = ['-data_retirada']
        indexes = [
            models.Index(
                fields=['viatura', '-data_retirada'],
                name='idx_retirada_peca_viat_data',
            ),
            models.Index(fields=['-data_retirada'], name='idx_retirada_peca_data'),
            models.Index(fields=['policial'], name='idx_retirada_peca_policial'),
        ]

    def __str__(self):
        return f"Retirada para {self.viatura.prefixo} em {self.data_retirada.strftime('%d/%m/%Y')}"


class RetiradaPecaItem(models.Model):
    retirada = models.ForeignKey(RetiradaPeca, on_delete=models.CASCADE, related_name='itens')
    peca = models.ForeignKey(PecaViatura, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(
        _('Quantidade'), validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = _('Item da Retirada de Peça')
        verbose_name_plural = _('Itens da Retirada de Peça')
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantidade__gte=1),
                name='ck_retirada_item_qtd_minima',
            ),
        ]
        indexes = [
            models.Index(fields=['retirada'], name='idx_retirada_item_retirada'),
            models.Index(fields=['peca'], name='idx_retirada_item_peca'),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.peca.quantidade_estoque >= self.quantidade:
                self.peca.quantidade_estoque -= self.quantidade
                self.peca.save()
            else:
                raise ValueError("Estoque insuficiente para a peça.")
        super().save(*args, **kwargs)


class EvidenciaManutencao(models.Model):
    """Fotos, laudos e documentos complementares de uma manutenção (Fase 3)"""
    manutencao = models.ForeignKey(
        Manutencao, on_delete=models.CASCADE, related_name='evidencias',
    )
    tipo = models.CharField(
        _('Tipo de Evidência'), max_length=20, choices=TipoEvidencia.choices,
    )
    arquivo = models.FileField(
        _('Arquivo'), upload_to='viaturas/manutencao/evidencias/',
    )
    descricao = models.CharField(_('Descrição'), max_length=200, blank=True)
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)
    data_upload = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Evidência de Manutenção')
        verbose_name_plural = _('Evidências de Manutenção')
        ordering = ['-data_upload']
        indexes = [
            models.Index(
                fields=['manutencao', 'tipo'],
                name='idx_evidencia_manut_tipo',
            ),
        ]

    def __str__(self):
        return (
            f"{self.get_tipo_display()} — {self.manutencao.viatura.prefixo}"
            f" ({self.data_upload.strftime('%d/%m/%Y')})"
        )


class ServicoManutencao(models.Model):
    """Registro imutável de cada serviço executado dentro de uma manutenção."""
    manutencao = models.ForeignKey(
        Manutencao, on_delete=models.CASCADE, related_name='servicos',
        verbose_name=_('Manutenção'),
    )
    descricao = models.TextField(_('Descrição do Serviço'))
    detalhamento = models.TextField(_('Detalhamento'), blank=True, null=True)
    pecas_garantia = models.TextField(_('Peças / Garantia'), blank=True, null=True)
    custo_pecas = models.DecimalField(
        _('Custo Peças (R$)'), max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    custo_mao_obra = models.DecimalField(
        _('Custo Mão de Obra (R$)'), max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    odometro = models.DecimalField(
        _('Odômetro'), max_digits=10, decimal_places=1,
        blank=True, null=True, validators=[MinValueValidator(Decimal('0'))],
    )
    status_na_epoca = models.CharField(
        _('Status na época'), max_length=20, blank=True,
        choices=StatusManutencao.choices,
        help_text=_('Snapshot do status da manutenção no momento do registro'),
    )
    registrado_por = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='servicos_manutencao_registrados',
    )
    data_registro = models.DateTimeField(_('Data do Registro'), auto_now_add=True)

    class Meta:
        verbose_name = _('Serviço de Manutenção')
        verbose_name_plural = _('Serviços de Manutenção')
        ordering = ['-data_registro']
        constraints = [
            models.CheckConstraint(
                check=models.Q(custo_pecas__gte=0),
                name='ck_servico_manut_custo_pecas_positivo',
            ),
            models.CheckConstraint(
                check=models.Q(custo_mao_obra__gte=0),
                name='ck_servico_manut_custo_mao_obra_positivo',
            ),
        ]
        indexes = [
            models.Index(
                fields=['manutencao', '-data_registro'],
                name='idx_servico_manut_data',
            ),
        ]

    def __str__(self):
        resumo = self.descricao[:60] + ('…' if len(self.descricao) > 60 else '')
        return f"Serviço — {self.manutencao.viatura.prefixo}: {resumo}"

    @property
    def custo_total(self):
        return self.custo_pecas + self.custo_mao_obra


class RegistroHistoricoManutencao(models.Model):
    """Linha do tempo append-only da manutenção (auditoria orientada a eventos)."""
    manutencao = models.ForeignKey(
        Manutencao, on_delete=models.CASCADE,
        related_name='registros_historico', verbose_name=_('Manutenção'),
    )
    tipo = models.CharField(
        _('Tipo de Evento'), max_length=20, choices=TipoEventoManutencao.choices,
    )
    titulo = models.CharField(_('Título'), max_length=200)
    descricao = models.TextField(_('Descrição'), blank=True)
    servico = models.ForeignKey(
        ServicoManutencao, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='eventos_historico', verbose_name=_('Serviço vinculado'),
    )
    metadados = models.JSONField(
        _('Metadados'), blank=True, null=True,
        help_text=_('Dados estruturados da alteração (campos, valores anteriores/novos)'),
    )
    registrado_por = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='historicos_manutencao_registrados',
    )
    data_registro = models.DateTimeField(_('Data do Registro'), auto_now_add=True)

    class Meta:
        verbose_name = _('Registro de Histórico de Manutenção')
        verbose_name_plural = _('Registros de Histórico de Manutenção')
        ordering = ['-data_registro']
        indexes = [
            models.Index(
                fields=['manutencao', '-data_registro'],
                name='idx_hist_manut_data',
            ),
            models.Index(fields=['tipo'], name='idx_hist_manut_tipo'),
        ]

    def __str__(self):
        return (
            f"{self.get_tipo_display()} — {self.manutencao.viatura.prefixo}"
            f" ({self.data_registro:%d/%m/%Y %H:%M})"
        )


class PlanoManutencaoPreventiva(models.Model):
    """Regras de manutenção preventiva por modelo de viatura (Fase 3)"""
    modelo = models.ForeignKey(
        ModeloViatura, on_delete=models.CASCADE,
        related_name='planos_preventivos',
    )
    descricao = models.CharField(
        _('Descrição do Serviço'), max_length=200,
        help_text='Ex: Troca de óleo, Revisão geral',
    )
    intervalo_km = models.PositiveIntegerField(
        _('Intervalo em Km'), null=True, blank=True,
        help_text='A cada quantos km realizar',
    )
    intervalo_dias = models.PositiveIntegerField(
        _('Intervalo em Dias'), null=True, blank=True,
        help_text='A cada quantos dias realizar',
    )
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Plano de Manutenção Preventiva')
        verbose_name_plural = _('Planos de Manutenção Preventiva')
        ordering = ['modelo__marca__nome', 'modelo__nome', 'descricao']
        indexes = [
            models.Index(
                fields=['modelo', 'ativo'],
                name='idx_plano_prev_modelo_ativo',
            ),
        ]

    def __str__(self):
        partes = [self.descricao]
        if self.intervalo_km:
            partes.append(f"a cada {self.intervalo_km:,} km")
        if self.intervalo_dias:
            partes.append(f"a cada {self.intervalo_dias} dias")
        return f"{self.modelo} — {' / '.join(partes)}"


class DocumentoViatura(models.Model):
    """Documentos de viatura: CRLV, Seguro, IPVA, DPVAT, Vistoria, etc."""
    viatura = models.ForeignKey(
        Viatura, on_delete=models.CASCADE, related_name='documentos',
    )
    tipo = models.CharField(
        _('Tipo de Documento'), max_length=20, choices=TipoDocumento.choices,
    )
    numero_documento = models.CharField(
        _('Número do Documento'), max_length=100, blank=True,
    )
    data_emissao = models.DateField(_('Data de Emissão'), null=True, blank=True)
    data_vencimento = models.DateField(_('Data de Vencimento'), null=True, blank=True)
    arquivo = models.FileField(
        _('Arquivo Digital'), upload_to='viaturas/documentos/%Y/%m/',
        blank=True, null=True, help_text='PDF ou imagem do documento',
    )
    observacoes = models.TextField(_('Observações'), blank=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    registrado_por = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name=_('Registrado por'),
        related_name='documentos_registrados',
    )
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Documento de Viatura')
        verbose_name_plural = _('Documentos de Viatura')
        ordering = ['tipo', 'data_vencimento']
        unique_together = ['viatura', 'tipo', 'numero_documento']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(data_emissao__isnull=True)
                    | models.Q(data_vencimento__isnull=True)
                    | models.Q(data_vencimento__gte=models.F('data_emissao'))
                ),
                name='ck_documento_venc_apos_emissao',
            ),
        ]
        indexes = [
            models.Index(
                fields=['viatura', 'tipo'],
                name='idx_documento_viat_tipo',
            ),
            models.Index(
                fields=['data_vencimento'],
                name='idx_documento_vencimento',
            ),
        ]

    def __str__(self):
        venc = f" — vence em {self.data_vencimento:%d/%m/%Y}" if self.data_vencimento else ""
        return f"{self.get_tipo_display()}{venc} ({self.viatura.prefixo})"

    @property
    def status_vencimento(self):
        """Retorna status do documento baseado na data de vencimento."""
        if not self.data_vencimento:
            return 'INDETERMINADO'
        hoje = timezone.now().date()
        dias = (self.data_vencimento - hoje).days
        if dias < 0:
            return 'VENCIDO'
        elif dias <= 30:
            return 'EXPIRANDO'
        return 'VIGENTE'
