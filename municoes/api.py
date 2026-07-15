from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from .models import LoteMunicao, RetiradaMunicao


@require_GET
def api_lotes(request):
    lotes = LoteMunicao.objects.filter(ativo=True, quantidade_atual__gt=0).select_related('material')
    data = [
        {
            'id': lote.id,
            'material': lote.material.nome,
            'numero_lote': lote.numero_lote,
            'calibre': lote.calibre,
            'tipo_municao': lote.get_tipo_municao_display(),
            'quantidade_atual': lote.quantidade_atual,
            'quantidade_estojos': lote.quantidade_estojos,
            'data_validade': lote.data_validade.isoformat() if lote.data_validade else None,
        }
        for lote in lotes
    ]
    return JsonResponse({'lotes': data})


@require_GET
def api_retiradas_pendentes(request):
    retiradas = RetiradaMunicao.objects.all().select_related('material', 'lote', 'policial')
    data = []
    for retirada in retiradas:
        pendente = retirada.quantidade_pendente
        if pendente > 0:
            data.append({
                'id': retirada.id,
                'material': retirada.material.nome,
                'numero': retirada.material.numero,
                'lote_numero': retirada.lote.numero_lote,
                'policial': retirada.policial.nome,
                'quantidade_pendente': pendente,
                'data_hora': retirada.data_hora.strftime('%d/%m/%Y %H:%M'),
            })
    return JsonResponse({'retiradas': data})


@require_GET
@login_required
def api_detalhe_retirada(request, retirada_id):
    """
    Retorna detalhes completos de uma retirada para uso no formulário de devolução.
    Inclui totais de quantidade, pendente, tipo de uso e contexto.
    """
    try:
        retirada = RetiradaMunicao.objects.select_related(
            'material', 'lote', 'policial'
        ).get(pk=retirada_id)
    except RetiradaMunicao.DoesNotExist:
        return JsonResponse({'error': 'Retirada não encontrada.'}, status=404)

    # Calcular totais de devoluções anteriores
    devolucoes = list(retirada.devolucoes.select_related('registro_disparo').all())

    total_devolvido = sum(d.quantidade for d in devolucoes)
    total_disparado = 0
    total_estojos_devolvidos = 0
    total_estojos_extraviados = 0
    total_extraviados = 0
    total_intactos_devolvidos = 0

    for dev in devolucoes:
        registro = getattr(dev, 'registro_disparo', None)
        disparado = registro.quantidade_disparada if registro else 0
        estojos = registro.quantidade_estojos if registro else 0
        estojos_ext = registro.quantidade_estojos_extraviados if registro else 0
        extraviado = registro.quantidade_extraviada if registro else 0
        intacto = max(dev.quantidade - (disparado + extraviado), 0)

        total_disparado += disparado
        total_estojos_devolvidos += estojos
        total_estojos_extraviados += estojos_ext
        total_extraviados += extraviado
        total_intactos_devolvidos += intacto

    pendente = retirada.quantidade_pendente

    return JsonResponse({
        'id': retirada.id,
        'policial': retirada.policial.nome,
        'material': retirada.material.nome,
        'calibre': retirada.lote.calibre,
        'lote': retirada.lote.numero_lote,
        'tipo_uso': retirada.tipo_uso,
        'tipo_uso_display': retirada.get_tipo_uso_display(),
        'finalidade': retirada.finalidade,
        'local_uso': retirada.local_uso or '',
        'data_hora': retirada.data_hora.strftime('%d/%m/%Y %H:%M'),
        # Totais acumulados
        'quantidade_retirada': retirada.quantidade,
        'quantidade_ja_devolvida': total_devolvido,
        'quantidade_pendente': pendente,
        # Breakdown das devoluções anteriores
        'historico': {
            'total_disparado': total_disparado,
            'total_estojos_devolvidos': total_estojos_devolvidos,
            'total_estojos_extraviados': total_estojos_extraviados,
            'total_extraviados': total_extraviados,
            'total_intactos_devolvidos': total_intactos_devolvidos,
        },
    })
