from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator
from simple_history.models import HistoricalRecords

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
        ('EM_USO', 'Em Serviço Administrativo'),
        ('MANUTENCAO', 'Em Manutenção/Oficina'),
        ('VISTORIA', 'Aguardando Vistoria'),
        ('PREGAO', 'Para Pregão'),
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

    LOCALIZACAO_CHOICES = [
        ('1_CIA', '1ª CIA'),
        ('2_CIA', '2ª CIA'),
        ('3_CIA', '3ª CIA'),
        ('4_CIA', '4ª CIA'),
        ('EM', 'EM'),
        ('P4', 'P4'),
        ('MOTOMEC', 'MOTOMEC'),
        ('OFICINA', 'Oficina'),
        ('EM_USO', 'Em Serviço Administrativo'),
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
    localizacao = models.CharField(_('Localização Atual'), max_length=20, choices=LOCALIZACAO_CHOICES, default='MOTOMEC')
    
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

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
        ('AGENDADA', 'Agendada (Futura)'),
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
    
    # Controle e Auditoria da Manutenção
    servicos_executados_corretamente = models.BooleanField(_('Serviços executados corretamente?'), default=False, help_text='Marque após a verificação/teste da viatura')
    detalhamento_servicos = models.TextField(_('Detalhamento dos Serviços (Pós-Manutenção)'), blank=True, null=True, help_text='O que foi efetivamente feito na oficina')
    detalhamento_pecas_garantia = models.TextField(_('Peças Trocadas e Condições de Garantia'), blank=True, null=True)
    
    # Anexos
    nota_fiscal = models.FileField(_('Nota Fiscal (Anexo)'), upload_to='viaturas/manutencao/notas/', blank=True, null=True)
    termo_garantia = models.FileField(_('Termo de Garantia (Anexo)'), upload_to='viaturas/manutencao/garantias/', blank=True, null=True)
    
    # Validades
    data_validade_garantia = models.DateField(_('Validade da Garantia (Data)'), blank=True, null=True)
    km_validade_garantia = models.DecimalField(_('Validade da Garantia (Km)'), max_digits=10, decimal_places=1, blank=True, null=True)
    
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='manutencoes_registradas')
    
    # Timestamps de Auditoria
    data_criacao = models.DateTimeField(_('Data de Criação'), auto_now_add=True, null=True)
    data_atualizacao = models.DateTimeField(_('Última Atualização'), auto_now=True, null=True)
    
    # Controle de Aprovação (Fase 2)
    aprovado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencoes_aprovadas', verbose_name=_('Aprovado por')
    )
    data_aprovacao = models.DateTimeField(_('Data de Aprovação'), null=True, blank=True)
    parecer_aprovacao = models.TextField(_('Parecer de Aprovação/Conclusão'), blank=True, null=True)
    
    # Controle de Cancelamento (Fase 2)
    motivo_cancelamento = models.TextField(_('Motivo do Cancelamento'), blank=True, null=True)
    cancelado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencoes_canceladas', verbose_name=_('Cancelado por')
    )
    data_cancelamento = models.DateTimeField(_('Data do Cancelamento'), null=True, blank=True)
    
    # Vínculo com Retirada de Peças (Fase 3)
    retirada_pecas = models.ForeignKey(
        'RetiradaPeca', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencao_vinculada', verbose_name=_('Retirada de Peças Vinculada')
    )
    
    history = HistoricalRecords()

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
                # Verifica se não há outras manutenções ativas
                outras_ativas = self.viatura.manutencoes.filter(status__in=['ABERTA', 'AGUARDANDO_PECA']).exclude(pk=self.pk).exists()
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

    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Checklist de Viatura')
        verbose_name_plural = _('Checklists de Viaturas')
        ordering = ['-data_hora']

    def __str__(self):
        return f"Checklist {self.viatura.prefixo} - {self.get_tipo_display()} ({self.data_hora.strftime('%d/%m/%Y')})"

class SolicitacaoBaixaViatura(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente (Aguardando Análise)'),
        ('MANUTENCAO', 'Encaminhar para Manutenção'),
        ('OFICINA', 'Encaminhar para Oficina'),
        ('AGUARDAR_VISTORIA', 'Aguardar Vistoria'),
        ('MOTOMEC', 'Encaminhar para MOTOMEC'),
        ('PREGAO', 'Destinar para Pregão'),
        ('DESCARGA', 'Efetuar Descarga (Baixa Definitiva)'),
        ('NEGADA', 'Negada/Cancelada'),
    ]

    CATEGORIA_CHOICES = [
        ('PREVENTIVA', 'Manutenção Preventiva'),
        ('SUBSTITUICAO', 'Substituição de Peças'),
        ('QUEBRA', 'Quebra / Defeito Mecânico'),
        ('ACIDENTE', 'Acidente / Sinistro'),
        ('INSERVIVEL', 'Inservível / Fim de Vida Útil'),
        ('REPASSE', 'Repasse / Transferência'),
        ('LEILAO', 'Destinação para Leilão'),
        ('OUTROS', 'Outros Motivos'),
    ]

    viatura = models.ForeignKey(Viatura, on_delete=models.CASCADE, related_name='solicitacoes_baixa')
    solicitante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='baixas_solicitadas', help_text="Usuário logado que registrou")
    
    # Novos campos solicitados
    motorista = models.ForeignKey('policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True, related_name='baixas_como_motorista', verbose_name=_('Motorista Responsável'))
    requisitante = models.ForeignKey('policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True, related_name='baixas_requisitadas', verbose_name=_('Policial Requisitante'))
    
    categoria_motivo = models.CharField(_('Categoria da Baixa'), max_length=25, choices=CATEGORIA_CHOICES, default='INSERVIVEL')
    quilometragem_baixa = models.DecimalField(_('Quilometragem/Horímetro na Baixa'), max_digits=10, decimal_places=1, null=True, blank=True)
    
    motivo = models.TextField(_('Justificativa Detalhada'))
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    observacoes_admin = models.TextField(_('Observações/Parecer do Gestor'), blank=True, null=True)
    analisado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='baixas_analisadas')
    data_analise = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _('Solicitação de Baixa de Viatura')
        verbose_name_plural = _('Solicitações de Baixa de Viatura')
        ordering = ['-data_solicitacao']

    def __str__(self):
        return f"Baixa {self.viatura.prefixo} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # A lógica de atualização automática da viatura foi movida para a view para suportar múltiplas destinações
        super().save(*args, **kwargs)


class PecaViatura(models.Model):
    """Cadastro de Peças para Viaturas"""
    CATEGORIA_PECA_CHOICES = [
        ('MOTOR', 'Motor e Componentes'),
        ('SUSPENSAO', 'Suspensão e Direção'),
        ('FREIOS', 'Freios'),
        ('ELETRICA', 'Elétrica e Iluminação'),
        ('TRANSMISSAO', 'Transmissão e Embreagem'),
        ('CARROCERIA', 'Carroceria e Acabamento'),
        ('LUBRIFICANTES', 'Fluidos e Lubrificantes'),
        ('OUTROS', 'Outros/Geral'),
    ]

    nome = models.CharField(_('Nome da Peça'), max_length=150)
    codigo = models.CharField(_('Código/Part Number'), max_length=50, blank=True, null=True)
    categoria = models.CharField(_('Categoria/Sistema'), max_length=30, choices=CATEGORIA_PECA_CHOICES, default='OUTROS')
    marca_fabricante = models.CharField(_('Marca/Fabricante'), max_length=100, blank=True, null=True)
    aplicacao = models.TextField(_('Aplicação (Modelos Compatíveis)'), blank=True, null=True)
    
    quantidade_estoque = models.PositiveIntegerField(_('Quantidade em Estoque'), default=0)
    limite_minimo = models.PositiveIntegerField(_('Estoque Mínimo'), default=0)
    localizacao_estoque = models.CharField(_('Localização no Estoque'), max_length=100, blank=True, null=True, help_text="Ex: Prateleira 2, Gaveta A")
    valor_unitario = models.DecimalField(_('Valor Unitário Estimado (R$)'), max_digits=10, decimal_places=2, blank=True, null=True)
    
    observacoes = models.TextField(_('Observações Gerais'), blank=True, null=True)
    ativo = models.BooleanField(_('Ativo'), default=True)

    class Meta:
        verbose_name = _('Peça de Viatura')
        verbose_name_plural = _('Peças de Viaturas')
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.quantidade_estoque} em estoque)"

class RetiradaPeca(models.Model):
    """Registro de Retirada de Peças para uso em Viatura"""
    viatura = models.ForeignKey(Viatura, on_delete=models.PROTECT, related_name='retiradas_pecas', verbose_name=_('Viatura de Destino'))
    policial = models.ForeignKey('policiais.Policial', on_delete=models.PROTECT, related_name='retiradas_pecas', verbose_name=_('Policial que Retirou'))
    data_retirada = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(_('Observações/Justificativa'), blank=True, null=True)
    
    assinado_eletronicamente = models.BooleanField(_('Assinado Eletronicamente?'), default=False)
    arquivo_recibo = models.FileField(_('Recibo de Retirada'), upload_to='viaturas/recibos_pecas/', null=True, blank=True)
    
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _('Retirada de Peça')
        verbose_name_plural = _('Retiradas de Peças')
        ordering = ['-data_retirada']

    def __str__(self):
        return f"Retirada para {self.viatura.prefixo} em {self.data_retirada.strftime('%d/%m/%Y')}"

class RetiradaPecaItem(models.Model):
    retirada = models.ForeignKey(RetiradaPeca, on_delete=models.CASCADE, related_name='itens')
    peca = models.ForeignKey(PecaViatura, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(_('Quantidade'))

    class Meta:
        verbose_name = _('Item da Retirada de Peça')
        verbose_name_plural = _('Itens da Retirada de Peça')

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
    TIPO_CHOICES = [
        ('FOTO_ANTES', 'Foto Antes do Serviço'),
        ('FOTO_DEPOIS', 'Foto Após o Serviço'),
        ('ORCAMENTO', 'Orçamento'),
        ('LAUDO', 'Laudo Técnico'),
        ('OUTRO', 'Outro Documento'),
    ]
    
    manutencao = models.ForeignKey(Manutencao, on_delete=models.CASCADE, related_name='evidencias')
    tipo = models.CharField(_('Tipo de Evidência'), max_length=20, choices=TIPO_CHOICES)
    arquivo = models.FileField(_('Arquivo'), upload_to='viaturas/manutencao/evidencias/')
    descricao = models.CharField(_('Descrição'), max_length=200, blank=True)
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)
    data_upload = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Evidência de Manutenção')
        verbose_name_plural = _('Evidências de Manutenção')
        ordering = ['-data_upload']

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.manutencao.viatura.prefixo} ({self.data_upload.strftime('%d/%m/%Y')})"


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
    )
    custo_mao_obra = models.DecimalField(
        _('Custo Mão de Obra (R$)'), max_digits=10, decimal_places=2, default=0,
    )
    odometro = models.DecimalField(
        _('Odômetro'), max_digits=10, decimal_places=1, blank=True, null=True,
    )
    status_na_epoca = models.CharField(
        _('Status na época'), max_length=20, blank=True,
        choices=Manutencao.STATUS_CHOICES,
        help_text=_('Snapshot do status da manutenção no momento do registro'),
    )
    registrado_por = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='servicos_manutencao_registrados',
    )
    data_registro = models.DateTimeField(_('Data do Registro'), auto_now_add=True)

    class Meta:
        verbose_name = _('Serviço de Manutenção')
        verbose_name_plural = _('Serviços de Manutenção')
        ordering = ['-data_registro']

    def __str__(self):
        resumo = self.descricao[:60] + ('…' if len(self.descricao) > 60 else '')
        return f"Serviço — {self.manutencao.viatura.prefixo}: {resumo}"

    @property
    def custo_total(self):
        return self.custo_pecas + self.custo_mao_obra


class RegistroHistoricoManutencao(models.Model):
    """Linha do tempo append-only da manutenção (auditoria orientada a eventos)."""
    TIPO_EVENTO = [
        ('ABERTURA', 'Abertura da Manutenção'),
        ('SERVICO', 'Serviço Registrado'),
        ('ATUALIZACAO', 'Atualização Administrativa'),
        ('STATUS', 'Mudança de Status'),
        ('CONCLUSAO', 'Conclusão'),
        ('CANCELAMENTO', 'Cancelamento'),
        ('EVIDENCIA', 'Evidência Anexada'),
    ]

    manutencao = models.ForeignKey(
        Manutencao, on_delete=models.CASCADE, related_name='registros_historico',
        verbose_name=_('Manutenção'),
    )
    tipo = models.CharField(_('Tipo de Evento'), max_length=20, choices=TIPO_EVENTO)
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
        User, on_delete=models.PROTECT, related_name='historicos_manutencao_registrados',
    )
    data_registro = models.DateTimeField(_('Data do Registro'), auto_now_add=True)

    class Meta:
        verbose_name = _('Registro de Histórico de Manutenção')
        verbose_name_plural = _('Registros de Histórico de Manutenção')
        ordering = ['-data_registro']

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.manutencao.viatura.prefixo} ({self.data_registro:%d/%m/%Y %H:%M})"


class PlanoManutencaoPreventiva(models.Model):
    """Regras de manutenção preventiva por modelo de viatura (Fase 3)"""
    modelo = models.ForeignKey(ModeloViatura, on_delete=models.CASCADE, related_name='planos_preventivos')
    descricao = models.CharField(_('Descrição do Serviço'), max_length=200, help_text='Ex: Troca de óleo, Revisão geral')
    intervalo_km = models.PositiveIntegerField(_('Intervalo em Km'), null=True, blank=True, help_text='A cada quantos km realizar')
    intervalo_dias = models.PositiveIntegerField(_('Intervalo em Dias'), null=True, blank=True, help_text='A cada quantos dias realizar')
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Plano de Manutenção Preventiva')
        verbose_name_plural = _('Planos de Manutenção Preventiva')
        ordering = ['modelo__marca__nome', 'modelo__nome', 'descricao']

    def __str__(self):
        partes = [self.descricao]
        if self.intervalo_km:
            partes.append(f"a cada {self.intervalo_km:,} km")
        if self.intervalo_dias:
            partes.append(f"a cada {self.intervalo_dias} dias")
        return f"{self.modelo} — {' / '.join(partes)}"
