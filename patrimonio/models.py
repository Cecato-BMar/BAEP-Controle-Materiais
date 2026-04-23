from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.utils import timezone

class CategoriaPatrimonio(models.Model):
    """Categorias macro para patrimônio (Ex: Informática, Mobiliário, Equipamento Tático)"""
    nome = models.CharField(_('Nome'), max_length=100, unique=True)
    descricao = models.TextField(_('Descrição'), blank=True, null=True)
    ativo = models.BooleanField(_('Ativo'), default=True)

    class Meta:
        verbose_name = _('Categoria de Patrimônio')
        verbose_name_plural = _('Categorias de Patrimônio')
        ordering = ['nome']

    def __str__(self):
        return self.nome

class BemPatrimonial(models.Model):
    """Modelo/Tipo de bem (Ex: Cadeira Giratória, Notebook Dell G15)"""
    nome = models.CharField(_('Nome do Bem'), max_length=200)
    descricao = models.TextField(_('Descrição Técnica'), blank=True, null=True)
    categoria = models.ForeignKey(CategoriaPatrimonio, on_delete=models.PROTECT, related_name='bens')
    
    # Especificações
    marca = models.CharField(_('Marca/Fabricante'), max_length=100, blank=True, null=True)
    modelo_referencia = models.CharField(_('Modelo de Referência'), max_length=100, blank=True, null=True)
    
    valor_unitario_estimado = models.DecimalField(_('Valor Unitário Estimado'), max_digits=12, decimal_places=2, default=0)
    
    ativo = models.BooleanField(_('Ativo'), default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Bem Patrimonial (Catálogo)')
        verbose_name_plural = _('Bens Patrimoniais (Catálogo)')
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.marca or 'S/M'})"

    @property
    def total_itens(self):
        return self.itens.count()

    @property
    def total_disponivel(self):
        return self.itens.filter(status='DISPONIVEL').count()

class ItemPatrimonial(models.Model):
    """Item individual com número de patrimônio e/ou série"""
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível (Reserva)'),
        ('EM_USO', 'Em Uso (Cautela)'),
        ('MANUTENCAO', 'Em Manutenção'),
        ('BAIXADO', 'Baixado/Inativo'),
        ('EXTRAVIADO', 'Extraviado/Furto'),
    ]

    ESTADO_CHOICES = [
        ('NOVO', 'Novo'),
        ('BOM', 'Bom'),
        ('REGULAR', 'Regular'),
        ('RUIM', 'Ruim'),
        ('INSERVIVEL', 'Inservível'),
    ]

    bem = models.ForeignKey(BemPatrimonial, on_delete=models.CASCADE, related_name='itens')
    numero_patrimonio = models.CharField(_('Nº de Patrimônio'), max_length=50, unique=True, help_text="Ex: PM-123456")
    numero_serie = models.CharField(_('Nº de Série'), max_length=100, blank=True, null=True, unique=True)
    
    estado_conservacao = models.CharField(_('Estado de Conservação'), max_length=20, choices=ESTADO_CHOICES, default='BOM')
    status = models.CharField(_('Status Atual'), max_length=20, choices=STATUS_CHOICES, default='DISPONIVEL')
    
    # Localização fixa
    localizacao = models.ForeignKey('estoque.LocalizacaoFisica', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Localização")
    
    # Responsável atual (se em uso)
    responsavel_atual = models.ForeignKey('policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True, related_name='itens_sob_cautela')
    
    data_aquisicao = models.DateField(_('Data de Aquisição'), null=True, blank=True)
    nota_fiscal = models.CharField(_('Nota Fiscal'), max_length=50, blank=True, null=True)
    
    observacoes = models.TextField(_('Observações'), blank=True, null=True)
    
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Item Patrimonial (Individual)')
        verbose_name_plural = _('Itens Patrimoniais (Individuais)')
        ordering = ['numero_patrimonio']

    def __str__(self):
        return f"{self.numero_patrimonio} - {self.bem.nome}"

class MovimentacaoPatrimonio(models.Model):
    """Histórico de cautelas, transferências e manutenções"""
    TIPO_CHOICES = [
        ('CAUTELA', 'Cautela (Saída para Policial)'),
        ('DEVOLUCAO', 'Devolução / Retorno'),
        ('TRANSFERENCIA', 'Transferência de Local'),
        ('MANUTENCAO_INICIO', 'Envio para Manutenção'),
        ('MANUTENCAO_FIM', 'Retorno de Manutenção'),
        ('BAIXA', 'Baixa Definitiva'),
    ]

    item = models.ForeignKey(ItemPatrimonial, on_delete=models.CASCADE, related_name='historico')
    tipo = models.CharField(_('Tipo de Movimentação'), max_length=20, choices=TIPO_CHOICES)
    
    data_hora = models.DateTimeField(_('Data/Hora'), default=timezone.now)
    
    # Destinos / Envolvidos
    policial = models.ForeignKey('policiais.Policial', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Policial Envolvido")
    local_destino = models.ForeignKey('estoque.LocalizacaoFisica', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Local de Destino")
    
    observacoes = models.TextField(_('Justificativa/Observações'), blank=True, null=True)
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _('Movimentação de Patrimônio')
        verbose_name_plural = _('Movimentações de Patrimônio')
        ordering = ['-data_hora']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.item.numero_patrimonio} - {self.data_hora.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            item = self.item
            atualizou = False
            
            # Atualiza localização se houver um local de destino, independentemente do tipo de movimentação
            if self.local_destino:
                item.localizacao = self.local_destino
                atualizou = True
                
            if self.tipo == 'CAUTELA':
                item.status = 'EM_USO'
                item.responsavel_atual = self.policial
                atualizou = True
            elif self.tipo == 'DEVOLUCAO':
                item.status = 'DISPONIVEL'
                item.responsavel_atual = None
                atualizou = True
            elif self.tipo == 'MANUTENCAO_INICIO':
                item.status = 'MANUTENCAO'
                atualizou = True
            elif self.tipo == 'MANUTENCAO_FIM':
                item.status = 'DISPONIVEL'
                atualizou = True
            elif self.tipo == 'BAIXA':
                item.status = 'BAIXADO'
                atualizou = True
                
            if atualizou:
                item.save(update_fields=['status', 'responsavel_atual', 'localizacao', 'data_atualizacao'])
