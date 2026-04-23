from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator

class MarcaViatura(models.Model):
    """Marcas de Viaturas (Ex: Toyota, Yamaha, Chevrolet)"""
    nome = models.CharField(_('Nome da Marca'), max_length=50, unique=True)
    ativo = models.BooleanField(_('Ativo'), default=True)

    class Meta:
        verbose_name = _('Marca')
        verbose_name_plural = _('Marcas')
        ordering = ['nome']

    def __str__(self):
        return self.nome

class ModeloViatura(models.Model):
    """Modelos atrelados às marcas (Ex: Hilux, XT 660)"""
    TIPO_CHOICES = [
        ('4_RODAS', 'Quatro Rodas (Carro/SUV/Pick-up)'),
        ('MOTO', 'Motocicleta'),
        ('EMBARCACAO', 'Embarcação'),
        ('CAMINHAO', 'Caminhão/Micro-ônibus'),
    ]
    
    marca = models.ForeignKey(MarcaViatura, on_delete=models.PROTECT, related_name='modelos')
    nome = models.CharField(_('Nome do Modelo'), max_length=100)
    tipo = models.CharField(_('Tipo de Viatura'), max_length=20, choices=TIPO_CHOICES)
    ativo = models.BooleanField(_('Ativo'), default=True)

    class Meta:
        verbose_name = _('Modelo')
        verbose_name_plural = _('Modelos')
        ordering = ['marca__nome', 'nome']

    def __str__(self):
        return f"{self.marca.nome} {self.nome} ({self.get_tipo_display()})"

class Viatura(models.Model):
    """Cadastro principal da viatura física"""
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível (Pronta para uso)'),
        ('EM_USO', 'Em Uso (Despachada)'),
        ('MANUTENCAO', 'Em Manutenção/Oficina'),
        ('BAIXADA', 'Baixada/Inativa'),
    ]
    
    COMBUSTIVEL_CHOICES = [
        ('FLEX', 'Flex (Álcool/Gasolina)'),
        ('GASOLINA', 'Gasolina'),
        ('ALCOOL', 'Etanol'),
        ('DIESEL', 'Diesel'),
        ('ELETRICO', 'Elétrico (kWh)'),
        ('OUTRO', 'Outro'),
    ]

    prefixo = models.CharField(_('Prefixo da Viatura'), max_length=20, unique=True, help_text="Ex: E-10201")
    placa = models.CharField(_('Placa'), max_length=15, blank=True, null=True, unique=True)
    chassi = models.CharField(_('Chassi/Nº de Série'), max_length=100, blank=True, null=True)
    renavam = models.CharField(_('RENAVAM'), max_length=30, blank=True, null=True)
    numero_patrimonio = models.CharField(_('Nº Patrimônio'), max_length=50, blank=True, null=True, unique=True)
    
    modelo = models.ForeignKey(ModeloViatura, on_delete=models.PROTECT, related_name='viaturas')
    ano_fabricacao = models.PositiveIntegerField(_('Ano de Fabricação'), blank=True, null=True)
    cor = models.CharField(_('Cor Predominante'), max_length=30, default="Cinza/PM")
    
    tipo_combustivel = models.CharField(_('Tipo de Combustível Padrão'), max_length=20, choices=COMBUSTIVEL_CHOICES, default='FLEX')
    capacidade_tanque = models.DecimalField(_('Capacidade do Tanque (L)'), max_digits=6, decimal_places=2, default=0)
    
    # Controle de Rodagem
    odometro_atual = models.DecimalField(_('Odômetro/Horímetro Atual'), max_digits=10, decimal_places=1, default=0, help_text="Km ou Horas(embarcação)")
    
    status = models.CharField(_('Status Atual'), max_length=20, choices=STATUS_CHOICES, default='DISPONIVEL')
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Viatura')
        verbose_name_plural = _('Viaturas')
        ordering = ['modelo__tipo', 'prefixo']

    @property
    def tipo(self):
        return self.modelo.get_tipo_display()

    def __str__(self):
        return f"{self.prefixo} - {self.modelo.nome} [{self.get_status_display()}]"

class DespachoViatura(models.Model):
    """Controle de Saída (Despacho) e Retorno das Viaturas para o Policiamento"""
    viatura = models.ForeignKey(Viatura, on_delete=models.PROTECT, related_name='despachos')
    motorista = models.ForeignKey('policiais.Policial', on_delete=models.PROTECT, related_name='despachos_motorista', verbose_name="Motorista")
    encarregado = models.ForeignKey('policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True, related_name='despachos_encarregado', verbose_name="Encarregado/Cmt Eqp")
    
    data_saida = models.DateTimeField(_('Data/Hora de Saída'), auto_now_add=True)
    km_saida = models.DecimalField(_('Odômetro na Saída'), max_digits=10, decimal_places=1)
    
    data_retorno = models.DateTimeField(_('Data/Hora de Retorno'), blank=True, null=True)
    km_retorno = models.DecimalField(_('Odômetro no Retorno'), max_digits=10, decimal_places=1, blank=True, null=True)
    
    observacoes_saida = models.TextField(_('Avarias/Obs na Saída'), blank=True, null=True)
    observacoes_retorno = models.TextField(_('Avarias/Obs no Retorno'), blank=True, null=True)
    
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Despachante")

    class Meta:
        verbose_name = _('Despacho de Viatura')
        verbose_name_plural = _('Despachos de Viaturas')
        ordering = ['-data_saida']

    def __str__(self):
        return f"Despacho {self.viatura.prefixo} em {self.data_saida.strftime('%d/%m/%Y %H:%M')}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Atualiza o status da Viatura
        if not self.data_retorno:
            if self.viatura.status == 'DISPONIVEL':
                self.viatura.status = 'EM_USO'
                self.viatura.save(update_fields=['status'])
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
    viatura = models.ForeignKey(Viatura, on_delete=models.PROTECT, related_name='abastecimentos')
    motorista = models.ForeignKey('policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Quem abasteceu")
    
    data_abastecimento = models.DateTimeField(_('Data e Hora'))
    odometro = models.DecimalField(_('Odômetro no momento'), max_digits=10, decimal_places=1)
    
    combustivel = models.CharField(_('Tipo Utilizado'), max_length=20, choices=Viatura.COMBUSTIVEL_CHOICES)
    quantidade_litros = models.DecimalField(_('Quantidade (Litros)'), max_digits=6, decimal_places=2)
    valor_total = models.DecimalField(_('Valor Total (R$)'), max_digits=10, decimal_places=2, blank=True, null=True)
    
    cupom_fiscal = models.CharField(_('Cupom Fiscal/Requisição'), max_length=50, blank=True, null=True)
    posto_fornecedor = models.CharField(_('Posto/Fornecedor'), max_length=100, blank=True, null=True)
    
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _('Abastecimento')
        verbose_name_plural = _('Abastecimentos')
        ordering = ['-data_abastecimento']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.odometro and self.odometro > self.viatura.odometro_atual:
            self.viatura.odometro_atual = self.odometro
            self.viatura.save(update_fields=['odometro_atual'])

class Oficina(models.Model):
    """Cadastro de Oficinas e Oficinas Especializadas"""
    nome = models.CharField(_('Nome/Razão Social'), max_length=150)
    cnpj = models.CharField(_('CNPJ'), max_length=20, blank=True, null=True)
    endereco = models.CharField(_('Endereço'), max_length=255, blank=True, null=True)
    cidade = models.CharField(_('Cidade'), max_length=100, default='Santos')
    telefone = models.CharField(_('Telefone/WhatsApp'), max_length=50, blank=True, null=True)
    contato_responsavel = models.CharField(_('Nome do Contato'), max_length=100, blank=True, null=True)
    especialidade = models.CharField(_('Especialidade'), max_length=100, blank=True, null=True, help_text="Ex: Funilaria, Mecânica Diesel, Elétrica")
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Oficina')
        verbose_name_plural = _('Oficinas')
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Manutencao(models.Model):
    """Controle de Manutenções Preventivas e Corretivas"""
    TIPO_MANUTENCAO = [
        ('PREVENTIVA', 'Preventiva (Revisão, Óleo, Pneus)'),
        ('CORRETIVA', 'Corretiva (Quebra, Acidente)'),
    ]

    STATUS_CHOICES = [
        ('ABERTA', 'Em Aberto'),
        ('AGUARDANDO_PECA', 'Aguardando Peça'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    viatura = models.ForeignKey(Viatura, on_delete=models.PROTECT, related_name='manutencoes')
    tipo = models.CharField(_('Tipo de Manutenção'), max_length=20, choices=TIPO_MANUTENCAO)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='ABERTA')
    
    data_inicio = models.DateField(_('Data de Início'))
    data_conclusao = models.DateField(_('Data de Conclusão'), blank=True, null=True)
    
    odometro = models.DecimalField(_('Odômetro na Manutenção'), max_digits=10, decimal_places=1)
    
    descricao = models.TextField(_('Descrição dos Serviços/Peças'))
    oficina = models.CharField(_('Oficina (Texto)'), max_length=150, blank=True, null=True)
    oficina_fk = models.ForeignKey(Oficina, on_delete=models.SET_NULL, null=True, blank=True, related_name='manutencoes', verbose_name=_('Oficina (Cadastrada)'))
    
    custo_pecas = models.DecimalField(_('Custo Peças (R$)'), max_digits=10, decimal_places=2, default=0)
    custo_mao_obra = models.DecimalField(_('Custo Mão de Obra (R$)'), max_digits=10, decimal_places=2, default=0)
    
    ordem_servico = models.CharField(_('O.S. Nº'), max_length=50, blank=True, null=True)
    
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)

    @property
    def custo_total(self):
        return self.custo_pecas + self.custo_mao_obra

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Atualiza o status da Viatura
        if self.status in ['ABERTA', 'AGUARDANDO_PECA']:
            if self.viatura.status != 'MANUTENCAO':
                self.viatura.status = 'MANUTENCAO'
                self.viatura.save(update_fields=['status'])
        elif self.status in ['CONCLUIDA', 'CANCELADA']:
            if self.viatura.status == 'MANUTENCAO':
                # Verifica se não há outras manutenções ativas
                outras_ativas = self.viatura.manutencoes.filter(status__in=['ABERTA', 'AGUARDANDO_PECA']).exclude(pk=self.pk).exists()
                if not outras_ativas:
                    self.viatura.status = 'DISPONIVEL'
                    self.viatura.save(update_fields=['status'])
                    
        # Atualiza odômetro
        if self.odometro and self.odometro > self.viatura.odometro_atual:
            self.viatura.odometro_atual = self.odometro
            self.viatura.save(update_fields=['odometro_atual'])

class ChecklistViatura(models.Model):
    """Checklist completo para avaliação da viatura (Inspeção Operacional)"""
    TIPO_CHECKLIST = [
        ('SAIDA', 'Saída de Serviço'),
        ('RETORNO', 'Retorno de Serviço'),
        ('ROTINA', 'Inspeção de Rotina/Semanal'),
    ]

    viatura = models.ForeignKey(Viatura, on_delete=models.CASCADE, related_name='checklists')
    policial = models.ForeignKey('policiais.Policial', on_delete=models.PROTECT, verbose_name="Avaliador")
    tipo = models.CharField(_('Tipo de Checklist'), max_length=20, choices=TIPO_CHECKLIST, default='SAIDA')
    data_hora = models.DateTimeField(auto_now_add=True)
    odometro = models.DecimalField(_('Odômetro Atual'), max_digits=10, decimal_places=1)

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
    triangulo_macaco_chave = models.BooleanField(_('Triângulo/Macaco/Chave Roda OK?'), default=True)
    cones_sinalizacao = models.BooleanField(_('Cones de Sinalização OK?'), default=True)
    documentacao_crlv = models.BooleanField(_('Documentação (CRLV) OK?'), default=True)
    kit_primeiros_socorros = models.BooleanField(_('Kit Primeiros Socorros OK?'), default=True)

    # Registro de Danos
    avarias_lataria = models.TextField(_('Avarias na Lataria/Pintura'), blank=True, null=True, help_text="Descreva riscos, mossas ou quebras")
    observacoes_gerais = models.TextField(_('Observações Gerais'), blank=True, null=True)

    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _('Checklist de Viatura')
        verbose_name_plural = _('Checklists de Viaturas')
        ordering = ['-data_hora']

    def __str__(self):
        return f"Checklist {self.viatura.prefixo} - {self.get_tipo_display()} ({self.data_hora.strftime('%d/%m/%Y')})"
