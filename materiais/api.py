from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Material

@login_required
def api_materiais(request):
    """
    API para listar todos os materiais
    """
    # Filtragem opcional por status
    status = request.GET.get('status', None)
    tipo = request.GET.get('tipo', None)
    termo = request.GET.get('termo', None)
    disponivel = request.GET.get('disponivel', None)
    
    materiais = Material.objects.all()
    
    # Filtra por status se especificado
    if status:
        materiais = materiais.filter(status=status)
    
    # Filtra por tipo se especificado
    if tipo:
        materiais = materiais.filter(tipo=tipo)
    
    # Filtra por termo de busca se especificado
    if termo:
        materiais = materiais.filter(
            Q(nome__icontains=termo) | 
            Q(numero__icontains=termo)
        )
    
    # Filtra apenas materiais disponíveis se solicitado
    if disponivel and disponivel.lower() == 'true':
        materiais = materiais.filter(status='DISPONIVEL', quantidade_disponivel__gt=0)
    
    # Ordena os materiais por tipo e nome
    materiais = materiais.order_by('tipo', 'nome')
    
    materiais_lista = [{
        'id': m.id,
        'nome': m.nome,
        'identificacao': m.numero,  # Usando numero como identificacao
        'numero': m.numero,
        'tipo': m.tipo,
        'tipo_display': m.get_tipo_display(),
        'status': m.status,
        'status_display': m.get_status_display(),
        'quantidade_total': m.quantidade,  # Corrigido para quantidade
        'quantidade_disponivel': m.quantidade_disponivel,
        'quantidade_em_uso': m.quantidade_em_uso,
        'estado': m.estado,
        'estado_display': m.get_estado_display()
    } for m in materiais]
    
    # Garante que a resposta seja um array JSON válido
    response = JsonResponse(materiais_lista, safe=False)
    response['Content-Type'] = 'application/json'
    return response

@login_required
def api_material_detalhe(request, material_id):
    """
    API para obter detalhes de um material específico
    """
    try:
        material = Material.objects.get(pk=material_id)
        
        material_data = {
            'id': material.id,
            'nome': material.nome,
            'identificacao': material.numero,  # Usando numero como identificacao
            'numero': material.numero,
            'tipo': material.tipo,
            'tipo_display': material.get_tipo_display(),
            'status': material.status,
            'status_display': material.get_status_display(),
            'quantidade_total': material.quantidade,  # Corrigido para quantidade
            'quantidade_disponivel': material.quantidade_disponivel,
            'quantidade_em_uso': material.quantidade_em_uso,
            'estado': material.estado,
            'estado_display': material.get_estado_display(),
            'observacoes': material.observacoes
        }
        
        return JsonResponse(material_data)
    except Material.DoesNotExist:
        return JsonResponse({'error': 'Material não encontrado'}, status=404)