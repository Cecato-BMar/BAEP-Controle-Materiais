"""
Material Bélico — Models do módulo de Controle de Material Bélico do 2º BAEP.
Abrange: armas de fogo, acessórios, kits operacionais, comunicação,
equipamentos não letais, munições, proteção balística e auditoria.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
try:
    from simple_history.models import HistoricalRecords
    _HAS_HISTORY = True
except ImportError:
    _HAS_HISTORY = False

    class HistoricalRecords:
        """Stub quando simple_history nao esta instalado."""
        pass

# =============================================================================
# LOCALIZAÇÕES COMPARTILHADAS
# =============================================================================

LOCALIZACAO_FUZIL_CHOICES = [
    ('KIT-01', 'KIT-01'), ('KIT-02', 'KIT-02'), ('KIT-03', 'KIT-03'),
    ('KIT-04', 'KIT-04'), ('KIT-05', 'KIT-05'), ('KIT-06', 'KIT-06'),
    ('KIT-07', 'KIT-07'), ('KIT-08', 'KIT-08'), ('KIT-09', 'KIT-09'),
    ('KIT-10', 'KIT-10'), ('KIT-11', 'KIT-11'), ('KIT-12', 'KIT-12'),
    ('RESERVA', 'Reserva'), ('CMT', 'Comandante'), ('SUBCMT', 'Subcomandante'),
    ('AT-01', 'AT-01'), ('AT-02', 'AT-02'), ('AT-03', 'AT-03'), ('AT-04', 'AT-04'),
    ('S-01', 'S-01'), ('S-02', 'S-02'), ('S-03', 'S-03'),
    ('3ª CIA', '3ª CIA'), ('CURSO', 'Curso'), ('P2', 'P2'), ('GUARDA', 'Guarda'),
]

STATUS_ARMA_CHOICES = [
    ('OK', 'OK'),
    ('EM_USO', 'Em Uso'),
    ('BAIXADO', 'Baixado'),
    ('SINDICANCIA', 'Sindicância'),
    ('MANUTENCAO', 'Manutenção'),
]

KIT_ESPINGARDA_CHOICES = [(str(i), f'KIT-{i:02d}') for i in range(1, 13)] + \
    [('S1', 'S1'), ('S2', 'S2'), ('S3', 'S3'), ('S4', 'S4'),
     ('S5', 'S5'), ('S6', 'S6'), ('S7', 'S7'),
     ('x', 'Sem Kit (x)'), ('xx', 'Sem Kit (xx)'),
     ('xxx', 'Sem Kit (xxx)'), ('xxxx', 'Sem Kit (xxxx)')]

# =============================================================================
# 1. ARMAS DE FOGO
# =============================================================================


class Fuzil(models.Model):
    """Fuzis: SCAR CAL.762, SCAR CAL.556, IMBEL IA2 CAL.556"""
    TIPO_CHOICES = [
        ('SCAR_762', 'SCAR CAL.762'),
        ('SCAR_556', 'SCAR CAL.556'),
        ('IMBEL_IA2', 'IMBEL IA2 CAL.556'),
    ]
    tipo = models.CharField(_('Tipo'), max_length=20, choices=TIPO_CHOICES)
    patrimonio = models.CharField(_('Patrimônio'), max_length=30, unique=True)
    localizacao = models.CharField(_('Localização'), max_length=20, choices=LOCALIZACAO_FUZIL_CHOICES)
    numero_recibo = models.CharField(_('Nº Recibo'), max_length=50, blank=True, null=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_ARMA_CHOICES, default='OK')
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(_('Data de Cadastro'), auto_now_add=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Fuzil')
        verbose_name_plural = _('Fuzis')
        ordering = ['tipo', 'patrimonio']

    def __str__(self):
        return f"{self.get_tipo_display()} — Pat. {self.patrimonio}"

    @property
    def pode_alocar_kit(self):
        """RN-02: Armas em SINDICÂNCIA não podem ser alocadas a kits."""
        return self.status != 'SINDICANCIA' and self.status != 'BAIXADO'


class EspingardaCal12(models.Model):
    """Espingardas Calibre 12"""
    STATUS_CHOICES = [('OK', 'OK'), ('EM_USO', 'Em Uso'), ('BAIXADO', 'Baixado'), ('MANUTENCAO', 'Manutenção')]
    numero_espingarda = models.CharField(_('Número da Espingarda'), max_length=30, unique=True)
    patrimonio = models.CharField(_('Patrimônio'), max_length=30, blank=True, null=True)
    kit_vinculado = models.CharField(_('Kit Vinculado'), max_length=10, choices=KIT_ESPINGARDA_CHOICES, blank=True, null=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='OK')
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Espingarda Cal.12')
        verbose_name_plural = _('Espingardas Cal.12')
        ordering = ['numero_espingarda']

    def __str__(self):
        return f"Espingarda {self.numero_espingarda}"


class PistolaGlock(models.Model):
    """Pistolas Glock G22 G5 .40"""
    SITUACAO_CHOICES = [
        ('ok', 'OK'),
        ('EM_USO', 'Em Uso'),
        ('APREENDIDA', 'Apreendida'),
        ('NOVIDADE', 'Novidade'),
    ]
    patrimonio = models.CharField(_('Patrimônio'), max_length=30, blank=True, null=True)
    numero_serie = models.CharField(_('Número de Série'), max_length=30, unique=True)
    modelo = models.CharField(_('Modelo'), max_length=60, default='PISTOLA GLOCK G22 G5 .40')
    cod_opm = models.CharField(_('Cód. OPM'), max_length=20, blank=True, null=True)
    unidade = models.CharField(_('Unidade'), max_length=20, default='2.BAEP')
    situacao_reserva = models.CharField(_('Situação na Reserva'), max_length=20, choices=SITUACAO_CHOICES, default='ok')
    numero_bopm = models.CharField(_('Nº BOPM'), max_length=50, blank=True, null=True,
                                   help_text=_('Obrigatório se apreendida (RN-02)'))
    numero_bopc = models.CharField(_('Nº BOPC'), max_length=50, blank=True, null=True)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Pistola Glock')
        verbose_name_plural = _('Pistolas Glock')
        ordering = ['numero_serie']

    def __str__(self):
        return f"Glock — Série {self.numero_serie}"

    def clean(self):
        """RN-02: Armas apreendidas devem registrar BOPM e BOPC obrigatoriamente."""
        super().clean()
        if self.situacao_reserva == 'APREENDIDA':
            if not self.numero_bopm or not self.numero_bopc:
                raise ValidationError(_('Armas apreendidas devem informar BOPM e BOPC (RN-02).'))


class PistolaTaurus(models.Model):
    """Pistolas Taurus: 24/7, PT100, 640"""
    MODELO_CHOICES = [
        ('TAURUS_24_7', 'PISTOLA TAURUS 24/7'),
        ('TAURUS_PT100', 'PISTOLA TAURUS PT100'),
        ('TAURUS_640', 'PISTOLA TAURUS 640'),
    ]
    patrimonio = models.CharField(_('Patrimônio'), max_length=30, blank=True, null=True)
    numero_serie = models.CharField(_('Número de Série'), max_length=30, unique=True)
    modelo = models.CharField(_('Modelo'), max_length=30, choices=MODELO_CHOICES)
    unidade = models.CharField(_('Unidade'), max_length=20, default='2.BAEP')
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Pistola Taurus')
        verbose_name_plural = _('Pistolas Taurus')
        ordering = ['numero_serie']

    def __str__(self):
        return f"{self.get_modelo_display()} — Série {self.numero_serie}"


class ArmaTransferenciaPendente(models.Model):
    """Armas na Reserva — Transferências Pendentes (aba PST TRANSF)"""
    ESPECIE_CHOICES = [('PISTOLA', 'Pistola'), ('REVOLVER', 'Revólver')]
    TIPO_VINCULO_CHOICES = [('POLICIAL', 'Policial'), ('PAISANO', 'Paisano')]
    SITUACAO_CHOICES = [
        ('FALECIDO', 'Falecido'), ('EXPULSO', 'Expulso'),
        ('BAIXA', 'Baixa'), ('TRANSFERENCIA', 'Transferência'),
    ]
    STATUS_CHOICES = [('PARADO', 'Parado'), ('INICIADO', 'Iniciado')]

    especie = models.CharField(_('Espécie'), max_length=20, choices=ESPECIE_CHOICES)
    marca = models.CharField(_('Marca'), max_length=50)
    modelo = models.CharField(_('Modelo'), max_length=100)
    calibre = models.CharField(_('Calibre'), max_length=20)
    numero_serie = models.CharField(_('Número de Série'), max_length=50)
    nome_policial = models.CharField(_('Nome do Policial'), max_length=150)
    tipo_vinculo = models.CharField(_('Tipo de Vínculo'), max_length=20, choices=TIPO_VINCULO_CHOICES)
    re_policial = models.CharField(_('RE do Policial'), max_length=20, blank=True, null=True)
    situacao = models.CharField(_('Situação'), max_length=20, choices=SITUACAO_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='PARADO')
    intencao_venda_nome = models.CharField(_('Intenção de Venda — Nome'), max_length=150, blank=True, null=True)
    intencao_venda_re = models.CharField(_('Intenção de Venda — RE'), max_length=20, blank=True, null=True)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Transferência Pendente')
        verbose_name_plural = _('Transferências Pendentes')
        ordering = ['-data_cadastro']

    def __str__(self):
        return f"{self.especie} {self.marca} {self.modelo} — {self.nome_policial}"


# =============================================================================
# 2. ACESSÓRIOS DE FUZIL
# =============================================================================


class RedDot(models.Model):
    """Red Dot — acessório de fuzil"""
    STATUS_CHOICES = [('OK', 'OK')]
    patrimonio = models.CharField(_('Patrimônio'), max_length=30, unique=True)
    localizacao = models.CharField(_('Localização'), max_length=20, choices=LOCALIZACAO_FUZIL_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='OK')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Red Dot')
        verbose_name_plural = _('Red Dots')
        ordering = ['patrimonio']

    def __str__(self):
        return f"Red Dot — Pat. {self.patrimonio}"


class Magnificador(models.Model):
    """Magnificador — acessório de fuzil"""
    STATUS_CHOICES = [('OK', 'OK'), ('SINDICANCIA', 'Sindicância')]
    patrimonio = models.CharField(_('Patrimônio'), max_length=30, unique=True)
    localizacao = models.CharField(_('Localização'), max_length=20, choices=LOCALIZACAO_FUZIL_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='OK')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Magnificador')
        verbose_name_plural = _('Magnificadores')
        ordering = ['patrimonio']

    def __str__(self):
        return f"Magnificador — Pat. {self.patrimonio}"


class Supressor(models.Model):
    """Supressor — acessório de fuzil (apenas AT-01 a AT-04)"""
    STATUS_CHOICES = [('OK', 'OK')]
    LOCALIZACAO_SUPRESSOR = [
        ('AT-01', 'AT-01'), ('AT-02', 'AT-02'),
        ('AT-03', 'AT-03'), ('AT-04', 'AT-04'),
    ]
    patrimonio = models.CharField(_('Patrimônio'), max_length=30, unique=True)
    localizacao = models.CharField(_('Localização'), max_length=20, choices=LOCALIZACAO_SUPRESSOR)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='OK')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Supressor')
        verbose_name_plural = _('Supressores')
        ordering = ['patrimonio']

    def __str__(self):
        return f"Supressor — Pat. {self.patrimonio}"


class VinculacaoAcessorioFuzil(models.Model):
    """Vinculação Arma–Acessório (RN-06: todo fuzil ativo deve ter vinculação explícita)"""
    fuzil = models.OneToOneField(Fuzil, on_delete=models.CASCADE, related_name='vinculacao_acessorios',
                                  verbose_name=_('Fuzil'))
    red_dot = models.ForeignKey(RedDot, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name=_('Red Dot'))
    magnificador = models.ForeignKey(Magnificador, on_delete=models.SET_NULL, null=True, blank=True,
                                      verbose_name=_('Magnificador'))
    supressor = models.ForeignKey(Supressor, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=_('Supressor'))
    numero_recibo_transferencia = models.CharField(_('Nº Recibo Transferência'), max_length=50, blank=True, null=True,
                                                    help_text=_('Recibo de transferência para 3ª CIA, se aplicável'))
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Vinculação Acessório–Fuzil')
        verbose_name_plural = _('Vinculações Acessório–Fuzil')

    def __str__(self):
        return f"Vinculação — {self.fuzil.patrimonio}"


# =============================================================================
# 3. KITS OPERACIONAIS
# =============================================================================


class KitOperacional(models.Model):
    """Kit Operacional — agrupa itens alocados a uma equipe (RN-01)"""
    NUMERO_KIT_CHOICES = [(str(i), f'KIT-{i:02d}') for i in range(1, 13)] + [
        ('CMT', 'Comandante'), ('SUBCMT', 'Subcomandante'),
        ('AT-01', 'AT-01'), ('AT-02', 'AT-02'), ('AT-03', 'AT-03'), ('AT-04', 'AT-04'),
        ('S-01', 'S-01'), ('S-02', 'S-02'), ('S-03', 'S-03'), ('GUARDA', 'Guarda'),
    ]
    numero_kit = models.CharField(_('Número do Kit'), max_length=10, choices=NUMERO_KIT_CHOICES, unique=True)
    fuzil_556_1 = models.ForeignKey(Fuzil, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='kit_556_1', verbose_name=_('Fuzil 5.56 (1º)'),
                                     limit_choices_to={'tipo__in': ['SCAR_556', 'IMBEL_IA2']})
    fuzil_556_2 = models.ForeignKey(Fuzil, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='kit_556_2', verbose_name=_('Fuzil 5.56 (2º)'),
                                     limit_choices_to={'tipo__in': ['SCAR_556', 'IMBEL_IA2']})
    fuzil_762 = models.ForeignKey(Fuzil, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='kit_762', verbose_name=_('Fuzil 7.62'),
                                   limit_choices_to={'tipo': 'SCAR_762'})
    espingarda = models.ForeignKey(EspingardaCal12, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='kit_espingarda', verbose_name=_('Espingarda Cal.12'))
    radio_ht = models.ForeignKey('RadioHT', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='kit_radio', verbose_name=_('Rádio HT'))
    am640 = models.ForeignKey('AM640', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='kit_am640', verbose_name=_('AM-640'))
    escudo = models.ForeignKey('EscudoBalistico', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='kit_escudo', verbose_name=_('Escudo Balístico'))
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Kit Operacional')
        verbose_name_plural = _('Kits Operacionais')
        ordering = ['numero_kit']

    def __str__(self):
        return f"Kit {self.numero_kit}"

    def clean(self):
        """RN-01: Validação de composição obrigatória do kit operacional."""
        super().clean()
        erros = {}
        # Kits padrão (KIT-01 a KIT-12) devem ter todos os itens obrigatórios
        if self.numero_kit and self.numero_kit.startswith('KIT-'):
            if not self.fuzil_556_1:
                erros['fuzil_556_1'] = _('Kit deve ter ao menos 1 fuzil CAL.556 (RN-01).')
            if not self.fuzil_762:
                erros['fuzil_762'] = _('Kit deve ter 1 fuzil SCAR CAL.762 (RN-01).')
            if not self.espingarda:
                erros['espingarda'] = _('Kit deve ter 1 espingarda CAL.12 (RN-01).')
            if not self.radio_ht:
                erros['radio_ht'] = _('Kit deve ter 1 rádio HT (RN-01).')
            if not self.am640:
                erros['am640'] = _('Kit deve ter 1 AM-640 (RN-01).')
            if not self.escudo:
                erros['escudo'] = _('Kit deve ter 1 escudo balístico (RN-01).')
        # RN-02: Armas em SINDICÂNCIA não podem ser alocadas
        for fuzil, campo in [(self.fuzil_556_1, 'fuzil_556_1'), (self.fuzil_556_2, 'fuzil_556_2'),
                             (self.fuzil_762, 'fuzil_762')]:
            if fuzil and not fuzil.pode_alocar_kit:
                erros[campo] = _(f'{fuzil.patrimonio} está em SINDICÂNCIA/BAIXADO e não pode ser alocado (RN-02).')
        if erros:
            raise ValidationError(erros)


# =============================================================================
# 4. EQUIPAMENTOS DE COMUNICAÇÃO
# =============================================================================


class RadioHT(models.Model):
    """Rádios HT Motorola APX 2000"""
    SITUACAO_CHOICES = [('OP', 'Operacional'), ('EM_USO', 'Em Uso'), ('MANUTENCAO', 'Manutenção')]
    patrimonio = models.CharField(_('Patrimônio'), max_length=30, unique=True)
    serie = models.CharField(_('Série'), max_length=50, unique=True)
    kit_vinculado = models.CharField(_('Kit Vinculado'), max_length=50, blank=True, null=True,
                                      help_text=_('Nº do kit ou descrição especial'))
    situacao = models.CharField(_('Situação'), max_length=20, choices=SITUACAO_CHOICES, default='OP')
    chamado_dtic = models.CharField(_('Chamado DTIC'), max_length=50, blank=True, null=True)
    data_chamado_dtic = models.DateField(_('Data do Chamado'), blank=True, null=True)
    controle_bateria_numero = models.PositiveIntegerField(_('Controle Bateria Nº'), blank=True, null=True)
    controle_bateria_localizacao = models.CharField(_('Localização Bateria'), max_length=100, blank=True, null=True)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Rádio HT')
        verbose_name_plural = _('Rádios HT')
        ordering = ['patrimonio']

    def __str__(self):
        return f"HT — Série {self.serie}"


class AM640(models.Model):
    """AM-640"""
    SITUACAO_CHOICES = [(f'KIT-{i:02d}', f'KIT-{i:02d}') for i in range(1, 11)] + [
        ('RESERVA', 'Reserva'), ('CMT', 'Comandante'), ('EM_USO', 'Em Uso'), ('BAIXADO', 'Baixado'),
    ]
    serie = models.CharField(_('Série'), max_length=50, unique=True)
    situacao = models.CharField(_('Situação'), max_length=20, choices=SITUACAO_CHOICES, default='RESERVA')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('AM-640')
        verbose_name_plural = _('AM-640')
        ordering = ['serie']

    def __str__(self):
        return f"AM-640 — Série {self.serie}"


class AM600(models.Model):
    """AM-600 — situação fixa: DESCARGA"""
    serie = models.CharField(_('Série'), max_length=50, unique=True)
    situacao = models.CharField(_('Situação'), max_length=20, default='DESCARGA', editable=False)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('AM-600')
        verbose_name_plural = _('AM-600')
        ordering = ['serie']

    def __str__(self):
        return f"AM-600 — Série {self.serie}"


class MosquetaoFederal(models.Model):
    """Mosquetão Federal 201/Z — situação fixa: DESCARGA"""
    serie = models.CharField(_('Série'), max_length=50, unique=True)
    situacao = models.CharField(_('Situação'), max_length=20, default='DESCARGA', editable=False)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Mosquetão Federal 201/Z')
        verbose_name_plural = _('Mosquetões Federal 201/Z')
        ordering = ['serie']

    def __str__(self):
        return f"Mosquetão — Série {self.serie}"


# =============================================================================
# 5. EQUIPAMENTOS NÃO LETAIS
# =============================================================================


class TASER(models.Model):
    """TASER — Controle de carga de bateria (RN-07)"""
    serie = models.CharField(_('Série'), max_length=50, unique=True)
    situacao = models.CharField(_('Situação'), max_length=30, default='RESERVA')
    carga_bateria_percent = models.PositiveIntegerField(_('Carga da Bateria (%)'), default=100,
                                                         validators=[MinValueValidator(0), MaxValueValidator(100)])
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('TASER')
        verbose_name_plural = _('TASER')
        ordering = ['serie']

    def __str__(self):
        return f"TASER — Série {self.serie}"

    @property
    def alerta_bateria(self):
        """RN-07: Carga abaixo de 50% gera alerta de recarga."""
        return self.carga_bateria_percent < 50

    @property
    def bloqueado_operacao(self):
        """RN-07: Carga 0% bloqueia alocação para operação."""
        return self.carga_bateria_percent == 0


class Algemas(models.Model):
    """Algemas — embalagem fixa PMESP"""
    numero = models.CharField(_('Número'), max_length=30, unique=True)
    embalagem = models.CharField(_('Embalagem'), max_length=20, default='PMESP', editable=False)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Algemas')
        verbose_name_plural = _('Algemas')
        ordering = ['numero']

    def __str__(self):
        return f"Algemas — Nº {self.numero}"


class MunicaoQuimica(models.Model):
    """Munições Químicas (não letais) — RN-03 controle de validade"""
    TIPO_CHOICES = [
        ('GL-201', 'GL-201'), ('GL-203L', 'GL-203L'), ('GL-303', 'GL-303'),
        ('GL-304', 'GL-304'), ('GL-307', 'GL-307'), ('GL-300T', 'GL-300T'),
        ('GL-300TH', 'GL-300TH'), ('GL_CS_40mm', 'GL CS 40mm'),
        ('GR_HG_CCS_60C', 'GR HG CCS 60C'), ('AM-403P', 'AM-403P'),
        ('OC_AEROSOL', 'OC Aerosol OC-V 6340'),
        ('FLASH_BANG', 'Granada Flash Bang 7290'),
        ('ESPARG_80', 'Espargidor Pimenta 80ml'),
        ('ESPARG_400', 'Espargidor Pimenta 400ml'),
        ('NRSC_GRANADA', '8909 NRSC Granada'),
    ]
    tipo_municao = models.CharField(_('Tipo de Munição'), max_length=30, choices=TIPO_CHOICES)
    qtd_armario = models.PositiveIntegerField(_('Qtd. Armário'), default=0)
    qtd_kto = models.PositiveIntegerField(_('Qtd. KTO'), default=0)
    qtd_bornal = models.PositiveIntegerField(_('Qtd. Bornal'), default=0)
    qtd_vencidas = models.PositiveIntegerField(_('Qtd. Vencidas'), default=0)
    validade_prazo = models.DateField(_('Validade'), blank=True, null=True)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Munição Química')
        verbose_name_plural = _('Munições Químicas')
        ordering = ['tipo_municao']

    def __str__(self):
        return f"{self.get_tipo_municao_display()}"

    @property
    def total(self):
        """Total calculado: armário + KTO + bornal."""
        return (self.qtd_armario or 0) + (self.qtd_kto or 0) + (self.qtd_bornal or 0)

    @property
    def vencida(self):
        """RN-03: Munições químicas vencidas devem gerar alerta."""
        if self.validade_prazo:
            return self.validade_prazo < timezone.now().date()
        return False


# =============================================================================
# 6. MUNIÇÕES CONVENCIONAIS
# =============================================================================


class MunicaoConvencional(models.Model):
    """Munições Convencionais — RN-05 controle detalhado"""
    CALIBRE_CHOICES = [('.40', 'Calibre .40'), ('.556', 'Calibre .556'),
                       ('.762', 'Calibre .762'), ('.12', 'Calibre .12')]
    SUBTIPO_CHOICES = [
        ('EXPO', 'EXPO'), ('ETPP', 'ETPP'), ('SS109', 'SS109'), ('SAT', 'SAT'),
        ('TREINA', 'Treinamento'), ('TRACANTE', 'Traçante'), ('FESTIM', 'Festim'),
        ('OP', 'OP'), ('AP', 'AP'), ('BALOTE', 'Balote'), ('SG', 'SG'), ('3T', '3T'),
    ]
    SECAO_CHOICES = [('RESERVA', 'Reserva'), ('CURSOS', 'Cursos')]

    calibre = models.CharField(_('Calibre'), max_length=10, choices=CALIBRE_CHOICES)
    subtipo = models.CharField(_('Subtipo'), max_length=20, choices=SUBTIPO_CHOICES)
    secao = models.CharField(_('Seção'), max_length=20, choices=SECAO_CHOICES, default='RESERVA')
    em_uso = models.PositiveIntegerField(_('Em Uso'), default=0,
                                          help_text=_('Somatório das cotas dos kits ativos (RN-05)'))
    estoque = models.PositiveIntegerField(_('Estoque'), default=0,
                                           help_text=_('Total geral - em uso - manuseadas - danificadas'))
    manuseadas = models.PositiveIntegerField(_('Manuseadas'), default=0)
    capsulas = models.PositiveIntegerField(_('Cápsulas (Estojos)'), default=0,
                                            help_text=_('Contabilizadas separadamente (RN-05)'))
    danificado = models.PositiveIntegerField(_('Danificado'), default=0)
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Munição Convencional')
        verbose_name_plural = _('Munições Convencionais')
        ordering = ['calibre', 'subtipo']
        unique_together = ['calibre', 'subtipo', 'secao']

    def __str__(self):
        return f"{self.calibre} {self.subtipo} — {self.secao}"

    @property
    def total(self):
        """Total calculado: em_uso + estoque + manuseadas + danificado."""
        return (self.em_uso or 0) + (self.estoque or 0) + (self.manuseadas or 0) + (self.danificado or 0)


class DistribuicaoMunicaoKit(models.Model):
    """Distribuição de munições por kit operacional — cotas padrão (RN-01/RN-05)"""
    kit = models.ForeignKey(KitOperacional, on_delete=models.CASCADE,
                             related_name='distribuicoes_municao', verbose_name=_('Kit Operacional'))
    calibre = models.CharField(_('Calibre'), max_length=10, choices=MunicaoConvencional.CALIBRE_CHOICES)
    subtipo = models.CharField(_('Subtipo'), max_length=20, choices=MunicaoConvencional.SUBTIPO_CHOICES)
    quantidade_cota = models.PositiveIntegerField(_('Quantidade (Cota)'), default=0)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Distribuição de Munição por Kit')
        verbose_name_plural = _('Distribuições de Munição por Kit')
        unique_together = ['kit', 'calibre', 'subtipo']

    def __str__(self):
        return f"{self.kit} — {self.calibre} {self.subtipo} ({self.quantidade_cota})"


# =============================================================================
# 7. EQUIPAMENTOS DE PROTEÇÃO
# =============================================================================


class ColeteBalistico(models.Model):
    """Coletes Balísticos — RN-03 controle de validade"""
    MARCA_CHOICES = [
        ('PROTECOP', 'PROTECOP'), ('KAVRO', 'KAVRO'),
        ('INBRATERRESTRE', 'INBRATERRESTRE'),
    ]
    SITUACAO_CHOICES = [
        ('DISPONIVEL', 'Disponível'), ('EM_USO', 'Em Uso'), ('SINDICANCIA', 'Sindicância'),
    ]
    marca = models.CharField(_('Marca'), max_length=30, choices=MARCA_CHOICES)
    tamanho = models.CharField(_('Tamanho'), max_length=30)
    patrimonio = models.CharField(_('Patrimônio'), max_length=30, blank=True, null=True)
    numero_serie = models.CharField(_('Número de Série'), max_length=50)
    situacao = models.CharField(_('Situação'), max_length=20, choices=SITUACAO_CHOICES, default='DISPONIVEL')
    obs = models.TextField(_('Observações'), blank=True, null=True)
    validade_descricao = models.CharField(_('Validade'), max_length=50,
                                           help_text=_('Ex: 7 ANOS FAB2023'))
    ano_fabricacao = models.PositiveIntegerField(_('Ano de Fabricação'), blank=True, null=True)
    anos_validade = models.PositiveIntegerField(_('Anos de Validade'), blank=True, null=True,
                                                 help_text=_('Ex: 7 para "7 ANOS FAB2023"'))
    tem_capa = models.BooleanField(_('Tem Capa'), default=False)
    obs_adicional = models.TextField(_('Obs. Adicional'), blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Colete Balístico')
        verbose_name_plural = _('Coletes Balísticos')
        ordering = ['numero_serie']

    def __str__(self):
        return f"Colete {self.marca} — {self.numero_serie}"

    @property
    def validade_vencida(self):
        """RN-03: Calcula vencimento a partir de FAB + anos de validade."""
        if self.ano_fabricacao and self.anos_validade:
            from datetime import date
            vencimento = date(self.ano_fabricacao + self.anos_validade, 12, 31)
            return vencimento < timezone.now().date()
        return False


class EscudoBalistico(models.Model):
    """Escudos Balísticos — RN-03 alerta de validade"""
    SITUACAO_CHOICES = [('OP', 'Operacional'), ('EM_USO', 'Em Uso'), ('BXA', 'Baixado')]
    LOTE_CHOICES = [('1cia', '1ª CIA'), ('2cia', '2ª CIA'), ('EM', 'EM')]

    numero = models.PositiveIntegerField(_('Número'), unique=True)
    material = models.CharField(_('Material'), max_length=100,
                                 default='ESCUDO BALISTICO EM ARAMIDA / NIVEL I')
    numero_serie = models.CharField(_('Número de Série'), max_length=50, blank=True, null=True)
    fabricacao = models.DateField(_('Data de Fabricação'), blank=True, null=True)
    validade = models.DateField(_('Validade'), blank=True, null=True)
    patrimonio = models.CharField(_('Patrimônio'), max_length=30, blank=True, null=True)
    localizacao = models.CharField(_('Localização'), max_length=50, default='RESERVA DE ARMAS')
    lote_companhia = models.CharField(_('Lote/Cia'), max_length=10, choices=LOTE_CHOICES, blank=True, null=True)
    situacao = models.CharField(_('Situação'), max_length=10, choices=SITUACAO_CHOICES, default='OP')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Escudo Balístico')
        verbose_name_plural = _('Escudos Balísticos')
        ordering = ['numero']

    def __str__(self):
        return f"Escudo Nº {self.numero}"

    @property
    def alerta_validade(self):
        """RN-03: Escudos com validade vencida mantêm status OP com flag de alerta."""
        if self.validade:
            return self.validade < timezone.now().date()
        return False


class CapaceteBalistico(models.Model):
    """Capacetes Balísticos — RN-03 alerta de validade"""
    MATERIAL_CHOICES = [
        ('COM_VISOR', 'CAP BAL NIVEL II C VISOR'),
        ('SEM_VISOR', 'CAP BAL NIVEL II S VISOR'),
    ]
    CONDICAO_CHOICES = [('OPERANDO', 'Operando'), ('EM_USO', 'Em Uso'), ('DANIFICADO', 'Danificado')]

    numero = models.PositiveIntegerField(_('Número'), unique=True)
    material = models.CharField(_('Material'), max_length=50, choices=MATERIAL_CHOICES)
    numero_serie = models.CharField(_('Número de Série'), max_length=50, blank=True, null=True)
    patrimonio = models.CharField(_('Patrimônio'), max_length=30, blank=True, null=True)
    fabricacao = models.DateField(_('Data de Fabricação'), blank=True, null=True)
    validade = models.CharField(_('Validade'), max_length=30, blank=True, null=True,
                                 help_text=_('Data ou "VENCIDO"'))
    localizacao = models.CharField(_('Localização'), max_length=50, default='RESERVA DE ARMAS')
    condicao = models.CharField(_('Condição'), max_length=20, choices=CONDICAO_CHOICES, default='OPERANDO')
    lote_companhia = models.CharField(_('Lote/Cia'), max_length=30, blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Capacete Balístico')
        verbose_name_plural = _('Capacetes Balísticos')
        ordering = ['numero']

    def __str__(self):
        return f"Capacete Nº {self.numero}"

    @property
    def alerta_validade(self):
        """RN-03: Capacetes com validade VENCIDO mantêm status OPERANDO com alerta."""
        return self.validade and self.validade.upper() == 'VENCIDO'


# =============================================================================
# 8. AUDITORIA
# =============================================================================


class AuditoriaMaterialBelico(models.Model):
    """Log de auditoria — RN-08: Histórico de alterações"""
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Usuário'),
                                 related_name='auditoria_material_belico')
    re_usuario = models.CharField(_('RE do Usuário'), max_length=20, blank=True, null=True)
    entidade = models.CharField(_('Entidade'), max_length=100)
    objeto_id = models.PositiveIntegerField(_('ID do Objeto'))
    campo_alterado = models.CharField(_('Campo Alterado'), max_length=100)
    valor_anterior = models.TextField(_('Valor Anterior'), blank=True, null=True)
    valor_novo = models.TextField(_('Valor Novo'), blank=True, null=True)
    data_hora = models.DateTimeField(_('Data/Hora'), auto_now_add=True)

    class Meta:
        verbose_name = _('Auditoria Material Bélico')
        verbose_name_plural = _('Auditorias Material Bélico')
        ordering = ['-data_hora']

    def __str__(self):
        return f"{self.data_hora.strftime('%d/%m/%Y %H:%M')} — {self.entidade} — {self.campo_alterado}"
