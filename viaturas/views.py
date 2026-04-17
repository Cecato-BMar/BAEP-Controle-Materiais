from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from decimal import Decimal

from .models import MarcaViatura, ModeloViatura, Viatura, DespachoViatura, Abastecimento, Manutencao, Oficina
from .forms import (ViaturaForm, DespachoSaidaForm, DespachoRetornoForm,
                    AbastecimentoForm, ManutencaoForm, MarcaViaturaForm, 
                    ModeloViaturaForm, OficinaForm)
from reserva_baep.decorators import require_module_permission

FROTA_GROUPS = ['frota', 'reserva_armas']  # grupos com acesso ao módulo


def _has_frota_permission(user):
    """Verifica se o usuário tem acesso ao módulo de frota."""
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=FROTA_GROUPS).exists()


# =============================================================================
# DASHBOARD FROTA
# =============================================================================

@login_required
@require_module_permission('frota')
def dashboard_frota(request):
    total = Viatura.objects.count()
    disponiveis = Viatura.objects.filter(status='DISPONIVEL').count()
    em_uso = Viatura.objects.filter(status='EM_USO').count()
    manutencao = Viatura.objects.filter(status='MANUTENCAO').count()
    baixadas = Viatura.objects.filter(status='BAIXADA').count()

    # Por tipo
    por_tipo = (
        Viatura.objects
        .values('modelo__tipo', 'modelo__tipo')
        .annotate(total=Count('id'))
        .order_by('modelo__tipo')
    )

    # Despachos ativos (sem retorno)
    despachos_ativos = DespachoViatura.objects.filter(data_retorno__isnull=True).select_related(
        'viatura', 'motorista', 'encarregado'
    ).order_by('-data_saida')

    # Manutenções em aberto
    manutencoes_abertas = Manutencao.objects.filter(data_conclusao__isnull=True).select_related('viatura')

    # Últimos abastecimentos
    ultimos_abastecimentos = Abastecimento.objects.select_related('viatura', 'motorista').order_by('-data_abastecimento')[:5]

    context = {
        'total': total,
        'disponiveis': disponiveis,
        'em_uso': em_uso,
        'manutencao': manutencao,
        'baixadas': baixadas,
        'por_tipo': por_tipo,
        'despachos_ativos': despachos_ativos,
        'manutencoes_abertas': manutencoes_abertas,
        'ultimos_abastecimentos': ultimos_abastecimentos,
    }
    return render(request, 'viaturas/dashboard.html', context)


# =============================================================================
# VIATURAS (CRUD)
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_viaturas(request):
    qs = Viatura.objects.select_related('modelo', 'modelo__marca').all()
    tipo = request.GET.get('tipo')
    status = request.GET.get('status')
    q = request.GET.get('q')

    if tipo:
        qs = qs.filter(modelo__tipo=tipo)
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(prefixo__icontains=q) |
            Q(placa__icontains=q) |
            Q(chassi__icontains=q) |
            Q(modelo__nome__icontains=q) |
            Q(modelo__marca__nome__icontains=q)
        )

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    modelos_tipo = ModeloViatura.TIPO_CHOICES

    return render(request, 'viaturas/lista_viaturas.html', {
        'page_obj': page,
        'tipo_filtro': tipo,
        'status_filtro': status,
        'q': q,
        'tipos_choices': modelos_tipo,
        'status_choices': Viatura.STATUS_CHOICES,
    })


@login_required
@require_module_permission('frota')
def criar_viatura(request):
    if request.method == 'POST':
        form = ViaturaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Viatura cadastrada com sucesso!')
            return redirect('viaturas:lista_viaturas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ViaturaForm()
    return render(request, 'viaturas/form_viatura.html', {'form': form, 'titulo': 'Nova Viatura'})


@login_required
@require_module_permission('frota')
def editar_viatura(request, pk):
    viatura = get_object_or_404(Viatura, pk=pk)
    if request.method == 'POST':
        form = ViaturaForm(request.POST, instance=viatura)
        if form.is_valid():
            form.save()
            messages.success(request, f'Viatura {viatura.prefixo} atualizada!')
            return redirect('viaturas:detalhe_viatura', pk=pk)
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ViaturaForm(instance=viatura)
    return render(request, 'viaturas/form_viatura.html', {'form': form, 'titulo': f'Editar {viatura.prefixo}', 'viatura': viatura})


@login_required
@require_module_permission('frota')
def detalhe_viatura(request, pk):
    viatura = get_object_or_404(Viatura.objects.select_related('modelo', 'modelo__marca'), pk=pk)
    despachos = viatura.despachos.select_related('motorista', 'encarregado', 'registrado_por').order_by('-data_saida')[:10]
    abastecimentos = viatura.abastecimentos.select_related('motorista').order_by('-data_abastecimento')[:10]
    manutencoes = viatura.manutencoes.order_by('-data_inicio')[:10]
    despacho_ativo = viatura.despachos.filter(data_retorno__isnull=True).first()

    # Totais
    total_km_rodado = (
        viatura.despachos.filter(km_retorno__isnull=False)
        .aggregate(total=Sum('km_retorno') - Sum('km_saida'))['total'] or Decimal('0')
    )
    total_combustivel = viatura.abastecimentos.aggregate(total=Sum('quantidade_litros'))['total'] or Decimal('0')
    custo_total_manutencao = sum(m.custo_total for m in viatura.manutencoes.all())

    return render(request, 'viaturas/detalhe_viatura.html', {
        'viatura': viatura,
        'despachos': despachos,
        'abastecimentos': abastecimentos,
        'manutencoes': manutencoes,
        'despacho_ativo': despacho_ativo,
        'total_km_rodado': total_km_rodado,
        'total_combustivel': total_combustivel,
        'custo_total_manutencao': custo_total_manutencao,
    })


# =============================================================================
# DESPACHO (SAÍDA / RETORNO)
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_despachos(request):
    qs = DespachoViatura.objects.select_related('viatura', 'motorista', 'encarregado', 'registrado_por').order_by('-data_saida')
    status = request.GET.get('status', 'ativos')

    if status == 'ativos':
        qs = qs.filter(data_retorno__isnull=True)
    elif status == 'concluidos':
        qs = qs.filter(data_retorno__isnull=False)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_despachos.html', {'page_obj': page, 'status_filtro': status})


@login_required
@require_module_permission('frota')
def criar_despacho(request):
    if request.method == 'POST':
        form = DespachoSaidaForm(request.POST)
        if form.is_valid():
            despacho = form.save(commit=False)
            despacho.registrado_por = request.user
            despacho.save()
            # Atualiza status da viatura
            despacho.viatura.status = 'EM_USO'
            despacho.viatura.save()
            messages.success(request, f'Despacho da viatura {despacho.viatura.prefixo} registrado!')
            return redirect('viaturas:lista_despachos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = DespachoSaidaForm()
    return render(request, 'viaturas/form_despacho.html', {'form': form, 'titulo': 'Registrar Despacho (Saída)'})


@login_required
@require_module_permission('frota')
def retorno_despacho(request, pk):
    despacho = get_object_or_404(DespachoViatura, pk=pk, data_retorno__isnull=True)
    if request.method == 'POST':
        form = DespachoRetornoForm(request.POST, instance=despacho)
        if form.is_valid():
            d = form.save(commit=False)
            d.data_retorno = timezone.now()
            d.save()
            # Atualiza odômetro e status da viatura
            viatura = despacho.viatura
            if d.km_retorno:
                viatura.odometro_atual = d.km_retorno
            viatura.status = 'DISPONIVEL'
            viatura.save()
            messages.success(request, f'Retorno da viatura {viatura.prefixo} registrado!')
            return redirect('viaturas:lista_despachos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = DespachoRetornoForm()
    return render(request, 'viaturas/form_retorno.html', {'form': form, 'despacho': despacho})


# =============================================================================
# ABASTECIMENTOS
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_abastecimentos(request):
    qs = Abastecimento.objects.select_related('viatura', 'motorista').order_by('-data_abastecimento')
    viatura_id = request.GET.get('viatura')
    if viatura_id:
        qs = qs.filter(viatura_id=viatura_id)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    viaturas = Viatura.objects.all()
    return render(request, 'viaturas/lista_abastecimentos.html', {
        'page_obj': page, 'viaturas': viaturas, 'viatura_filtro': viatura_id
    })


@login_required
@require_module_permission('frota')
def criar_abastecimento(request):
    if request.method == 'POST':
        form = AbastecimentoForm(request.POST)
        if form.is_valid():
            ab = form.save(commit=False)
            ab.registrado_por = request.user
            ab.save()
            # Atualiza odometro
            if ab.odometro > ab.viatura.odometro_atual:
                ab.viatura.odometro_atual = ab.odometro
                ab.viatura.save()
            messages.success(request, 'Abastecimento registrado com sucesso!')
            return redirect('viaturas:lista_abastecimentos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = AbastecimentoForm()
    return render(request, 'viaturas/form_abastecimento.html', {'form': form, 'titulo': 'Registrar Abastecimento'})


# =============================================================================
# MANUTENÇÕES
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_manutencoes(request):
    qs = Manutencao.objects.select_related('viatura', 'oficina_fk').order_by('-data_inicio')
    status = request.GET.get('status', 'abertas')
    if status == 'abertas':
        qs = qs.filter(data_conclusao__isnull=True)
    elif status == 'concluidas':
        qs = qs.filter(data_conclusao__isnull=False)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_manutencoes.html', {'page_obj': page, 'status_filtro': status})


@login_required
@require_module_permission('frota')
def detalhe_manutencao(request, pk):
    man = get_object_or_404(Manutencao.objects.select_related('viatura', 'oficina_fk', 'registrado_por'), pk=pk)
    return render(request, 'viaturas/detalhe_manutencao.html', {'manutencao': man})


@login_required
@require_module_permission('frota')
def concluir_manutencao(request, pk):
    man = get_object_or_404(Manutencao, pk=pk, data_conclusao__isnull=True)
    man.data_conclusao = timezone.now().date()
    man.status = 'CONCLUIDA'
    man.save()
    
    # Libera a viatura para DISPONIVEL
    viatura = man.viatura
    viatura.status = 'DISPONIVEL'
    viatura.save()
    
    messages.success(request, f'Manutenção da viatura {viatura.prefixo} marcada como concluída!')
    return redirect('viaturas:lista_manutencoes')


@login_required
@require_module_permission('frota')
def criar_manutencao(request):
    if request.method == 'POST':
        form = ManutencaoForm(request.POST)
        if form.is_valid():
            man = form.save(commit=False)
            man.registrado_por = request.user
            man.save()
            # Atualiza status da viatura para manutenção se for o caso
            if man.status in ['ABERTA', 'AGUARDANDO_PECA']:
                man.viatura.status = 'MANUTENCAO'
                man.viatura.save()
            elif man.status == 'CONCLUIDA':
                man.viatura.status = 'DISPONIVEL'
                man.viatura.save()
                
            messages.success(request, 'Manutenção registrada com sucesso!')
            return redirect('viaturas:lista_manutencoes')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ManutencaoForm()
    return render(request, 'viaturas/form_manutencao.html', {'form': form, 'titulo': 'Registrar Manutenção'})


@login_required
@require_module_permission('frota')
def editar_manutencao(request, pk):
    man = get_object_or_404(Manutencao, pk=pk)
    if request.method == 'POST':
        form = ManutencaoForm(request.POST, instance=man)
        if form.is_valid():
            m = form.save()
            # Se manutenção foi concluída ou cancelada, libera a viatura
            if m.status in ['CONCLUIDA', 'CANCELADA']:
                m.viatura.status = 'DISPONIVEL'
                m.viatura.save()
            elif m.status in ['ABERTA', 'AGUARDANDO_PECA']:
                m.viatura.status = 'MANUTENCAO'
                m.viatura.save()
                
            messages.success(request, 'Manutenção atualizada!')
            return redirect('viaturas:lista_manutencoes')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ManutencaoForm(instance=man)
    return render(request, 'viaturas/form_manutencao.html', {'form': form, 'titulo': 'Editar Manutenção', 'manutencao': man})

# =============================================================================
# MARCAS E MODELOS (AUXILIARES)
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_marcas(request):
    qs = MarcaViatura.objects.annotate(count_modelos=Count('modelos')).all()
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_marcas.html', {'page_obj': page})


@login_required
@require_module_permission('frota')
def criar_marca(request):
    if request.method == 'POST':
        form = MarcaViaturaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Marca cadastrada com sucesso!')
            return redirect('viaturas:lista_marcas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = MarcaViaturaForm()
    return render(request, 'viaturas/form_marca.html', {'form': form, 'titulo': 'Nova Marca'})


@login_required
@require_module_permission('frota')
def editar_marca(request, pk):
    marca = get_object_or_404(MarcaViatura, pk=pk)
    if request.method == 'POST':
        form = MarcaViaturaForm(request.POST, instance=marca)
        if form.is_valid():
            form.save()
            messages.success(request, f'Marca {marca.nome} atualizada!')
            return redirect('viaturas:lista_marcas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = MarcaViaturaForm(instance=marca)
    return render(request, 'viaturas/form_marca.html', {'form': form, 'titulo': f'Editar {marca.nome}'})


@login_required
@require_module_permission('frota')
def lista_modelos(request):
    qs = ModeloViatura.objects.select_related('marca').annotate(count_viaturas=Count('viaturas')).all()
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_modelos.html', {'page_obj': page})


@login_required
@require_module_permission('frota')
def criar_modelo(request):
    if request.method == 'POST':
        form = ModeloViaturaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Modelo cadastrado com sucesso!')
            return redirect('viaturas:lista_modelos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ModeloViaturaForm()
    return render(request, 'viaturas/form_modelo.html', {'form': form, 'titulo': 'Novo Modelo'})


@login_required
@require_module_permission('frota')
def editar_modelo(request, pk):
    modelo = get_object_or_404(ModeloViatura, pk=pk)
    if request.method == 'POST':
        form = ModeloViaturaForm(request.POST, instance=modelo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Modelo {modelo.nome} atualizado!')
            return redirect('viaturas:lista_modelos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ModeloViaturaForm(instance=modelo)
    return render(request, 'viaturas/form_modelo.html', {'form': form, 'titulo': f'Editar {modelo.nome}'})


# =============================================================================
# OFICINAS
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_oficinas(request):
    qs = Oficina.objects.annotate(total_manutencoes=Count('manutencoes')).all()
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_oficinas.html', {'page_obj': page})


@login_required
@require_module_permission('frota')
def criar_oficina(request):
    if request.method == 'POST':
        form = OficinaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Oficina cadastrada com sucesso!')
            return redirect('viaturas:lista_oficinas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = OficinaForm()
    return render(request, 'viaturas/form_oficina.html', {'form': form, 'titulo': 'Nova Oficina'})


@login_required
@require_module_permission('frota')
def editar_oficina(request, pk):
    oficina = get_object_or_404(Oficina, pk=pk)
    if request.method == 'POST':
        form = OficinaForm(request.POST, instance=oficina)
        if form.is_valid():
            form.save()
            messages.success(request, f'Oficina {oficina.nome} atualizada!')
            return redirect('viaturas:lista_oficinas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = OficinaForm(instance=oficina)
    return render(request, 'viaturas/form_oficina.html', {'form': form, 'titulo': f'Editar {oficina.nome}'})
