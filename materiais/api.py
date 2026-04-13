from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Material

@login_required
def api_materiais(request):
    """
    API para listar todos os materiais
    """
    # Filtragem opcional
    status = request.GET.get('status', None)
    tipo = request.GET.get('tipo', None)
    categoria = request.GET.get('categoria', None)
    estado = request.GET.get('estado', None)
    localizacao = request.GET.get('localizacao', None)
    termo = request.GET.get('termo', None)
    disponivel = request.GET.get('disponivel', None)
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    
    materiais = Material.objects.all()
    
    # Filtra por status se especificado
    if status:
        materiais = materiais.filter(status=status)
    
    if tipo:
        materiais = materiais.filter(tipo=tipo)
        
    if categoria:
        materiais = materiais.filter(categoria=categoria)
        
    if estado:
        materiais = materiais.filter(estado=estado)
        
    if localizacao:
        materiais = materiais.filter(localizacao_fisica_id=localizacao)
    
    if termo:
        materiais = materiais.filter(
            Q(nome__icontains=termo) | 
            Q(numero__icontains=termo)
        )
    
    if disponivel and disponivel.lower() == 'true':
        materiais = materiais.filter(status='DISPONIVEL', quantidade_disponivel__gt=0)
    
    materiais = materiais.order_by('tipo', 'nome')
    
    # Paginação
    from django.core.paginator import Paginator
    paginator = Paginator(materiais, page_size)
    page_obj = paginator.get_page(page)
    
    materiais_lista = [{
        'id': m.id,
        'nome': m.nome,
        'numero': m.numero,
        'tipo_display': m.get_tipo_display(),
        'categoria_display': m.get_categoria_display() if m.categoria else "",
        'status_display': m.get_status_display(),
        'quantidade_disponivel': m.quantidade_disponivel,
        'estado_display': m.get_estado_display(),
        'localizacao_nome': m.localizacao_fisica.nome if m.localizacao_fisica else "---"
    } for m in page_obj]
    
    data = {
        'results': materiais_lista,
        'pagination': {
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'number': page_obj.number,
            'num_pages': paginator.num_pages,
            'total_items': paginator.count
        }
    }
    
    return JsonResponse(data)

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