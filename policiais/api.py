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
    API para obter detalhes de um policial específico.
    Inclui foto_url para uso no painel de preview do formulário de retirada.
    """
    try:
        policial = Policial.objects.get(pk=policial_id)

        foto_url = None
        if policial.foto:
            try:
                foto_url = request.build_absolute_uri(policial.foto.url)
            except Exception:
                foto_url = policial.foto.url

        policial_data = {
            'id': policial.id,
            're': policial.re,
            'nome': policial.nome,
            'posto': policial.posto,
            'posto_display': policial.get_posto_display(),
            'situacao': policial.situacao,
            'foto_url': foto_url,
        }
        
        return JsonResponse(policial_data)
    except Policial.DoesNotExist:
        return JsonResponse({'error': 'Policial não encontrado'}, status=404)