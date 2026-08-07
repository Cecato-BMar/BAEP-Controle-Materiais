from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import LoteMunicao, RetiradaMunicao


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


def api_retirada_detalhe(request, retirada_id):
    retirada = get_object_or_404(
        RetiradaMunicao.objects.select_related('material', 'lote', 'policial'),
        pk=retirada_id
    )
    devolucoes = list(retirada.devolucoes.select_related('registro_disparo'))

    total_ja_devolvido = sum(d.quantidade for d in devolucoes)
    total_intactos = 0
    total_disparado = 0
    total_estojos = 0
    total_estojos_extraviados = 0
    total_extraviados = 0

    for dev in devolucoes:
        reg = getattr(dev, 'registro_disparo', None)
        disp = reg.quantidade_disparada if reg else 0
        ext = reg.quantidade_extraviada if reg else 0
        est = reg.quantidade_estojos if reg else 0
        est_ext = reg.quantidade_estojos_extraviados if reg else 0
        intact = max(dev.quantidade - (disp + ext), 0)

        total_intactos += intact
        total_disparado += disp
        total_estojos += est
        total_estojos_extraviados += est_ext
        total_extraviados += ext

    data = {
        'id': retirada.id,
        'policial': retirada.policial.nome,
        'material': retirada.material.nome,
        'calibre': retirada.lote.calibre,
        'lote': retirada.lote.numero_lote,
        'data_hora': retirada.data_hora.strftime('%d/%m/%Y %H:%M'),
        'finalidade': retirada.finalidade,
        'tipo_uso': retirada.tipo_uso,
        'tipo_uso_display': retirada.get_tipo_uso_display(),
        'quantidade_retirada': retirada.quantidade,
        'quantidade_ja_devolvida': total_ja_devolvido,
        'quantidade_pendente': max(retirada.quantidade - total_ja_devolvido, 0),
        'historico': {
            'total_intactos_devolvidos': total_intactos,
            'total_disparado': total_disparado,
            'total_estojos_devolvidos': total_estojos,
            'total_estojos_extraviados': total_estojos_extraviados,
            'total_extraviados': total_extraviados,
        }
    }
    return JsonResponse(data)

