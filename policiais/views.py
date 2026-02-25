from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Policial
from .forms import PolicialForm, PolicialSearchForm

@login_required
def lista_policiais(request):
    form = PolicialSearchForm(request.GET)
    policiais = Policial.objects.all()
    
    # Filtragem
    if form.is_valid():
        termo_busca = form.cleaned_data.get('termo_busca')
        posto = form.cleaned_data.get('posto')
        situacao = form.cleaned_data.get('situacao')
        
        if termo_busca:
            policiais = policiais.filter(
                Q(nome__icontains=termo_busca) | 
                Q(re__icontains=termo_busca)
            )
        
        if posto:
            policiais = policiais.filter(posto=posto)
            
        if situacao:
            policiais = policiais.filter(situacao=situacao)
    
    # Paginação
    paginator = Paginator(policiais, 10)  # 10 itens por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'total_policiais': policiais.count(),
    }
    
    return render(request, 'policiais/lista_policiais.html', context)

@login_required
def detalhe_policial(request, policial_id):
    policial = get_object_or_404(Policial, pk=policial_id)
    movimentacoes = policial.movimentacoes.all().order_by('-data_hora')[:10]  # Últimas 10 movimentações
    
    context = {
        'policial': policial,
        'movimentacoes': movimentacoes,
    }
    
    return render(request, 'policiais/detalhe_policial.html', context)

@login_required
def novo_policial(request):
    if request.method == 'POST':
        form = PolicialForm(request.POST, request.FILES)
        if form.is_valid():
            policial = form.save()
            messages.success(request, _('Policial cadastrado com sucesso!'))
            return redirect('policiais:detalhe_policial', policial_id=policial.pk)
    else:
        form = PolicialForm()
    
    return render(request, 'policiais/form_policial.html', {
        'form': form,
        'titulo': _('Novo Policial'),
    })

@login_required
def editar_policial(request, policial_id):
    policial = get_object_or_404(Policial, pk=policial_id)
    
    if request.method == 'POST':
        form = PolicialForm(request.POST, request.FILES, instance=policial)
        if form.is_valid():
            form.save()
            messages.success(request, _('Policial atualizado com sucesso!'))
            return redirect('policiais:detalhe_policial', policial_id=policial.pk)
    else:
        form = PolicialForm(instance=policial)
    
    return render(request, 'policiais/form_policial.html', {
        'form': form,
        'policial': policial,
        'titulo': _('Editar Policial'),
    })
