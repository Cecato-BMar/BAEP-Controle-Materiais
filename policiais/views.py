from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from reserva_baep.decorators import require_module_permission
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator
from .models import Policial
from .forms import PolicialForm, PolicialSearchForm
from django.http import JsonResponse
import xlrd
from django.db import transaction
import os

@login_required
@require_module_permission('reserva_armas')
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
@require_module_permission('reserva_armas')
def detalhe_policial(request, policial_id):
    policial = get_object_or_404(Policial, pk=policial_id)
    movimentacoes = policial.movimentacoes.all().order_by('-data_hora')[:10]  # Últimas 10 movimentações
    
    context = {
        'policial': policial,
        'movimentacoes': movimentacoes,
    }
    
    return render(request, 'policiais/detalhe_policial.html', context)

@login_required
@require_module_permission('reserva_armas')
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
@require_module_permission('reserva_armas')
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

@login_required
@require_module_permission('reserva_armas')
def importar_policiais_excel(request):
    if request.method == 'POST':
        xls_file = request.FILES.get('arquivo_excel')
        
        # Se não enviou arquivo no POST, mas clicou em importar, tenta o arquivo padrão no disco
        if not xls_file:
            path_padrao = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Efetivo - MARÇO.xls')
            if os.path.exists(path_padrao):
                try:
                    workbook = xlrd.open_workbook(path_padrao)
                except Exception as e:
                    messages.error(request, f"Erro ao abrir arquivo padrão: {e}")
                    return redirect('policiais:lista_policiais')
            else:
                messages.error(request, "Nenhum arquivo enviado e arquivo padrão 'Efetivo - MARÇO.xls' não encontrado.")
                return redirect('policiais:lista_policiais')
        else:
            # Ler arquivo do upload
            try:
                # xlrd precisa de um path ou file_contents
                workbook = xlrd.open_workbook(file_contents=xls_file.read())
            except Exception as e:
                messages.error(request, f"Erro ao ler arquivo enviado: {e}")
                return redirect('policiais:lista_policiais')

        sheet = workbook.sheet_by_index(0)
        
        cont_sucesso = 0
        cont_atualizado = 0
        cont_erro = 0
        
        # Mapeamento de Postos (Excel -> Modelo)
        mapa_postos = {
            'TEN CEL PM': 'TENCEL_PM',
            'MAJ PM': 'MAJ_PM',
            'CAP PM': 'CAP_PM',
            '1º TEN PM': '1TEN_PM',
            '2º TEN PM': '2TEN_PM',
            'SUBTEN PM': 'SUBTEN_PM',
            'SUB TEN PM': 'SUBTEN_PM',
            'ST PM': 'STEN_PM',
            '1º SGT PM': '1SGT_PM',
            '2º SGT PM': '2SGT_PM',
            '3º SGT PM': '3SGT_PM',
            'CB PM': 'CB_PM',
            'SD PM': 'SD_PM',
            'CEL PM': 'CEL_PM',
        }

        try:
            with transaction.atomic():
                # Começar da linha 1 (pula cabeçalho na linha 0)
                for i in range(1, sheet.nrows):
                    row = sheet.row_values(i)
                    if len(row) < 4: continue
                    
                    posto_raw = str(row[1]).strip().upper()
                    re_raw = str(row[2]).strip()
                    nome_raw = str(row[3]).strip().upper()
                    
                    if not re_raw or not nome_raw: continue
                    
                    # Limpar RE (remover traços e transformar em string limpa)
                    re_limpo = re_raw.replace('-', '').replace('.', '')
                    
                    posto_codigo = mapa_postos.get(posto_raw, 'SD_PM') # Default Sd se não achar
                    
                    # Update or Create
                    obj, created = Policial.objects.update_or_create(
                        re=re_limpo,
                        defaults={
                            'nome': nome_raw,
                            'posto': posto_codigo,
                            'situacao': 'ATIVO'
                        }
                    )
                    
                    if created: cont_sucesso += 1
                    else: cont_atualizado += 1
            
            messages.success(request, f"Importação concluída: {cont_sucesso} novos, {cont_atualizado} atualizados.")
        except Exception as e:
            messages.error(request, f"Erro durante o processamento dos dados: {e}")
            
    return redirect('policiais:lista_policiais')

@login_required
@require_module_permission('reserva_armas')
def excluir_policial(request, policial_id):
    policial = get_object_or_404(Policial, pk=policial_id)
    
    if request.method == 'POST':
        nome = policial.nome
        try:
            policial.delete()
            messages.success(request, _(f'Policial {nome} excluído com sucesso!'))
        except ProtectedError:
            messages.error(request, _(f'Não é possível excluir o policial {nome} pois ele possui movimentações registradas. Você pode apenas alterá-lo para INATIVO.'))
            return redirect('policiais:detalhe_policial', policial_id=policial.id)
            
    return redirect('policiais:lista_policiais')
@login_required
def buscar_policiais_ajax(request):
    """View para busca Ajax de policiais (Efetivo)"""
    q_raw = request.GET.get('q', '').strip()
    if not q_raw:
        return JsonResponse({'results': []})
    
    q_clean = ''.join(filter(str.isalnum, q_raw))
    
    policiais = Policial.objects.filter(
        Q(nome__icontains=q_raw) | 
        Q(re__icontains=q_raw) | 
        Q(re__icontains=q_clean),
        situacao='ATIVO'
    ).order_by('nome')[:15]
    
    results = [{
        'id': p.pk,
        'text': f"{p.re} - {p.get_posto_display()} {p.nome}",
    } for p in policiais]
    
    return JsonResponse({'results': results})
