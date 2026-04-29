from django.db import models
from django.conf import settings
from estoque.models import Produto

class Solicitacao(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente (Aguardando Análise)'),
        ('EM_SEPARACAO', 'Em Separação'),
        ('PRONTO', 'Pronto para Retirada'),
        ('ENTREGUE', 'Entregue / Finalizado'),
        ('CANCELADO', 'Cancelado'),
    ]

    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='solicitacoes_feitas',
        verbose_name='Solicitante'
    )
    orgao_requisitante = models.ForeignKey('estoque.OrgaoRequisitante', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Seção/Cia Requisitante')
    policial_requisitante = models.ForeignKey(
        'policiais.Policial', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='solicitacoes_materiais',
        verbose_name='Policial Requisitante'
    )
    entregue_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entregas_realizadas',
        verbose_name='Entregue por'
    )
    data_solicitacao = models.DateTimeField(auto_now_add=True, verbose_name='Data da Solicitação')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE', verbose_name='Status')
    observacoes = models.TextField(blank=True, null=True, verbose_name='Observações do Solicitante')
    notas_admin = models.TextField(blank=True, null=True, verbose_name='Notas do Almoxarifado')
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Última Atualização')

    class Meta:
        verbose_name = 'Solicitação de Material'
        verbose_name_plural = 'Solicitações de Materiais'
        ordering = ['-data_solicitacao']

    def __str__(self):
        return f"Solicitação #{self.id} - {self.solicitante.get_full_name() or self.solicitante.username}"

class ItemSolicitacao(models.Model):
    solicitacao = models.ForeignKey(
        Solicitacao, 
        on_delete=models.CASCADE, 
        related_name='itens',
        verbose_name='Solicitação'
    )
    produto = models.ForeignKey(
        Produto, 
        on_delete=models.PROTECT, 
        verbose_name='Produto'
    )
    quantidade_solicitada = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Qtd. Solicitada')
    quantidade_atendida = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Qtd. Atendida')

    class Meta:
        verbose_name = 'Item da Solicitação'
        verbose_name_plural = 'Itens da Solicitação'

    def __str__(self):
        return f"{self.quantidade_solicitada}x {self.produto.nome}"
