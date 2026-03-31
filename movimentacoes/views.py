from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from reserva_baep.decorators import require_module_permission
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
import json
from .models import Movimentacao, Retirada, Devolucao
from .forms import RetiradaForm, DevolucaoForm, MovimentacaoSearchForm
from materiais.models import Material
from policiais.models import Policial

@login_required
@require_module_permission('reserva_armas')
def lista_movimentacoes(request):
    form = MovimentacaoSearchForm(request.GET)
    movimentacoes = Movimentacao.objects.all().order_by('-data_hora')
    
    # Filtragem
    if form.is_valid():
        tipo = form.cleaned_data.get('tipo')
        policial = form.cleaned_data.get('policial')
        material = form.cleaned_data.get('material')
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')
        
        if tipo:
            movimentacoes = movimentacoes.filter(tipo=tipo)
        
        if policial:
            movimentacoes = movimentacoes.filter(policial=policial)
            
        if material:
            movimentacoes = movimentacoes.filter(material=material)
            
        if data_inicio:
            movimentacoes = movimentacoes.filter(data_hora__date__gte=data_inicio)
            
        if data_fim:
            movimentacoes = movimentacoes.filter(data_hora__date__lte=data_fim)
    
    # Paginação
    paginator = Paginator(movimentacoes, 20)  # 20 itens por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'total_movimentacoes': movimentacoes.count(),
    }
    
    return render(request, 'movimentacoes/lista_movimentacoes.html', context)

@login_required
@require_module_permission('reserva_armas')
def detalhe_movimentacao(request, pk):
    movimentacao = get_object_or_404(Movimentacao, pk=pk)
    
    context = {
        'movimentacao': movimentacao,
    }
    
    # Adiciona informações específicas dependendo do tipo de movimentação
    if movimentacao.tipo == 'RETIRADA':
        try:
            retirada = movimentacao.retirada
            context['retirada'] = retirada
        except Retirada.DoesNotExist:
            pass
    elif movimentacao.tipo == 'DEVOLUCAO':
        try:
            devolucao = movimentacao.devolucao
            context['devolucao'] = devolucao
        except Devolucao.DoesNotExist:
            pass
    
    return render(request, 'movimentacoes/detalhe_movimentacao.html', context)

@login_required
@require_module_permission('reserva_armas')
def nova_retirada(request):
    if request.method == 'POST':
        form = RetiradaForm(request.POST)
        if form.is_valid():
            policial = form.cleaned_data['policial']
            finalidade = form.cleaned_data['finalidade']
            local_uso = form.cleaned_data['local_uso']
            data_prevista_devolucao = form.cleaned_data['data_prevista_devolucao']
            observacoes = form.cleaned_data['observacoes']
            materiais_selecionados = form.cleaned_data['materiais_selecionados']
            
            # Verifica se o policial está ativo
            if policial.situacao != 'ATIVO':
                messages.error(request, _(f'O policial {policial.nome} não está ativo. Não é possível registrar retirada.'))
                # Garante que apenas materiais disponíveis e com quantidade disponível sejam listados
                materiais_disponiveis = Material.objects.filter(status='DISPONIVEL', quantidade_disponivel__gt=0)
                return render(request, 'movimentacoes/form_retirada.html', {
                    'form': form,
                    'materiais': materiais_disponiveis,
                })
            
            # Converte a string JSON em lista de dicionários
            try:
                materiais_lista = json.loads(materiais_selecionados)
                
                if not materiais_lista:
                    messages.error(request, _('Nenhum material selecionado para retirada.'))
                    # Garante que apenas materiais disponíveis e com quantidade disponível sejam listados
                    materiais_disponiveis = Material.objects.filter(status='DISPONIVEL', quantidade_disponivel__gt=0)
                    return render(request, 'movimentacoes/form_retirada.html', {
                        'form': form,
                        'materiais': materiais_disponiveis,
                    })
                
                # Processa cada material selecionado
                for item in materiais_lista:
                    material_id = item.get('id')
                    quantidade = item.get('quantidade', 1)
                    
                    material = get_object_or_404(Material, pk=material_id)
                    
                    # Verifica se o material está disponível
                    if material.status != 'DISPONIVEL':
                        messages.error(request, _(f'O material {material.nome} ({material.numero}) não está disponível.'))
                        # Garante que apenas materiais disponíveis e com quantidade disponível sejam listados
                        materiais_disponiveis = Material.objects.filter(status='DISPONIVEL', quantidade_disponivel__gt=0)
                        return render(request, 'movimentacoes/form_retirada.html', {
                            'form': form,
                            'materiais': materiais_disponiveis,
                        })
                    
                    # Verifica se há quantidade disponível
                    if material.quantidade_disponivel < quantidade:
                        messages.error(request, _(f'Quantidade insuficiente para o material {material.nome} ({material.numero}).'))
                        # Garante que apenas materiais disponíveis e com quantidade disponível sejam listados
                        materiais_disponiveis = Material.objects.filter(status='DISPONIVEL', quantidade_disponivel__gt=0)
                        return render(request, 'movimentacoes/form_retirada.html', {
                            'form': form,
                            'materiais': materiais_disponiveis,
                        })
                    
                    # Cria a movimentação
                    movimentacao = Movimentacao.objects.create(
                        material=material,
                        policial=policial,
                        quantidade=quantidade,
                        tipo='RETIRADA',
                        observacoes=observacoes,
                        registrado_por=request.user
                    )
                    
                    # Cria o registro de retirada
                    Retirada.objects.create(
                        movimentacao=movimentacao,
                        finalidade=finalidade,
                        local_uso=local_uso,
                        data_prevista_devolucao=data_prevista_devolucao
                    )
                    
                    # Atualiza a quantidade disponível do material
                    material.quantidade_disponivel -= quantidade
                    material.quantidade_em_uso += quantidade
                    
                    # Atualiza o status do material se necessário
                    # Sempre atualiza para EM_USO quando há retirada, independente da quantidade disponível
                    if material.status == 'DISPONIVEL':
                        material.status = 'EM_USO'
                    
                    material.save()
                
                messages.success(request, _('Retirada registrada com sucesso!'))
                return redirect('movimentacoes:lista_movimentacoes')
                
            except json.JSONDecodeError:
                messages.error(request, _('Erro ao processar os materiais selecionados.'))
                # Garante que apenas materiais disponíveis e com quantidade disponível sejam listados
                materiais_disponiveis = Material.objects.filter(status='DISPONIVEL', quantidade_disponivel__gt=0)
                return render(request, 'movimentacoes/form_retirada.html', {
                    'form': form,
                    'materiais': materiais_disponiveis,
                })
    else:
        form = RetiradaForm()
    
    # Garante que apenas materiais disponíveis e com quantidade disponível sejam listados
    # Usando filter() para garantir que apenas materiais com status DISPONIVEL e quantidade_disponivel > 0 sejam listados
    materiais_disponiveis = Material.objects.filter(status='DISPONIVEL', quantidade_disponivel__gt=0).order_by('tipo', 'nome')
    
    return render(request, 'movimentacoes/form_retirada.html', {
        'form': form,
        'materiais': materiais_disponiveis,
    })

@login_required
@require_module_permission('reserva_armas')
def nova_devolucao(request):
    if request.method == 'POST':
        form = DevolucaoForm(request.POST)
        if form.is_valid():
            try:
                policial = form.cleaned_data.get('policial')
                observacoes = form.cleaned_data.get('observacoes', '')
                devolucoes_selecionadas = form.cleaned_data.get('devolucoes_selecionadas', '')
            except KeyError as e:
                messages.error(request, _(f'Campo obrigatório não encontrado: {e}'))
                return render(request, 'movimentacoes/form_devolucao.html', {'form': form})
            
            # Verifica se há materiais selecionados
            if not devolucoes_selecionadas:
                messages.error(request, _('Nenhum material selecionado para devolução.'))
                return render(request, 'movimentacoes/form_devolucao.html', {'form': form})
            
            # Converte a string JSON em lista de dicionários
            try:
                devolucoes_lista = json.loads(devolucoes_selecionadas)
                
                if not devolucoes_lista:
                    messages.error(request, _('Nenhum material selecionado para devolução.'))
                    return render(request, 'movimentacoes/form_devolucao.html', {'form': form})
                
                # Processa cada material selecionado para devolução
                for item in devolucoes_lista:
                    retirada_id = item.get('retirada_id')
                    material_id = item.get('material_id')
                    quantidade = item.get('quantidade', 1)
                    estado_devolucao = item.get('estado', 'BOM')
                    
                    # Validações básicas
                    if not retirada_id or not material_id:
                        messages.error(request, _('Dados inválidos para devolução.'))
                        return render(request, 'movimentacoes/form_devolucao.html', {'form': form})
                    
                    try:
                        material = get_object_or_404(Material, pk=material_id)
                        retirada = get_object_or_404(Retirada, pk=retirada_id)
                    except (Material.DoesNotExist, Retirada.DoesNotExist):
                        messages.error(request, _('Material ou retirada não encontrado.'))
                        return render(request, 'movimentacoes/form_devolucao.html', {'form': form})
                    
                    # Usa o policial da retirada se não houver policial selecionado
                    policial_devolucao = policial if policial else retirada.movimentacao.policial
                    
                    # Cria a movimentação
                    movimentacao = Movimentacao.objects.create(
                        material=material,
                        policial=policial_devolucao,
                        quantidade=quantidade,
                        tipo='DEVOLUCAO',
                        observacoes=observacoes,
                        registrado_por=request.user
                    )
                    
                    # Cria o registro de devolução
                    Devolucao.objects.create(
                        movimentacao=movimentacao,
                        retirada_referencia=retirada,
                        estado_devolucao=estado_devolucao
                    )
                    
                    # Atualiza a quantidade disponível do material
                    material.quantidade_disponivel += quantidade
                    material.quantidade_em_uso -= quantidade
                    
                    # Atualiza o estado do material se necessário
                    if estado_devolucao in ['RUIM', 'PESSIMO']:
                        material.estado = estado_devolucao
                    
                    # Verifica se o material deve ir para manutenção
                    manutencao = item.get('manutencao', False)
                    if manutencao or estado_devolucao in ['RUIM', 'PESSIMO']:
                        # Se o material estiver marcado para manutenção ou em estado ruim/péssimo
                        if material.status != 'MANUTENCAO':
                            material.status = 'MANUTENCAO'
                    # Atualiza o status do material se toda a quantidade em uso foi devolvida
                    elif material.quantidade_em_uso == 0:
                        # Se não há quantidade em uso, o material deve estar disponível
                        # (exceto se estiver marcado para manutenção ou em estado ruim/péssimo)
                        if material.status in ['EM_USO', 'MANUTENCAO'] and not (manutencao or estado_devolucao in ['RUIM', 'PESSIMO']):
                            material.status = 'DISPONIVEL'
                    
                    material.save()
                
                messages.success(request, _('Devolução registrada com sucesso!'))
                return redirect('movimentacoes:lista_movimentacoes')
                
            except json.JSONDecodeError:
                messages.error(request, _('Erro ao processar os materiais selecionados.'))
                return render(request, 'movimentacoes/form_devolucao.html', {'form': form})
    else:
        form = DevolucaoForm()
    
    return render(request, 'movimentacoes/form_devolucao.html', {
        'form': form,
    })

@login_required
@require_module_permission('reserva_armas')
def buscar_retiradas_pendentes(request):
    policial_id = request.GET.get('policial_id')
    
    if not policial_id:
        return JsonResponse({'error': 'Policial não informado'}, status=400)
    
    # Busca todas as retiradas do policial que ainda não foram totalmente devolvidas
    retiradas_pendentes = []
    
    # Busca as movimentações de retirada do policial
    movimentacoes_retirada = Movimentacao.objects.filter(
        policial_id=policial_id,
        tipo='RETIRADA'
    ).select_related('material', 'retirada')
    
    for mov in movimentacoes_retirada:
        # Calcula a quantidade já devolvida deste material para esta retirada
        devolucoes = Devolucao.objects.filter(retirada_referencia=mov.retirada)
        quantidade_devolvida = sum(d.movimentacao.quantidade for d in devolucoes)
        
        # Se ainda há quantidade pendente de devolução
        if quantidade_devolvida < mov.quantidade:
            quantidade_pendente = mov.quantidade - quantidade_devolvida
            
            retiradas_pendentes.append({
                'retirada_id': mov.retirada.id,
                'material_id': mov.material.id,
                'material_nome': mov.material.nome,
                'material_numero': mov.material.numero,
                'material_tipo': mov.material.get_tipo_display(),
                'quantidade_retirada': mov.quantidade,
                'quantidade_devolvida': quantidade_devolvida,
                'quantidade_pendente': quantidade_pendente,
                'data_retirada': mov.data_hora.strftime('%d/%m/%Y %H:%M'),
                'finalidade': mov.retirada.finalidade
            })
    
    return JsonResponse({'retiradas': retiradas_pendentes})

@login_required
@require_module_permission('reserva_armas')
def buscar_materiais_disponiveis(request):
    termo = request.GET.get('termo', '')
    tipo = request.GET.get('tipo', '')
    
    materiais = Material.objects.filter(status='DISPONIVEL', quantidade_disponivel__gt=0)
    
    if termo:
        materiais = materiais.filter(Q(nome__icontains=termo) | Q(numero__icontains=termo))
    
    if tipo:
        materiais = materiais.filter(tipo=tipo)
    
    materiais_lista = [{
        'id': m.id,
        'nome': m.nome,
        'numero': m.numero,
        'tipo': m.get_tipo_display(),
        'quantidade_disponivel': m.quantidade_disponivel,
        'estado': m.get_estado_display()
    } for m in materiais]
    
    return JsonResponse({'materiais': materiais_lista})
