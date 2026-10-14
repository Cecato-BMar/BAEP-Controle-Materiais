from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from reserva_baep.decorators import require_module_permission
from .models import TipoUniforme, EntregaUniforme, AlertaUniforme
from .forms import TipoUniformeForm, EntregaUniformeForm


@login_required
@require_module_permission('uniformes')
def dashboard(request):
    """
    Dashboard principal do módulo de Uniformes com KPIs e últimas entregas.
    """
    hoje = timezone.localdate()
    tipos_ativos_count = TipoUniforme.objects.filter(ativo=True).count()
    entregas_ativas_count = EntregaUniforme.objects.filter(ativa=True).count()
    entregas_vencidas_count = EntregaUniforme.objects.filter(
        ativa=True,
        data_vencimento_calc__lt=hoje
    ).count()
    alertas_pendentes_count = AlertaUniforme.objects.filter(lido=False).count()

    ultimas_entregas = EntregaUniforme.objects.select_related(
        'policial',
        'tipo_uniforme',
        'entregue_por'
    ).order_by('-criado_em')[:10]

    context = {
        'tipos_ativos_count': tipos_ativos_count,
        'entregas_ativas_count': entregas_ativas_count,
        'entregas_vencidas_count': entregas_vencidas_count,
        'alertas_pendentes_count': alertas_pendentes_count,
        'ultimas_entregas': ultimas_entregas,
        'hoje': hoje,
    }
    return render(request, 'uniformes/dashboard.html', context)


@login_required
@require_module_permission('uniformes')
def lista_tipos(request):
    """
    Listagem de catálogo de uniformes com filtros e paginação.
    """
    qs = TipoUniforme.objects.all().order_by('nome')

    ativo_filtro = request.GET.get('ativo')
    if ativo_filtro in ['1', 'true', 'True']:
        qs = qs.filter(ativo=True)
    elif ativo_filtro in ['0', 'false', 'False']:
        qs = qs.filter(ativo=False)

    q = request.GET.get('q')
    if q:
        qs = qs.filter(nome__icontains=q.strip())

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'ativo_filtro': ativo_filtro,
        'q': q or '',
    }
    return render(request, 'uniformes/lista_tipos.html', context)


@login_required
@require_module_permission('uniformes')
def criar_tipo(request):
    """
    Cadastra novo tipo de uniforme.
    """
    if request.method == 'POST':
        form = TipoUniformeForm(request.POST)
        if form.is_valid():
            tipo = form.save()
            messages.success(request, f"Tipo de uniforme '{tipo.nome}' criado com sucesso.")
            return redirect('uniformes:lista_tipos')
    else:
        form = TipoUniformeForm()

    return render(request, 'uniformes/form_tipo.html', {'form': form, 'titulo': 'Novo Tipo de Uniforme'})


@login_required
@require_module_permission('uniformes')
def editar_tipo(request, pk):
    """
    Edita tipo de uniforme existente.
    """
    tipo = get_object_or_404(TipoUniforme, pk=pk)
    if request.method == 'POST':
        form = TipoUniformeForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Tipo de uniforme '{tipo.nome}' atualizado com sucesso.")
            return redirect('uniformes:lista_tipos')
    else:
        form = TipoUniformeForm(instance=tipo)

    return render(request, 'uniformes/form_tipo.html', {
        'form': form,
        'tipo': tipo,
        'titulo': f"Editar: {tipo.nome}"
    })


@login_required
@require_module_permission('uniformes')
def lista_entregas(request):
    """
    Listagem de entregas com filtros por status ativa, tipo, vencidas e busca de policial.
    """
    qs = EntregaUniforme.objects.select_related(
        'policial',
        'tipo_uniforme',
        'entregue_por'
    ).all().order_by('-data_entrega', '-criado_em')

    ativa_filtro = request.GET.get('ativa')
    if ativa_filtro in ['1', 'true', 'True']:
        qs = qs.filter(ativa=True)
    elif ativa_filtro in ['0', 'false', 'False']:
        qs = qs.filter(ativa=False)

    tipo_filtro = request.GET.get('tipo')
    if tipo_filtro and tipo_filtro.isdigit():
        qs = qs.filter(tipo_uniforme_id=int(tipo_filtro))

    vencidas_filtro = request.GET.get('vencidas')
    hoje = timezone.localdate()
    if vencidas_filtro == '1':
        qs = qs.filter(ativa=True, data_vencimento_calc__lt=hoje)

    q = request.GET.get('q')
    if q:
        q_clean = q.strip()
        qs = qs.filter(
            Q(policial__nome__icontains=q_clean) |
            Q(policial__re__icontains=q_clean)
        )

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    tipos = TipoUniforme.objects.filter(ativo=True).order_by('nome')

    context = {
        'page_obj': page_obj,
        'tipos': tipos,
        'ativa_filtro': ativa_filtro,
        'tipo_filtro': int(tipo_filtro) if (tipo_filtro and tipo_filtro.isdigit()) else '',
        'vencidas_filtro': vencidas_filtro,
        'q': q or '',
        'hoje': hoje,
    }
    return render(request, 'uniformes/lista_entregas.html', context)


@login_required
@require_module_permission('uniformes')
def criar_entrega(request):
    """
    Registra nova entrega de uniforme, atribuindo request.user em entregue_por.
    """
    if request.method == 'POST':
        form = EntregaUniformeForm(request.POST)
        if form.is_valid():
            entrega = form.save(commit=False)
            entrega.entregue_por = request.user
            entrega.save()
            messages.success(request, f"Entrega de {entrega.tipo_uniforme.nome} registrada com sucesso.")
            return redirect('uniformes:detalhe_entrega', pk=entrega.pk)
    else:
        form = EntregaUniformeForm()

    return render(request, 'uniformes/form_entrega.html', {
        'form': form,
        'titulo': 'Registrar Entrega de Uniforme'
    })


@login_required
@require_module_permission('uniformes')
def editar_entrega(request, pk):
    """
    Edita registro de entrega de uniforme existente.
    """
    entrega = get_object_or_404(EntregaUniforme, pk=pk)
    if request.method == 'POST':
        form = EntregaUniformeForm(request.POST, instance=entrega)
        if form.is_valid():
            form.save()  # entregue_por permanece o original
            messages.success(request, f"Entrega #{entrega.pk} atualizada com sucesso.")
            return redirect('uniformes:detalhe_entrega', pk=entrega.pk)
    else:
        form = EntregaUniformeForm(instance=entrega)

    return render(request, 'uniformes/form_entrega.html', {
        'form': form,
        'entrega': entrega,
        'titulo': f"Editar Entrega #{entrega.pk}"
    })


@login_required
@require_module_permission('uniformes')
def detalhe_entrega(request, pk):
    """
    Visualiza os detalhes completos de uma entrega, histórico de alertas e status.
    """
    entrega = get_object_or_404(
        EntregaUniforme.objects.select_related('policial', 'tipo_uniforme', 'entregue_por'),
        pk=pk
    )
    alertas = entrega.alertas.select_related('lido_por').order_by('-criado_em')

    context = {
        'entrega': entrega,
        'alertas': alertas,
        'hoje': timezone.localdate(),
    }
    return render(request, 'uniformes/detalhe_entrega.html', context)


@login_required
@require_module_permission('uniformes')
@require_POST
def excluir_entrega(request, pk):
    """
    Desativa (ativa=False) o registro de entrega em vez de hard delete, garantindo
    rastreabilidade e evitando erros com integridade relacional PROTECT.
    """
    entrega = get_object_or_404(EntregaUniforme, pk=pk)
    entrega.ativa = False
    entrega.save(update_fields=['ativa', 'atualizado_em'])
    messages.success(
        request,
        f"A entrega de '{entrega.tipo_uniforme.nome}' para '{entrega.policial.nome}' foi desativada/cancelada com sucesso."
    )
    return redirect('uniformes:lista_entregas')


@login_required
@require_module_permission('uniformes')
def lista_alertas(request):
    """
    Listagem paginada de alertas in-app gerados pelo sistema.
    """
    qs = AlertaUniforme.objects.select_related(
        'entrega__policial',
        'entrega__tipo_uniforme',
        'lido_por'
    ).all().order_by('lido', '-criado_em')

    lido_filtro = request.GET.get('lido')
    if lido_filtro in ['0', 'pendente', 'false', 'False']:
        qs = qs.filter(lido=False)
    elif lido_filtro in ['1', 'lido', 'true', 'True']:
        qs = qs.filter(lido=True)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'lido_filtro': lido_filtro or '',
        'pendentes_count': AlertaUniforme.objects.filter(lido=False).count(),
    }
    return render(request, 'uniformes/lista_alertas.html', context)


@login_required
@require_module_permission('uniformes')
@require_POST
def marcar_alerta_lido(request, pk):
    """
    Marca um alerta como lido pelo usuário logado. Suporta AJAX ou redirect convencional.
    """
    alerta = get_object_or_404(AlertaUniforme, pk=pk)
    alerta.marcar_como_lido(request.user)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'success': True,
            'id': alerta.pk,
            'mensagem': 'Alerta marcado como lido com sucesso.'
        })

    messages.success(request, "Alerta marcado como lido.")
    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('uniformes:lista_alertas')
