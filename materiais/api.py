from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.http import JsonResponse

from .models import LoteMunicao, Material

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


def _parse_positive_int(raw_value, default, field_name, max_value=None):
    if raw_value in (None, ''):
        return default

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f'Parâmetro {field_name} inválido.')

    if value < 1:
        raise ValueError(f'Parâmetro {field_name} inválido.')

    if max_value is not None and value > max_value:
        raise ValueError(f'Parâmetro {field_name} não pode ser maior que {max_value}.')

    return value


@login_required
def api_materiais(request):
    """
    API para listar todos os materiais
    """
    try:
        page = _parse_positive_int(request.GET.get('page'), 1, 'page')
        page_size = _parse_positive_int(
            request.GET.get('page_size'),
            DEFAULT_PAGE_SIZE,
            'page_size',
            MAX_PAGE_SIZE,
        )
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    status = request.GET.get('status', None)
    tipo = request.GET.get('tipo', None)
    categoria = request.GET.get('categoria', None)
    estado = request.GET.get('estado', None)
    localizacao = request.GET.get('localizacao', None)
    termo = request.GET.get('termo', None)
    disponivel = request.GET.get('disponivel', None)

    materiais = (
        Material.objects.select_related('localizacao_fisica')
        .prefetch_related(
            Prefetch(
                'lotes',
                queryset=LoteMunicao.objects.filter(ativo=True).order_by('data_validade', 'numero_lote'),
            )
        )
    )

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
        materiais = materiais.filter(Q(nome__icontains=termo) | Q(numero__icontains=termo))

    if disponivel and disponivel.lower() == 'true':
        materiais = materiais.filter(status='DISPONIVEL', quantidade_disponivel__gt=0)

    materiais = materiais.order_by('tipo', 'nome')

    paginator = Paginator(materiais, page_size)
    page_obj = paginator.get_page(page)

    materiais_lista = []
    for material in page_obj:
        item = {
            'id': material.id,
            'nome': material.nome,
            'numero': material.numero,
            'tipo': material.tipo,
            'tipo_display': material.get_tipo_display(),
            'categoria_display': material.get_categoria_display() if material.categoria else '',
            'status_display': material.get_status_display(),
            'quantidade_disponivel': material.quantidade_disponivel,
            'estado_display': material.get_estado_display(),
            'localizacao_nome': material.localizacao_fisica.nome if material.localizacao_fisica else '---',
        }

        if material.tipo == 'MUNICAO':
            item['lotes'] = [
                {
                    'id': lote.id,
                    'calibre': lote.calibre,
                    'marca': lote.marca,
                    'numero_lote': lote.numero_lote,
                    'tipo_municao': lote.tipo_municao,
                    'tipo_municao_display': lote.get_tipo_municao_display(),
                    'data_fabricacao': lote.data_fabricacao.isoformat() if lote.data_fabricacao else None,
                    'data_validade': lote.data_validade.isoformat() if lote.data_validade else None,
                    'quantidade_atual': lote.quantidade_atual,
                }
                for lote in material.lotes.all()
            ]

        materiais_lista.append(item)

    data = {
        'results': materiais_lista,
        'pagination': {
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'number': page_obj.number,
            'num_pages': paginator.num_pages,
            'total_items': paginator.count,
        },
    }

    return JsonResponse(data)


@login_required
def api_material_detalhe(request, material_id):
    """
    API para obter detalhes de um material específico
    """
    try:
        material = Material.objects.select_related('localizacao_fisica').get(pk=material_id)

        material_data = {
            'id': material.id,
            'nome': material.nome,
            'identificacao': material.numero,
            'numero': material.numero,
            'tipo': material.tipo,
            'tipo_display': material.get_tipo_display(),
            'status': material.status,
            'status_display': material.get_status_display(),
            'quantidade_total': material.quantidade,
            'quantidade_disponivel': material.quantidade_disponivel,
            'quantidade_em_uso': material.quantidade_em_uso,
            'estado': material.estado,
            'estado_display': material.get_estado_display(),
            'observacoes': material.observacoes,
            'localizacao_nome': material.localizacao_fisica.nome if material.localizacao_fisica else '---',
        }

        return JsonResponse(material_data)
    except Material.DoesNotExist:
        return JsonResponse({'error': 'Material não encontrado'}, status=404)


@login_required
def api_lotes_material(request, material_id):
    """
    API para obter lotes ativos de um material específico
    """
    lotes = (
        LoteMunicao.objects.filter(material_id=material_id, ativo=True, quantidade_atual__gt=0)
        .order_by('data_validade')
    )

    lotes_lista = [
        {
            'id': lote.id,
            'numero_lote': lote.numero_lote,
            'marca': lote.marca,
            'calibre': lote.calibre,
            'quantidade_atual': lote.quantidade_atual,
            'data_validade': lote.data_validade.strftime('%d/%m/%Y') if lote.data_validade else 'Sem validade',
            'vencido': lote.vencido,
        }
        for lote in lotes
    ]

    return JsonResponse({'lotes': lotes_lista})
