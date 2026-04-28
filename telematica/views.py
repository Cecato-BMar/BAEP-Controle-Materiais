from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator

from .models import (CategoriaEquipamento, Equipamento, ConfiguracaoRadio, 
                     LinhaMovel, ServicoTI, ManutencaoTI)
from .forms import (CategoriaEquipamentoForm, EquipamentoForm, ConfiguracaoRadioForm, 
                    LinhaMovelForm, ServicoTIForm, ManutencaoTIForm)
from reserva_baep.decorators import require_module_permission

@login_required
@require_module_permission('telematica')
def dashboard_telematica(request):
    total_equipamentos = Equipamento.objects.count()
    operacionais = Equipamento.objects.filter(status='OPERACIONAL').count()
    em_manutencao = Equipamento.objects.filter(status='MANUTENCAO').count()
    
    por_categoria = Equipamento.objects.values('categoria__nome', 'categoria__icone').annotate(total=Count('id')).order_by('-total')
    ultimas_manutencoes = ManutencaoTI.objects.select_related('equipamento').order_by('-data_inicio')[:5]
    servicos_ativos = ServicoTI.objects.filter(status=True).count()
    
    # Alertas
    hoje = timezone.now().date()
    garantias_vencendo = Equipamento.objects.filter(vencimento_garantia__lte=hoje + timezone.timedelta(days=30), status='OPERACIONAL').count()
    
    context = {
        'total_equipamentos': total_equipamentos,
        'operacionais': operacionais,
        'em_manutencao': em_manutencao,
        'por_categoria': por_categoria,
        'ultimas_manutencoes': ultimas_manutencoes,
        'servicos_ativos': servicos_ativos,
        'garantias_vencendo': garantias_vencendo,
    }
    return render(request, 'telematica/dashboard.html', context)

# EQUIPAMENTOS
@login_required
@require_module_permission('telematica')
def lista_equipamentos(request):
    q = request.GET.get('q', '')
    cat = request.GET.get('categoria', '')
    qs = Equipamento.objects.select_related('categoria').all()
    
    if q:
        qs = qs.filter(
            Q(hostname__icontains=q) | 
            Q(numero_serie__icontains=q) | 
            Q(patrimonio__icontains=q) |
            Q(marca__icontains=q) |
            Q(modelo__icontains=q)
        )
    if cat:
        qs = qs.filter(categoria_id=cat)
        
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    categorias = CategoriaEquipamento.objects.all()
    
    return render(request, 'telematica/lista_equipamentos.html', {
        'page_obj': page,
        'q': q,
        'categorias': categorias,
        'categoria_filtro': cat
    })

@login_required
@require_module_permission('telematica')
def detalhe_equipamento(request, pk):
    equipamento = get_object_or_404(Equipamento.objects.select_related('categoria'), pk=pk)
    manutencoes = equipamento.manutencoes_ti.all().order_by('-data_inicio')
    return render(request, 'telematica/detalhe_equipamento.html', {
        'equipamento': equipamento,
        'manutencoes': manutencoes
    })

@login_required
@require_module_permission('telematica')
def criar_equipamento(request):
    if request.method == 'POST':
        form = EquipamentoForm(request.POST)
        if form.is_valid():
            equip = form.save(commit=False)
            equip.registrado_por = request.user
            # Força o status inicial como OPERACIONAL se for um novo cadastro
            # a menos que o usuário tenha escolhido explicitamente outro
            if not equip.status:
                equip.status = 'OPERACIONAL'
            equip.save()
            messages.success(request, 'Equipamento cadastrado com sucesso!')
            return redirect('telematica:lista_equipamentos')
    else:
        form = EquipamentoForm()
    return render(request, 'telematica/form_equipamento.html', {'form': form, 'titulo': 'Novo Equipamento'})

@login_required
@require_module_permission('telematica')
def editar_equipamento(request, pk):
    equipamento = get_object_or_404(Equipamento, pk=pk)
    if request.method == 'POST':
        form = EquipamentoForm(request.POST, instance=equipamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipamento atualizado!')
            return redirect('telematica:detalhe_equipamento', pk=pk)
    else:
        form = EquipamentoForm(instance=equipamento)
    return render(request, 'telematica/form_equipamento.html', {'form': form, 'titulo': f'Editar {equipamento.hostname or equipamento.numero_serie}'})

@login_required
@require_module_permission('telematica')
def excluir_equipamento(request, pk):
    equipamento = get_object_or_404(Equipamento, pk=pk)
    if request.method == 'POST':
        try:
            equipamento.delete()
            messages.success(request, 'Equipamento excluído com sucesso.')
        except Exception as e:
            messages.error(request, f'Erro ao excluir: {e}')
        return redirect('telematica:lista_equipamentos')
    return render(request, 'telematica/confirmar_exclusao.html', {'objeto': equipamento, 'url_voltar': 'telematica:lista_equipamentos'})

# MANUTENÇÕES
@login_required
@require_module_permission('telematica')
def lista_manutencoes(request):
    qs = ManutencaoTI.objects.select_related('equipamento', 'equipamento__categoria').all()
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'telematica/lista_manutencoes.html', {'page_obj': page})

@login_required
@require_module_permission('telematica')
def criar_manutencao(request):
    equip_id = request.GET.get('equipamento')
    initial = {}
    if equip_id:
        initial['equipamento'] = get_object_or_404(Equipamento, pk=equip_id)
        
    if request.method == 'POST':
        form = ManutencaoTIForm(request.POST)
        if form.is_valid():
            mnt = form.save(commit=False)
            mnt.registrado_por = request.user
            mnt.save()
            messages.success(request, 'Manutenção registrada!')
            return redirect('telematica:lista_manutencoes')
    else:
        form = ManutencaoTIForm(initial=initial)
    return render(request, 'telematica/form_manutencao.html', {'form': form, 'titulo': 'Registrar Manutenção'})

@login_required
@require_module_permission('telematica')
def editar_manutencao(request, pk):
    mnt = get_object_or_404(ManutencaoTI, pk=pk)
    if request.method == 'POST':
        form = ManutencaoTIForm(request.POST, instance=mnt)
        if form.is_valid():
            form.save()
            messages.success(request, 'Manutenção atualizada!')
            return redirect('telematica:lista_manutencoes')
    else:
        form = ManutencaoTIForm(instance=mnt)
    return render(request, 'telematica/form_manutencao.html', {'form': form, 'titulo': 'Editar Manutenção'})

@login_required
@require_module_permission('telematica')
def excluir_manutencao(request, pk):
    mnt = get_object_or_404(ManutencaoTI, pk=pk)
    if request.method == 'POST':
        mnt.delete()
        messages.success(request, 'Registro de manutenção excluído.')
        return redirect('telematica:lista_manutencoes')
    return render(request, 'telematica/confirmar_exclusao.html', {'objeto': mnt, 'url_voltar': 'telematica:lista_manutencoes'})

# SERVIÇOS
@login_required
@require_module_permission('telematica')
def lista_servicos(request):
    servicos = ServicoTI.objects.all()
    return render(request, 'telematica/lista_servicos.html', {'servicos': servicos})

@login_required
@require_module_permission('telematica')
def excluir_servico(request, pk):
    servico = get_object_or_404(ServicoTI, pk=pk)
    if request.method == 'POST':
        servico.delete()
        messages.success(request, 'Serviço excluído.')
        return redirect('telematica:lista_servicos')
    return render(request, 'telematica/confirmar_exclusao.html', {'objeto': servico, 'url_voltar': 'telematica:lista_servicos'})

# LINHAS MÓVEIS
@login_required
@require_module_permission('telematica')
def lista_linhas(request):
    q = request.GET.get('q', '')
    qs = LinhaMovel.objects.select_related('equipamento_vinculado', 'policial_responsavel').all()
    if q:
        qs = qs.filter(Q(numero__icontains=q) | Q(iccid__icontains=q) | Q(imei_1__icontains=q))
    return render(request, 'telematica/lista_linhas.html', {'linhas': qs, 'q': q})

@login_required
@require_module_permission('telematica')
def criar_linha(request):
    if request.method == 'POST':
        form = LinhaMovelForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Linha móvel cadastrada!')
            return redirect('telematica:lista_linhas')
    else:
        form = LinhaMovelForm()
    return render(request, 'telematica/form_linha.html', {'form': form, 'titulo': 'Nova Linha Móvel'})

@login_required
@require_module_permission('telematica')
def editar_linha(request, pk):
    linha = get_object_or_404(LinhaMovel, pk=pk)
    if request.method == 'POST':
        form = LinhaMovelForm(request.POST, instance=linha)
        if form.is_valid():
            form.save()
            messages.success(request, 'Linha móvel atualizada!')
            return redirect('telematica:lista_linhas')
    else:
        form = LinhaMovelForm(instance=linha)
    return render(request, 'telematica/form_linha.html', {'form': form, 'titulo': f'Editar Linha {linha.numero}'})

@login_required
@require_module_permission('telematica')
def excluir_linha(request, pk):
    linha = get_object_or_404(LinhaMovel, pk=pk)
    if request.method == 'POST':
        linha.delete()
        messages.success(request, 'Linha móvel excluída.')
        return redirect('telematica:lista_linhas')
    return render(request, 'telematica/confirmar_exclusao.html', {'objeto': linha, 'url_voltar': 'telematica:lista_linhas'})

# SERVIÇOS (CRUD)
@login_required
@require_module_permission('telematica')
def criar_servico(request):
    if request.method == 'POST':
        form = ServicoTIForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Serviço cadastrado!')
            return redirect('telematica:lista_servicos')
    else:
        form = ServicoTIForm()
    return render(request, 'telematica/form_servico.html', {'form': form, 'titulo': 'Novo Serviço de TI'})

@login_required
@require_module_permission('telematica')
def editar_servico(request, pk):
    servico = get_object_or_404(ServicoTI, pk=pk)
    if request.method == 'POST':
        form = ServicoTIForm(request.POST, instance=servico)
        if form.is_valid():
            form.save()
            messages.success(request, 'Serviço atualizado!')
            return redirect('telematica:lista_servicos')
    else:
        form = ServicoTIForm(instance=servico)
    return render(request, 'telematica/form_servico.html', {'form': form, 'titulo': f'Editar {servico.nome}'})

# CATEGORIAS (CRUD RÁPIDO)
@login_required
@require_module_permission('telematica')
def lista_categorias(request):
    categorias = CategoriaEquipamento.objects.annotate(total=Count('equipamentos'))
    return render(request, 'telematica/lista_categorias.html', {'categorias': categorias})

@login_required
@require_module_permission('telematica')
def criar_categoria(request):
    if request.method == 'POST':
        form = CategoriaEquipamentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria criada!')
            return redirect('telematica:lista_categorias')
    else:
        form = CategoriaEquipamentoForm()
    return render(request, 'telematica/form_categoria.html', {'form': form, 'titulo': 'Nova Categoria'})

@login_required
@require_module_permission('telematica')
def editar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaEquipamento, pk=pk)
    if request.method == 'POST':
        form = CategoriaEquipamentoForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria atualizada!')
            return redirect('telematica:lista_categorias')
    else:
        form = CategoriaEquipamentoForm(instance=categoria)
    return render(request, 'telematica/form_categoria.html', {'form': form, 'titulo': 'Editar Categoria'})

@login_required
@require_module_permission('telematica')
def excluir_categoria(request, pk):
    categoria = get_object_or_404(CategoriaEquipamento, pk=pk)
    if request.method == 'POST':
        try:
            categoria.delete()
            messages.success(request, 'Categoria excluída.')
        except Exception:
            messages.error(request, 'Não é possível excluir categorias que possuem equipamentos vinculados.')
        return redirect('telematica:lista_categorias')
    return render(request, 'telematica/confirmar_exclusao.html', {'objeto': categoria, 'url_voltar': 'telematica:lista_categorias'})
from django.http import JsonResponse
from django.views.decorators.http import require_GET

@login_required
@require_GET
def buscar_equipamentos_ajax(request):
    """Busca de equipamentos para autocomplete"""
    q = request.GET.get('q', '')
    qs = Equipamento.objects.filter(
        Q(hostname__icontains=q) | 
        Q(numero_serie__icontains=q) | 
        Q(patrimonio__icontains=q) |
        Q(marca__icontains=q)
    )[:15]
    data = [{'id': e.pk, 'text': f"{e.hostname or 'S/H'} — {e.numero_serie} ({e.categoria.nome})"} for e in qs]
    return JsonResponse({'results': data})
