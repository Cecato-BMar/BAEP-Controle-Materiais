from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import (CategoriaEquipamento, Equipamento, ConfiguracaoRadio, 
                     LinhaMovel, ServicoTI, SolicitacaoSuporteTI)
from .forms import (CategoriaEquipamentoForm, EquipamentoForm, ConfiguracaoRadioForm, 
                    LinhaMovelForm, ServicoTIForm, ChamadoInternoTIForm,
                    SolicitacaoSuporteTIForm, AtendimentoSuporteTIForm)
from reserva_baep.decorators import require_module_permission

@login_required
@require_module_permission('telematica')
def dashboard_telematica(request):
    total_equipamentos = Equipamento.objects.count()
    operacionais = Equipamento.objects.filter(status='OPERACIONAL').count()
    em_manutencao = Equipamento.objects.filter(status='MANUTENCAO').count()
    
    por_categoria = Equipamento.objects.values('categoria__nome', 'categoria__icone').annotate(total=Count('id')).order_by('-total')
    
    # Busca unificada de suportes/manutenções recentes (últimos criados)
    ultimas_intervencoes = SolicitacaoSuporteTI.objects.select_related('equipamento', 'solicitante').order_by('-data_solicitacao')[:5]
    servicos_ativos = ServicoTI.objects.filter(status=True).count()
    
    # Alertas e Suportes
    hoje = timezone.now().date()
    garantias_vencendo = Equipamento.objects.filter(vencimento_garantia__lte=hoje + timezone.timedelta(days=30), status='OPERACIONAL').count()
    
    suportes_pendentes = SolicitacaoSuporteTI.objects.filter(status='PENDENTE').select_related('solicitante').order_by('-data_solicitacao')
    total_pendentes = suportes_pendentes.count()
    
    context = {
        'total_equipamentos': total_equipamentos,
        'operacionais': operacionais,
        'em_manutencao': em_manutencao,
        'por_categoria': por_categoria,
        'ultimas_manutencoes': ultimas_intervencoes,
        'servicos_ativos': servicos_ativos,
        'garantias_vencendo': garantias_vencendo,
        'suportes_pendentes': suportes_pendentes[:5],
        'total_pendentes': total_pendentes,
    }
    return render(request, 'telematica/dashboard.html', context)

# EQUIPAMENTOS
@login_required
@require_module_permission('telematica')
def lista_equipamentos(request):
    hostname = request.GET.get('hostname', '')
    serie_pat = request.GET.get('serie_pat', '')
    marca = request.GET.get('marca', '')
    policial = request.GET.get('policial', '')
    cat = request.GET.get('categoria', '')
    qs = Equipamento.objects.select_related('categoria', 'policial_responsavel').all()
    
    if hostname:
        qs = qs.filter(hostname__icontains=hostname)
    if serie_pat:
        qs = qs.filter(Q(numero_serie__icontains=serie_pat) | Q(patrimonio__icontains=serie_pat))
    if marca:
        qs = qs.filter(Q(marca__icontains=marca) | Q(modelo__icontains=marca))
    if policial:
        qs = qs.filter(policial_responsavel_id=policial)
    if cat:
        qs = qs.filter(categoria_id=cat)
        
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    categorias = CategoriaEquipamento.objects.all()
    
    policial_obj = None
    if policial:
        from policiais.models import Policial
        try:
            policial_obj = Policial.objects.get(pk=policial)
        except Policial.DoesNotExist:
            pass
    
    return render(request, 'telematica/lista_equipamentos.html', {
        'page_obj': page,
        'hostname': hostname,
        'serie_pat': serie_pat,
        'marca': marca,
        'policial_obj': policial_obj,
        'categorias': categorias,
        'categoria_filtro': cat
    })

@login_required
@require_module_permission('telematica')
def detalhe_equipamento(request, pk):
    equipamento = get_object_or_404(Equipamento.objects.select_related('categoria'), pk=pk)
    manutencoes = equipamento.suportes.all().order_by('-data_solicitacao')
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

# SUPORTE TÉCNICO / CHAMADOS (GESTÃO)
@login_required
@require_module_permission('telematica')
def lista_manutencoes(request):
    """Lista unificada de todos os suportes e manutenções"""
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    
    qs = SolicitacaoSuporteTI.objects.select_related('equipamento', 'solicitante', 'tecnico_atribuido').all()
    
    if q:
        qs = qs.filter(
            Q(id__icontains=q) | 
            Q(solicitante__username__icontains=q) | 
            Q(descricao_problema__icontains=q) |
            Q(equipamento__hostname__icontains=q)
        )
    
    if status and status != 'TODOS':
        qs = qs.filter(status=status)
        
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'telematica/lista_manutencoes.html', {'page_obj': page, 'q': q, 'status_atual': status})

@login_required
@require_module_permission('telematica')
def criar_manutencao(request):
    """Abertura de chamado diretamente pela Telemática"""
    if request.method == 'POST':
        form = ChamadoInternoTIForm(request.POST)
        if form.is_valid():
            chamado = form.save(commit=False)
            chamado.origem = 'INTERNO'
            chamado.aberto_por = request.user
            # Se já abriu com status Em Atendimento e não tem data de início, seta agora
            if chamado.status == 'EM_ATENDIMENTO' and not chamado.data_inicio_atendimento:
                chamado.data_inicio_atendimento = timezone.now()
            chamado.save()
            messages.success(request, 'Chamado interno registrado com sucesso!')
            return redirect('telematica:lista_manutencoes')
    else:
        initial = {}
        equip_id = request.GET.get('equipamento')
        if equip_id:
            initial['equipamento'] = get_object_or_404(Equipamento, pk=equip_id)
        form = ChamadoInternoTIForm(initial=initial)
    return render(request, 'telematica/form_manutencao.html', {'form': form, 'titulo': 'Abrir Chamado Interno'})

@login_required
@require_module_permission('telematica')
def editar_manutencao(request, pk):
    """Edição de chamados existentes (administrativo)"""
    chamado = get_object_or_404(SolicitacaoSuporteTI, pk=pk)
    if request.method == 'POST':
        form = ChamadoInternoTIForm(request.POST, instance=chamado)
        if form.is_valid():
            form.save()
            messages.success(request, 'Chamado atualizado!')
            return redirect('telematica:lista_manutencoes')
    else:
        form = ChamadoInternoTIForm(instance=chamado)
    return render(request, 'telematica/form_manutencao.html', {'form': form, 'titulo': 'Editar Chamado'})

@login_required
@require_module_permission('telematica')
def excluir_manutencao(request, pk):
    chamado = get_object_or_404(SolicitacaoSuporteTI, pk=pk)
    if request.method == 'POST':
        chamado.delete()
        messages.success(request, 'Registro excluído.')
        return redirect('telematica:lista_manutencoes')
    return render(request, 'telematica/confirmar_exclusao.html', {'objeto': chamado, 'url_voltar': 'telematica:lista_manutencoes'})

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
        Q(marca__icontains=q) |
        Q(modelo__icontains=q) |
        Q(setor__nome__icontains=q) |
        Q(codigo_unidade__icontains=q) |
        Q(usuario_responsavel__icontains=q) |
        Q(policial_responsavel__nome__icontains=q) |
        Q(policial_responsavel__re__icontains=q)
    ).select_related('categoria', 'setor', 'policial_responsavel')[:25]
    
    data = []
    for e in qs:
        # Constrói uma string de localização informativa
        local = f" [{e.setor.nome}]" if e.setor else ""
        if e.codigo_unidade:
            local = f" [{e.codigo_unidade} - {e.setor.nome if e.setor else ''}]"
            
        # Constrói a identificação do responsável
        resp = ""
        if e.policial_responsavel:
            resp = f" | Resp: {e.policial_responsavel.posto} {e.policial_responsavel.nome}"
        elif e.usuario_responsavel:
            resp = f" | Resp: {e.usuario_responsavel}"
            
        text = f"{e.hostname or 'S/H'} — {e.numero_serie} ({e.categoria.nome}){local}{resp}"
        data.append({'id': e.pk, 'text': text})
    return JsonResponse({'results': data})

# SOLICITAÇÕES DE SUPORTE (USUÁRIO)
@login_required
def solicitar_suporte(request):
    if request.method == 'POST':
        form = SolicitacaoSuporteTIForm(request.POST)
        if form.is_valid():
            suporte = form.save(commit=False)
            suporte.solicitante = request.user
            suporte.aberto_por = request.user
            suporte.save()
            messages.success(request, 'Sua solicitação de suporte foi enviada com sucesso!')
            return redirect('telematica:minhas_solicitacoes_suporte')
    else:
        form = SolicitacaoSuporteTIForm()
    return render(request, 'telematica/form_suporte.html', {'form': form, 'titulo': 'Solicitar Suporte de TI'})

@login_required
def minhas_solicitacoes_suporte(request):
    qs = SolicitacaoSuporteTI.objects.filter(solicitante=request.user).order_by('-data_solicitacao')
    return render(request, 'telematica/minhas_solicitacoes_suporte.html', {'solicitacoes': qs})

@login_required
@require_module_permission('telematica')
def atender_suporte(request, pk):
    suporte = get_object_or_404(SolicitacaoSuporteTI, pk=pk)
    if request.method == 'POST':
        form = AtendimentoSuporteTIForm(request.POST, instance=suporte)
        if form.is_valid():
            atendimento = form.save(commit=False)
            # Se for a primeira vez que atende, marca o início
            if not atendimento.data_inicio_atendimento:
                atendimento.data_inicio_atendimento = timezone.now()
            
            if atendimento.status == 'CONCLUIDA' and not atendimento.data_conclusao:
                atendimento.data_conclusao = timezone.now()
            atendimento.save()
            messages.success(request, 'Atendimento de suporte atualizado!')
            return redirect('telematica:lista_manutencoes')
    else:
        form = AtendimentoSuporteTIForm(instance=suporte)
    return render(request, 'telematica/form_atendimento.html', {'form': form, 'suporte': suporte})
