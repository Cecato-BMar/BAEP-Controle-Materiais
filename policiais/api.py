from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Policial

@login_required
def api_policiais(request):
    """
    API para listar todos os policiais ativos
    """
    policiais = Policial.objects.filter(situacao='ATIVO')
    
    policiais_lista = [{
        'id': p.id,
        're': p.re,
        'nome': p.nome,
        'posto': p.posto,
        'situacao': p.situacao
    } for p in policiais]
    
    return JsonResponse(policiais_lista, safe=False)

@login_required
def api_policial_detalhe(request, policial_id):
    """
    API para obter detalhes de um policial específico
    """
    try:
        policial = Policial.objects.get(pk=policial_id)
        
        policial_data = {
            'id': policial.id,
            're': policial.re,
            'nome': policial.nome,
            'posto': policial.posto,
            'posto_display': policial.get_posto_display(),
            'situacao': policial.situacao,
            'data_nascimento': policial.data_nascimento.strftime('%Y-%m-%d') if hasattr(policial, 'data_nascimento') and policial.data_nascimento else None,
            'data_ingresso': policial.data_ingresso.strftime('%Y-%m-%d') if hasattr(policial, 'data_ingresso') and policial.data_ingresso else None,
            'email': policial.email if hasattr(policial, 'email') else None,
            'telefone': policial.telefone if hasattr(policial, 'telefone') else None,
            'foto': policial.foto.url if policial.foto else None
        }
        
        return JsonResponse(policial_data)
    except Policial.DoesNotExist:
        return JsonResponse({'error': 'Policial não encontrado'}, status=404)