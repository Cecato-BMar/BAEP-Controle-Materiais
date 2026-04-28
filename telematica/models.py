from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.utils import timezone

class CategoriaEquipamento(models.Model):
    """Categorias de equipamentos de TI e Comunicação (ex: PC, Rádio, Celular)"""
    nome = models.CharField(_('Nome da Categoria'), max_length=50, unique=True)
    icone = models.CharField(_('Ícone (FontAwesome)'), max_length=50, default='fas fa-laptop')
    descricao = models.TextField(_('Descrição'), blank=True, null=True)

    class Meta:
        verbose_name = _('Categoria de Equipamento')
        verbose_name_plural = _('Categorias de Equipamentos')
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Equipamento(models.Model):
    """Cadastro principal de ativos de tecnologia do batalhão"""
    STATUS_CHOICES = [
        ('OPERACIONAL', 'Operacional / Em Uso'),
        ('RESERVA', 'Reserva Técnica'),
        ('MANUTENCAO', 'Em Manutenção'),
        ('BAIXADO', 'Baixado / Inativo'),
        ('EXTRAVIADO', 'Extraviado / Roubado'),
    ]

    categoria = models.ForeignKey(CategoriaEquipamento, on_delete=models.PROTECT, related_name='equipamentos')
    marca = models.CharField(_('Marca'), max_length=100)
    modelo = models.CharField(_('Modelo'), max_length=100)
    numero_serie = models.CharField(_('Nº de Série'), max_length=100, unique=True)
    patrimonio = models.CharField(_('Nº Patrimônio'), max_length=50, blank=True, null=True, unique=True)
    
    # Especificações de Hardware (Geral)
    processador = models.CharField(_('Processador'), max_length=100, blank=True, null=True)
    memoria_ram = models.CharField(_('Memória RAM'), max_length=50, blank=True, null=True)
    armazenamento = models.CharField(_('Armazenamento (HD/SSD)'), max_length=100, blank=True, null=True)
    sistema_operacional = models.CharField(_('Sistema Operacional'), max_length=100, blank=True, null=True)
    
    # Rede e IP
    hostname = models.CharField(_('Nome na Rede (Hostname)'), max_length=100, blank=True, null=True)
    endereco_ip = models.GenericIPAddressField(_('Endereço IP'), blank=True, null=True)
    endereco_mac = models.CharField(_('Endereço MAC'), max_length=17, blank=True, null=True)
    vlan = models.CharField(_('VLAN'), max_length=20, blank=True, null=True)
    porta_switch = models.CharField(_('Porta do Switch'), max_length=50, blank=True, null=True)
    
    # Localização
    setor = models.CharField(_('Setor/Seção'), max_length=100)
    usuario_responsavel = models.CharField(_('Usuário Principal'), max_length=150, blank=True, null=True)
    
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='OPERACIONAL')
    data_aquisicao = models.DateField(_('Data de Aquisição'), blank=True, null=True)
    vencimento_garantia = models.DateField(_('Vencimento da Garantia'), blank=True, null=True)
    
    observacoes = models.TextField(_('Observações Técnicas'), blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Equipamento')
        verbose_name_plural = _('Equipamentos')
        ordering = ['categoria', 'hostname', 'patrimonio']

    def __str__(self):
        return f"{self.categoria.nome} - {self.hostname or self.numero_serie} ({self.status})"

class ConfiguracaoRadio(models.Model):
    """Configurações específicas para Rádios (HT/Móveis/Fixos)"""
    equipamento = models.OneToOneField(Equipamento, on_delete=models.CASCADE, limit_choices_to={'categoria__nome__icontains': 'Rádio'}, related_name='config_radio')
    issi = models.CharField(_('ISSI'), max_length=50, unique=True, help_text="Identificação Individual no Sistema")
    tei = models.CharField(_('TEI'), max_length=50, blank=True, null=True, unique=True, help_text="Identificação do Equipamento")
    grupo_principal = models.CharField(_('Grupo de Conversação Principal'), max_length=100)
    criptografia_ativa = models.BooleanField(_('Criptografia Habilitada?'), default=True)
    versao_firmware = models.CharField(_('Versão de Firmware'), max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = _('Configuração de Rádio')
        verbose_name_plural = _('Configurações de Rádios')

    def __str__(self):
        return f"Rádio ISSI: {self.issi}"

class LinhaMovel(models.Model):
    """Gerenciamento de chips e linhas para celulares, tablets e TPDS"""
    numero = models.CharField(_('Número do Telefone'), max_length=20, unique=True)
    operadora = models.CharField(_('Operadora'), max_length=50)
    iccid = models.CharField(_('ICCID (Nº do Chip)'), max_length=30, unique=True)
    imei_1 = models.CharField(_('IMEI 1'), max_length=20, blank=True, null=True)
    imei_2 = models.CharField(_('IMEI 2'), max_length=20, blank=True, null=True)
    plano_dados = models.CharField(_('Plano/Cota de Dados'), max_length=100, blank=True, null=True)
    equipamento_vinculado = models.OneToOneField(Equipamento, on_delete=models.SET_NULL, null=True, blank=True, related_name='linha_movel')
    policial_responsavel = models.ForeignKey('policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True, related_name='linhas_telematica')
    ativo = models.BooleanField(_('Ativo'), default=True)

    class Meta:
        verbose_name = _('Linha Móvel')
        verbose_name_plural = _('Linhas Móveis')

    def __str__(self):
        return f"{self.numero} ({self.operadora})"

class ServicoTI(models.Model):
    """Serviços de rede e infraestrutura (Internet, Links, VPN, Servidores Cloud)"""
    TIPO_CHOICES = [
        ('INTERNET', 'Link de Internet'),
        ('VPN', 'VPN / Acesso Remoto'),
        ('SISTEMA', 'Sistema Corporativo'),
        ('STORAGE', 'Backup / Armazenamento'),
        ('REDE', 'Infraestrutura de Rede'),
    ]
    
    nome = models.CharField(_('Nome do Serviço'), max_length=100)
    tipo = models.CharField(_('Tipo'), max_length=20, choices=TIPO_CHOICES)
    fornecedor = models.CharField(_('Fornecedor/Órgão'), max_length=150)
    descricao = models.TextField(_('Descrição Técnica'))
    numero_contrato = models.CharField(_('Nº Contrato/Protocolo'), max_length=100, blank=True, null=True)
    vencimento = models.DateField(_('Data de Vencimento/Renovação'), blank=True, null=True)
    status = models.BooleanField(_('Em Operação?'), default=True)
    
    # Detalhes de Conexão
    ip_publico = models.GenericIPAddressField(_('IP Público/Gateway'), blank=True, null=True)
    velocidade = models.CharField(_('Velocidade/Capacidade'), max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = _('Serviço de TI')
        verbose_name_plural = _('Serviços de TI')

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.nome}"

from django.db.models.signals import post_save
from django.dispatch import receiver

class ManutencaoTI(models.Model):
    """Registro de manutenções e suportes técnicos"""
    TIPO_MANUTENCAO = [
        ('PREVENTIVA', 'Preventiva'),
        ('CORRETIVA', 'Corretiva / Reparo'),
        ('UPGRADE', 'Upgrade / Melhoria'),
        ('SOFTWARE', 'Instalação/Configuração Software'),
    ]
    
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='manutencoes_ti')
    tipo = models.CharField(_('Tipo de Manutenção'), max_length=20, choices=TIPO_MANUTENCAO)
    data_inicio = models.DateTimeField(_('Início'), default=timezone.now)
    data_fim = models.DateTimeField(_('Fim'), blank=True, null=True)
    descricao_problema = models.TextField(_('Descrição do Problema / Solicitação'))
    solucao_tecnica = models.TextField(_('Solução Aplicada'), blank=True, null=True)
    tecnico_responsavel = models.CharField(_('Técnico Responsável'), max_length=150)
    custo = models.DecimalField(_('Custo (R$)'), max_digits=10, decimal_places=2, default=0)
    concluida = models.BooleanField(_('Concluída?'), default=False)
    
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _('Manutenção de TI')
        verbose_name_plural = _('Manutenções de TI')
        ordering = ['-data_inicio']

    def __str__(self):
        return f"MNT {self.equipamento.hostname or self.equipamento.numero_serie} - {self.data_inicio.strftime('%d/%m/%Y')}"

@receiver(post_save, sender=ManutencaoTI)
def sync_equipamento_status(sender, instance, **kwargs):
    """Sincroniza o status do equipamento baseado na conclusão da manutenção"""
    equipamento = instance.equipamento
    if not instance.concluida:
        if equipamento.status != 'MANUTENCAO':
            equipamento.status = 'MANUTENCAO'
            equipamento.save(update_fields=['status'])
    else:
        # Se a manutenção foi concluída, verifica se não há outras em aberto
        outras_pendentes = ManutencaoTI.objects.filter(equipamento=equipamento, concluida=False).exists()
        if not outras_pendentes and equipamento.status == 'MANUTENCAO':
            equipamento.status = 'OPERACIONAL'
            equipamento.save(update_fields=['status'])
