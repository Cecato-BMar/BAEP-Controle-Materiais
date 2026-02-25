from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import F, Sum
from django.utils import timezone
from decimal import Decimal
from .models import MovimentacaoEstoque, Produto, AjusteEstoque, ItemInventario


@receiver(post_save, sender=MovimentacaoEstoque)
def atualizar_estoque_movimentacao(sender, instance, created, **kwargs):
    """Atualiza o estoque do produto após uma movimentação"""
    produto = instance.produto
    quantidade = instance.quantidade
    
    if instance.tipo_movimentacao == 'ENTRADA':
        # Entrada: aumenta o estoque
        Produto.objects.filter(pk=produto.pk).update(
            estoque_atual=F('estoque_atual') + quantidade
        )
        
        # Atualiza lote se especificado
        if instance.lote:
            instance.lote.quantidade_atual += quantidade
            instance.lote.save()
            
    elif instance.tipo_movimentacao == 'SAIDA':
        # Saída: diminui o estoque
        Produto.objects.filter(pk=produto.pk).update(
            estoque_atual=F('estoque_atual') - quantidade
        )
        
        # Atualiza lote se especificado
        if instance.lote:
            instance.lote.quantidade_atual -= quantidade
            instance.lote.save()
            
    elif instance.tipo_movimentacao == 'TRANSFERENCIA':
        # Transferência não afeta o total, apenas a localização
        pass
        
    elif instance.tipo_movimentacao == 'AJUSTE':
        # Ajuste: positivo ou negativo
        Produto.objects.filter(pk=produto.pk).update(
            estoque_atual=F('estoque_atual') + quantidade
        )
        
        # Atualiza lote se especificado
        if instance.lote:
            instance.lote.quantidade_atual += quantidade
            instance.lote.save()

    # Atualiza valor total do produto
    produto.refresh_from_db()
    Produto.objects.filter(pk=produto.pk).update(
        valor_total=F('estoque_atual') * produto.valor_unitario
    )


@receiver(post_save, sender=AjusteEstoque)
def atualizar_estoque_ajuste(sender, instance, created, **kwargs):
    """Atualiza o estoque do produto após um ajuste"""
    produto = instance.produto
    
    # Atualiza estoque para a quantidade depois do ajuste
    Produto.objects.filter(pk=produto.pk).update(
        estoque_atual=instance.quantidade_depois
    )
    
    # Atualiza lote se especificado
    if instance.lote:
        # Recalcula quantidade do lote baseado em todos os ajustes
        from django.db.models import Sum
        total_ajustes_lote = AjusteEstoque.objects.filter(
            lote=instance.lote
        ).aggregate(total=Sum('quantidade'))['total'] or 0
        
        # Obtém quantidade inicial do lote
        movimentacoes_entrada = MovimentacaoEstoque.objects.filter(
            lote=instance.lote,
            tipo_movimentacao='ENTRADA'
        ).aggregate(total=Sum('quantidade'))['total'] or 0
        
        movimentacoes_saida = MovimentacaoEstoque.objects.filter(
            lote=instance.lote,
            tipo_movimentacao='SAIDA'
        ).aggregate(total=Sum('quantidade'))['total'] or 0
        
        instance.lote.quantidade_atual = movimentacoes_entrada - movimentacoes_saida + total_ajustes_lote
        instance.lote.save()

    # Atualiza valor total do produto
    produto.refresh_from_db()
    Produto.objects.filter(pk=produto.pk).update(
        valor_total=F('estoque_atual') * produto.valor_unitario
    )


@receiver(pre_save, sender=ItemInventario)
def calcular_diferenca_item_inventario(sender, instance, **kwargs):
    """Calcula a diferença entre quantidade contada e do sistema"""
    if instance.quantidade_contada is not None:
        instance.diferenca = instance.quantidade_contada - instance.quantidade_sistema


@receiver(post_save, sender=ItemInventario)
def atualizar_status_inventario(sender, instance, created, **kwargs):
    """Atualiza o status do inventário baseado nos itens contados"""
    inventario = instance.inventario
    total_itens = inventario.itens_inventario.count()
    itens_contados = inventario.itens_inventario.filter(contado_em__isnull=False).count()
    
    if itens_contados == 0:
        status = 'PLANEJADO'
    elif itens_contados < total_itens:
        status = 'EM_ANDAMENTO'
    else:
        status = 'CONCLUIDO'
    
    if inventario.status != status:
        inventario.status = status
        if status == 'CONCLUIDO' and inventario.data_fim is None:
            inventario.data_fim = timezone.now()
        inventario.save(update_fields=['status', 'data_fim'])

    if inventario.status == 'CONCLUIDO' and inventario.data_fim is not None:
        itens_para_ajustar = inventario.itens_inventario.filter(
            contado_em__isnull=False
        ).exclude(status_contagem='AJUSTADO')

        for item in itens_para_ajustar:
            if item.quantidade_contada is None:
                continue

            diferenca = item.diferenca
            if diferenca is None:
                diferenca = item.quantidade_contada - item.quantidade_sistema

            if diferenca == 0:
                item.status_contagem = 'AJUSTADO'
                item.save(update_fields=['status_contagem'])
                continue

            tipo_ajuste = 'ACRESCIMO' if diferenca > 0 else 'DEBITO'
            quantidade_ajuste = abs(Decimal(diferenca))

            produto = item.produto
            produto.refresh_from_db(fields=['estoque_atual', 'valor_unitario'])

            AjusteEstoque.objects.create(
                inventario=inventario,
                produto=produto,
                lote=item.lote,
                numero_serie=item.numero_serie,
                tipo_ajuste=tipo_ajuste,
                motivo='INVENTARIO',
                quantidade=quantidade_ajuste,
                valor_unitario=produto.valor_unitario,
                quantidade_antes=produto.estoque_atual,
                quantidade_depois=item.quantidade_contada,
                observacoes=item.observacoes,
                aprovado_por=inventario.responsavel,
            )

            item.status_contagem = 'AJUSTADO'
            item.save(update_fields=['status_contagem'])
