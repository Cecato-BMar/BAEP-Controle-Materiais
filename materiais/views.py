from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Material
from .forms import MaterialForm, MaterialSearchForm

@login_required
def lista_materiais(request):
    form = MaterialSearchForm(request.GET)
    materiais = Material.objects.all()
    
    # Filtragem
    if form.is_valid():
        termo_busca = form.cleaned_data.get('termo_busca')
        tipo = form.cleaned_data.get('tipo')
        status = form.cleaned_data.get('status')
        
        if termo_busca:
            materiais = materiais.filter(
                Q(nome__icontains=termo_busca) | 
                Q(numero__icontains=termo_busca)
            )
        
        if tipo:
            materiais = materiais.filter(tipo=tipo)
            
        if status:
            materiais = materiais.filter(status=status)
    
    # Paginação
    paginator = Paginator(materiais, 10)  # 10 itens por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'total_materiais': materiais.count(),
    }
    
    return render(request, 'materiais/lista_materiais.html', context)

@login_required
def detalhe_material(request, material_id):
    material = get_object_or_404(Material, pk=material_id)
    movimentacoes = material.movimentacoes.all().order_by('-data_hora')[:10]  # Últimas 10 movimentações
    
    context = {
        'material': material,
        'movimentacoes': movimentacoes,
    }
    
    return render(request, 'materiais/detalhe_material.html', context)

@login_required
def novo_material(request):
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.quantidade_disponivel = material.quantidade
            material.save()
            messages.success(request, _('Material cadastrado com sucesso!'))
            return redirect('materiais:detalhe_material', material_id=material.pk)
    else:
        form = MaterialForm()
    
    return render(request, 'materiais/form_material.html', {
        'form': form,
        'titulo': _('Novo Material'),
    })

@login_required
def editar_material(request, material_id):
    material = get_object_or_404(Material, pk=material_id)
    
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, _('Material atualizado com sucesso!'))
            return redirect('materiais:detalhe_material', material_id=material.pk)
    else:
        form = MaterialForm(instance=material)
    
    return render(request, 'materiais/form_material.html', {
        'form': form,
        'material': material,
        'titulo': _('Editar Material'),
    })
