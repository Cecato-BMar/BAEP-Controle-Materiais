"""
viaturas/services/abastecimento_service.py
Serviços de abastecimento e gestão de retirada de peças.

Centraliza a lógica de:
  - Registro de abastecimentos (com sincronização de odômetro).
  - Registro de retirada de peças (com transação e validação de estoque).
  - Consultas de consumo e histórico por viatura.
"""
from decimal import Decimal
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, F
from django.utils import timezone

from viaturas.models import (
    Viatura, Abastecimento, RetiradaPeca, RetiradaPecaItem,
    PecaViatura, Combustivel,
)


# ============================================================================
# VALIDAÇÕES
# ============================================================================
def _validar_litros(quantidade):
    if quantidade is None or quantidade <= Decimal('0'):
        raise ValidationError('Quantidade de litros deve ser positiva.', code='litros_invalidos')


def _validar_estoque(peca, quantidade):
    """Verifica se há estoque suficiente antes de retirar."""
    if peca.quantidade_estoque < quantidade:
        raise ValidationError(
            f'Estoque insuficiente para "{peca.nome}": '
            f'disponível={peca.quantidade_estoque}, solicitado={quantidade}.',
            code='estoque_insuficiente',
        )


# ============================================================================
# ABASTECIMENTO
# ============================================================================
@transaction.atomic
def registrar_abastecimento(
    viatura,
    motorista,
    usuario,
    *,
    data_abastecimento,
    odometro,
    combustivel,
    quantidade_litros,
    valor_total=None,
    cupom_fiscal=None,
    posto_fornecedor=None,
):
    """
    Registra um abastecimento e sincroniza o odômetro da viatura.

    O odômetro da viatura é atualizado se o valor registrado for maior que o atual.

    Args:
        viatura: instância de Viatura.
        motorista: Policial que abasteceu (pode ser None).
        usuario: User logado.
        data_abastecimento: datetime do abastecimento.
        odometro: leitura do odômetro no momento.
        combustivel: tipo de combustível (choice de Combustivel).
        quantidade_litros: litros abastecidos.
        valor_total: valor pago em R$ (opcional).
        cupom_fiscal: número do cupom (opcional).
        posto_fornecedor: nome do posto (opcional).

    Raises:
        ValidationError: se litros <= 0.

    Returns:
        Abastecimento criado.
    """
    _validar_litros(quantidade_litros)

    abastecimento = Abastecimento.objects.create(
        viatura=viatura,
        motorista=motorista,
        data_abastecimento=data_abastecimento,
        odometro=odometro,
        combustivel=combustivel,
        quantidade_litros=quantidade_litros,
        valor_total=valor_total,
        cupom_fiscal=cupom_fiscal or '',
        posto_fornecedor=posto_fornecedor or '',
        registrado_por=usuario,
    )

    # Sincronizar odômetro (model.save() também faz, mas garantimos aqui)
    if odometro and odometro > viatura.odometro_atual:
        viatura.odometro_atual = odometro
        viatura.save(update_fields=['odometro_atual'])

    return abastecimento


def listar_abastecimentos(viatura_id=None, limite=None):
    """
    Lista abastecimentos ordenados por data, com filtro opcional por viatura.

    Args:
        viatura_id: ID da viatura (None = todas).
        limite: quantidade máxima de registros (None = todos).

    Returns:
        QuerySet de Abastecimento.
    """
    qs = (
        Abastecimento.objects
        .select_related('viatura', 'motorista')
        .order_by('-data_abastecimento')
    )
    if viatura_id:
        qs = qs.filter(viatura_id=viatura_id)
    if limite:
        qs = qs[:limite]
    return qs


def obter_consumo_viatura(viatura):
    """
    Retorna dados consolidados de consumo de uma viatura.

    Args:
        viatura: instância de Viatura.

    Returns:
        dict com:
            total_litros, total_valor, total_abastecimentos,
            consumo_por_combustivel (list),
            media_litros_por_abastecimento.
    """
    abastecimentos = viatura.abastecimentos.all()
    agg = abastecimentos.aggregate(
        total_litros=Sum('quantidade_litros'),
        total_valor=Sum('valor_total'),
        total=Sum('quantidade_litros'),
        qtd_abastecimentos=Sum('quantidade_litros'),  # Count
    )
    total_litros = agg['total_litros'] or Decimal('0')
    total_valor = agg['total_valor'] or Decimal('0')
    qtd = abastecimentos.count()

    # Consumo por tipo de combustível
    consumo_por_tipo = list(
        abastecimentos
        .values('combustivel')
        .annotate(
            litros=Sum('quantidade_litros'),
            valor=Sum('valor_total'),
            abastecimentos_count=Sum('quantidade_litros'),
        )
        .order_by('combustivel')
    )

    media = total_litros / qtd if qtd else Decimal('0')

    return {
        'total_litros': total_litros,
        'total_valor': total_valor,
        'total_abastecimentos': qtd,
        'media_litros_por_abastecimento': media,
        'consumo_por_combustivel': consumo_por_tipo,
    }


# ============================================================================
# RETIRADA DE PEÇAS
# ============================================================================
@transaction.atomic
def criar_retirada(viatura, policial, usuario, *, itens, observacoes=''):
    """
    Cria uma retirada de peças com múltiplos itens em transação atômica.

    Para cada item, valida e debita o estoque da peça.
    Se qualquer item falhar, toda a retirada é revertida (atomic).

    Args:
        viatura: Viatura de destino.
        policial: Policial que retirou.
        usuario: User logado.
        itens: list[dict] com [{peca, quantidade}, ...].
            - peca: instância de PecaViatura ou PK.
            - quantidade: int >= 1.
        observacoes: texto opcional.

    Raises:
        ValidationError: se qualquer item tiver estoque insuficiente.
        ValueError: propagado do save() de RetiradaPecaItem.

    Returns:
        RetiradaPeca criada (com itens salvos).
    """
    if not itens:
        raise ValidationError('Informe ao menos um item na retirada.', code='itens_vazio')

    # Resolver peças (aceita PK ou instância)
    itens_resolvidos = []
    for item in itens:
        peca = item.get('peca') or item.get('peca_id')
        quantidade = item.get('quantidade', 1)
        if isinstance(peca, int) or isinstance(peca, str):
            peca = PecaViatura.objects.get(pk=peca)
        if not isinstance(peca, PecaViatura):
            raise ValidationError(f'Peça inválida: {peca}', code='peca_invalida')
        itens_resolvidos.append({'peca': peca, 'quantidade': quantidade})

    # Validar estoque antes de criar qualquer coisa
    for item in itens_resolvidos:
        _validar_estoque(item['peca'], item['quantidade'])

    # Criar retirada
    retirada = RetiradaPeca.objects.create(
        viatura=viatura,
        policial=policial,
        observacoes=observacoes,
        registrado_por=usuario,
    )

    # Criar itens (cada save() debita estoque)
    for item in itens_resolvidos:
        RetiradaPecaItem.objects.create(
            retirada=retirada,
            peca=item['peca'],
            quantidade=item['quantidade'],
        )

    return retirada


def listar_retiradas(viatura_id=None, limite=None):
    """
    Lista retiradas ordenadas por data, com filtro opcional por viatura.

    Args:
        viatura_id: ID da viatura (None = todas).
        limite: quantidade máxima de registros.

    Returns:
        QuerySet de RetiradaPeca.
    """
    from django.db.models import Count
    qs = (
        RetiradaPeca.objects
        .select_related('viatura', 'policial', 'registrado_por')
        .annotate(total_itens=Count('itens'))
        .order_by('-data_retirada')
    )
    if viatura_id:
        qs = qs.filter(viatura_id=viatura_id)
    if limite:
        qs = qs[:limite]
    return qs


def obter_pecas_estoque_critico():
    """
    Retorna peças com estoque abaixo do mínimo, ordenadas por criticidade.

    Returns:
        QuerySet de PecaViatura com estoque_abaixo_minimo=True.
    """
    return (
        PecaViatura.objects
        .filter(ativo=True)
        .annotate(
            diferenca=F('quantidade_estoque') - F('limite_minimo'),
        )
        .filter(diferenca__lte=0)
        .order_by('diferenca', 'nome')
    )


def repor_estoque(peca, quantidade):
    """
    Adiciona quantidade ao estoque de uma peça.

    Args:
        peca: instância de PecaViatura.
        quantidade: int positivo.

    Returns:
        PecaViatura com estoque atualizado.
    """
    if quantidade <= 0:
        raise ValidationError('Quantidade de reposição deve ser positiva.', code='qtd_invalida')
    peca.quantidade_estoque += quantidade
    peca.save(update_fields=['quantidade_estoque'])
    return peca
