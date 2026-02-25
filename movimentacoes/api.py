from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Movimentacao, Retirada, Devolucao

@login_required
def api_retirada_detalhe(request, retirada_id):
    """
    API para obter detalhes de uma retirada específica
    """
    retirada = get_object_or_404(Retirada, pk=retirada_id)
    movimentacao = retirada.movimentacao
    
    # Calcula a quantidade já devolvida deste material para esta retirada
    devolucoes = Devolucao.objects.filter(retirada_referencia=retirada)
    quantidade_devolvida = sum(d.movimentacao.quantidade for d in devolucoes)
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
            'identificacao': movimentacao.material.numero,  # Usando numero como identificacao
            'numero': movimentacao.material.numero,
            'tipo': movimentacao.material.tipo,
            'tipo_display': movimentacao.material.get_tipo_display(),
        },
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
    policial_id = request.GET.get('policial_id')
    material_id = request.GET.get('material_id')
    
    # Filtra as movimentações de retirada
    movimentacoes_retirada = Movimentacao.objects.filter(tipo='RETIRADA')
    
    if policial_id:
        movimentacoes_retirada = movimentacoes_retirada.filter(policial_id=policial_id)
    
    if material_id:
        movimentacoes_retirada = movimentacoes_retirada.filter(material_id=material_id)
    
    movimentacoes_retirada = movimentacoes_retirada.select_related('material', 'policial', 'retirada')
    
    retiradas_pendentes = []
    
    for mov in movimentacoes_retirada:
        # Verifica se a retirada tem uma referência válida
        if not hasattr(mov, 'retirada'):
            continue
            
        # Calcula a quantidade já devolvida deste material para esta retirada
        devolucoes = Devolucao.objects.filter(retirada_referencia=mov.retirada)
        quantidade_devolvida = sum(d.movimentacao.quantidade for d in devolucoes)
        
        # Se ainda há quantidade pendente de devolução
        if quantidade_devolvida < mov.quantidade:
            quantidade_pendente = mov.quantidade - quantidade_devolvida
            
            retiradas_pendentes.append({
                'id': mov.retirada.id,
                'material': {
                    'id': mov.material.id,
                    'nome': mov.material.nome,
                    'identificacao': mov.material.numero,  # Usando numero como identificacao
                    'tipo_display': mov.material.get_tipo_display(),
                },
                'policial': {
                    'id': mov.policial.id,
                    're': mov.policial.re,
                    'nome': mov.policial.nome,
                },
                'data_hora': mov.data_hora.strftime('%d/%m/%Y %H:%M'),
                'finalidade': mov.retirada.finalidade,
                'quantidade_retirada': mov.quantidade,
                'quantidade_devolvida': quantidade_devolvida,
                'quantidade_pendente': quantidade_pendente,
            })
    
    return JsonResponse(retiradas_pendentes, safe=False)