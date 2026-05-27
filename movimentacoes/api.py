from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from .models import Devolucao, Movimentacao, Retirada


def _parse_optional_positive_int(raw_value, field_name):
    if raw_value in (None, ''):
        return None

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f'Parâmetro {field_name} inválido.')

    if value < 1:
        raise ValueError(f'Parâmetro {field_name} inválido.')

    return value


def _calcular_quantidade_devolvida(retirada):
    return (
        Devolucao.objects.filter(retirada_referencia=retirada)
        .aggregate(total=Sum('movimentacao__quantidade'))
        .get('total')
        or 0
    )


@login_required
def api_retirada_detalhe(request, retirada_id):
    """
    API para obter detalhes de uma retirada específica
    """
    retirada = get_object_or_404(
        Retirada.objects.select_related(
            'movimentacao__material',
            'movimentacao__policial',
            'movimentacao__registrado_por',
            'movimentacao__lote_municao',
        ),
        pk=retirada_id,
    )
    movimentacao = retirada.movimentacao
    quantidade_devolvida = _calcular_quantidade_devolvida(retirada)
    quantidade_pendente = movimentacao.quantidade - quantidade_devolvida

    retirada_data = {
        'id': retirada.id,
        'data_hora': movimentacao.data_hora.strftime('%d/%m/%Y %H:%M'),
        'finalidade': retirada.finalidade,
        'local_uso': retirada.local_uso,
        'data_prevista_devolucao': retirada.data_prevista_devolucao.strftime('%d/%m/%Y %H:%M') if retirada.data_prevista_devolucao else None,
        'quantidade_retirada': movimentacao.quantidade,
        'quantidade_devolvida': quantidade_devolvida,
        'quantidade_pendente': quantidade_pendente,
        'observacoes': movimentacao.observacoes,
        'material': {
            'id': movimentacao.material.id,
            'nome': movimentacao.material.nome,
            'identificacao': movimentacao.material.numero,
            'numero': movimentacao.material.numero,
            'tipo': movimentacao.material.tipo,
            'tipo_display': movimentacao.material.get_tipo_display(),
        },
        'lote': {
            'id': movimentacao.lote_municao.id,
            'numero_lote': movimentacao.lote_municao.numero_lote,
            'marca': movimentacao.lote_municao.marca,
            'calibre': movimentacao.lote_municao.calibre,
        } if movimentacao.lote_municao else None,
        'policial': {
            'id': movimentacao.policial.id,
            're': movimentacao.policial.re,
            'nome': movimentacao.policial.nome,
            'posto': movimentacao.policial.posto,
        },
        'registrado_por': {
            'id': movimentacao.registrado_por.id,
            'username': movimentacao.registrado_por.username,
            'nome': movimentacao.registrado_por.get_full_name() or movimentacao.registrado_por.username,
        }
    }

    return JsonResponse(retirada_data)


@login_required
def api_retiradas_pendentes(request):
    """
    API para listar retiradas pendentes de devolução
    Pode ser filtrado por policial_id e/ou material_id
    """
    try:
        policial_id = _parse_optional_positive_int(request.GET.get('policial_id'), 'policial_id')
        material_id = _parse_optional_positive_int(request.GET.get('material_id'), 'material_id')
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    movimentacoes_retirada = (
        Movimentacao.objects.filter(tipo='RETIRADA', retirada__isnull=False)
        .select_related('material', 'policial', 'retirada', 'lote_municao')
        .annotate(quantidade_devolvida=Sum('retirada__devolucoes__movimentacao__quantidade'))
        .order_by('-data_hora')
    )

    if policial_id:
        movimentacoes_retirada = movimentacoes_retirada.filter(policial_id=policial_id)

    if material_id:
        movimentacoes_retirada = movimentacoes_retirada.filter(material_id=material_id)

    retiradas_pendentes = []

    for mov in movimentacoes_retirada:
        quantidade_devolvida = mov.quantidade_devolvida or 0

        if quantidade_devolvida < mov.quantidade:
            quantidade_pendente = mov.quantidade - quantidade_devolvida

            retiradas_pendentes.append({
                'id': mov.retirada.id,
                'material': {
                    'id': mov.material.id,
                    'nome': mov.material.nome,
                    'identificacao': mov.material.numero,
                    'tipo': mov.material.tipo,
                    'tipo_display': mov.material.get_tipo_display(),
                },
                'policial': {
                    'id': mov.policial.id,
                    're': mov.policial.re,
                    'nome': mov.policial.nome,
                },
                'lote': {
                    'id': mov.lote_municao.id,
                    'numero_lote': mov.lote_municao.numero_lote,
                    'marca': mov.lote_municao.marca,
                    'calibre': mov.lote_municao.calibre,
                } if mov.lote_municao else None,
                'data_hora': mov.data_hora.strftime('%d/%m/%Y %H:%M'),
                'finalidade': mov.retirada.finalidade,
                'quantidade_retirada': mov.quantidade,
                'quantidade_devolvida': quantidade_devolvida,
                'quantidade_pendente': quantidade_pendente,
                'lote_id': mov.lote_municao.id if mov.lote_municao else None,
                'lote_numero': mov.lote_municao.numero_lote if mov.lote_municao else None,
                'lote_calibre': mov.lote_municao.calibre if mov.lote_municao else None,
            })

    return JsonResponse(retiradas_pendentes, safe=False)
