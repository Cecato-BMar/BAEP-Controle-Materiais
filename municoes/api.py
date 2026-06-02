from django.http import JsonResponse
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
