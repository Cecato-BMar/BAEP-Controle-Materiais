from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Sum, Count, F, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
import json
import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal

# ReportLab para PDFs
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

from reserva_baep.decorators import require_module_permission
from policiais.models import Policial

from .models import (
    Categoria, Subcategoria, UnidadeMedida, UnidadeFornecimento, Cor, ContaPatrimonial,
    OrgaoRequisitante, LocalizacaoFisica, MilitarRequisitante,
    Fornecedor, Produto, Lote, NumeroSerie,
    MovimentacaoEstoque, Inventario, ItemInventario, AjusteEstoque
)
from .forms import (
    CategoriaForm, SubcategoriaForm, UnidadeMedidaForm, UnidadeFornecimentoForm, CorForm,
    ContaPatrimonialForm, OrgaoRequisitanteForm, LocalizacaoFisicaForm,
    MilitarRequisitanteForm, FornecedorForm, ProdutoForm, LoteForm,
    NumeroSerieForm, EntradaMaterialForm, SaidaMaterialForm,
    MovimentacaoEstoqueForm, InventarioForm, ItemInventarioForm,
    AjusteEstoqueForm, PainelEstoqueFilterForm
)


def is_admin(user):
    return user.is_superuser or user.groups.filter(name='administracao').exists()


def is_materiais(user):
    return is_admin(user) or user.groups.filter(name='materiais').exists()


# =============================================================================
# DASHBOARD
# =============================================================================

@login_required
@require_module_permission('materiais')
def dashboard_estoque(request):
    """Dashboard principal do estoque com indicadores PAP"""
    total_produtos = Produto.objects.filter(status='ATIVO').count()

    # Alertas PAP
    alertas_estoque_minimo = []
    alertas_cotacao = []
    for p in Produto.objects.filter(status='ATIVO').select_related('categoria', 'unidade_medida'):
        if p.precisa_reposicao:
            alertas_estoque_minimo.append(p)
        if p.cotacao_vencida:
            alertas_cotacao.append(p)

    # Movimentações recentes
    movimentacoes_recentes = MovimentacaoEstoque.objects.select_related(
        'produto', 'usuario'
    ).order_by('-data_hora')[:10]

    # Lotes próximos ao vencimento
    data_limite = timezone.now().date() + timedelta(days=30)
    lotes_vencendo = Lote.objects.filter(
        data_validade__lte=data_limite,
        data_validade__gte=timezone.now().date(),
        ativo=True
    ).count()

    # Valor total do estoque
    valor_total_estoque = sum(
        p.saldo_calculado * Decimal(str(p.valor_unitario or 0))
        for p in Produto.objects.filter(status='ATIVO')
    )

    context = {
        'total_produtos': total_produtos,
        'alertas_estoque_minimo': alertas_estoque_minimo[:5],
        'total_alertas_estoque': len(alertas_estoque_minimo),
        'alertas_cotacao': alertas_cotacao[:5],
        'total_alertas_cotacao': len(alertas_cotacao),
        'movimentacoes_recentes': movimentacoes_recentes,
        'lotes_vencendo': lotes_vencendo,
        'valor_total_estoque': valor_total_estoque,
    }
    return render(request, 'estoque/dashboard.html', context)


# =============================================================================
# PAINEL DE CONTROLE DE ESTOQUE (PAP §4 — Somente Leitura)
# =============================================================================

@login_required
@require_module_permission('materiais')
def painel_controle_estoque(request):
    """Painel de controle somente leitura com indicadores PAP §4"""
    form = PainelEstoqueFilterForm(request.GET or None)
    material = None
    indicadores = None

    if form.is_valid():
        material = form.cleaned_data.get('material')
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')

        if material:
            saldo = material.saldo_calculado
            consumo_medio = material.consumo_medio(data_inicio, data_fim)
            autonomia = material.autonomia(data_inicio, data_fim)

            # Última entrada para calcular tempo de reposição
            ultima_entrada = MovimentacaoEstoque.objects.filter(
                produto=material,
                subtipo='COMPRA_NOVA'
            ).order_by('-data_movimentacao').first()

            indicadores = {
                'material': material,
                'saldo': saldo,
                'consumo_medio': consumo_medio,
                'autonomia': autonomia,
                'estoque_minimo': material.estoque_minimo,
                'precisa_reposicao': material.precisa_reposicao,
                'estoque_critico': material.estoque_critico,
                'data_cotacao': material.data_cotacao,
                'cotacao_vencida': material.cotacao_vencida,
                'tempo_reposicao': material.tempo_reposicao_calculado,
                'ultima_entrada': ultima_entrada,
                'data_inicio': data_inicio,
                'data_fim': data_fim,
            }

    # Contadores estratégicos para o Dashboard KPI
    count_reposicao = 0
    count_cotacao_vencida = 0
    total_valor_estoque = Decimal('0.00')

    # Todos os materiais ativos para o relatório consolidado
    todos_materiais = Produto.objects.filter(status='ATIVO').select_related('categoria', 'unidade_medida')
    for m in todos_materiais:
        m.saldo_atual = m.saldo_calculado
        m.alerta_reposicao = m.precisa_reposicao
        m.alerta_cotacao = m.cotacao_vencida
        
        if m.alerta_reposicao:
            count_reposicao += 1
        if m.alerta_cotacao:
            count_cotacao_vencida += 1
        
        # Valor estimado (Saldo * Preço Médio ou Valor Unitário)
        preco = m.preco_medio or m.valor_unitario or Decimal('0.00')
        total_valor_estoque += (m.saldo_atual * preco)

    context = {
        'form': form,
        'material': material,
        'indicadores': indicadores,
        'todos_materiais': todos_materiais,
        'count_reposicao': count_reposicao,
        'count_cotacao_vencida': count_cotacao_vencida,
        'total_valor_estoque': total_valor_estoque,
        'responsavel': request.user,
    }
    return render(request, 'estoque/painel_controle.html', context)


# =============================================================================
# ENTRADA DE MATERIAIS (PAP §2)
# =============================================================================

@login_required
@require_module_permission('materiais')
def criar_entrada_material(request):
    """Registrar entrada de material conforme PAP §2"""
    if request.method == 'POST':
        form = EntradaMaterialForm(request.POST)
        form.instance.tipo_movimentacao = 'ENTRADA'
        if form.is_valid():
            mov = form.save(commit=False)
            mov.usuario = request.user
            mov._request = request
            # tipo derivado do subtipo pelo model.save()
            mov.save()
            messages.success(
                request,
                _(f'Entrada registrada com sucesso! Saldo atualizado para {mov.produto.saldo_calculado}.')
            )
            return redirect('estoque:lista_movimentacoes')
        else:
            messages.error(request, _('Corrija os erros abaixo.'))
    else:
        form = EntradaMaterialForm()

    return render(request, 'estoque/entrada_material.html', {
        'form': form,
        'titulo': 'Registrar Entrada de Material',
    })


# =============================================================================
# SAÍDA DE MATERIAIS (PAP §3)
# =============================================================================

@login_required
@require_module_permission('materiais')
def criar_saida_material(request):
    """Registrar saída de material conforme PAP §3"""
    if request.method == 'POST':
        form = SaidaMaterialForm(request.POST)
        form.instance.tipo_movimentacao = 'SAIDA'
        if form.is_valid():
            mov = form.save(commit=False)
            mov.usuario = request.user
            mov._request = request
            # Define valor unitário como preço médio do produto
            if mov.produto and not mov.valor_unitario:
                mov.valor_unitario = mov.produto.preco_medio or mov.produto.valor_unitario
            mov.save()
            messages.success(
                request,
                _(f'Saída registrada com sucesso! Saldo restante: {mov.produto.saldo_calculado}.')
            )
            return redirect(reverse('estoque:confirmacao_saida_material') + f'?id={mov.id}')
        else:
            messages.error(request, _('Corrija os erros abaixo.'))
    else:
        form = SaidaMaterialForm()

    return render(request, 'estoque/saida_material.html', {
        'form': form,
        'titulo': 'Registrar Saída de Material',
    })


# =============================================================================
# CATEGORIAS
# =============================================================================

@login_required
@user_passes_test(is_admin)
@require_module_permission('materiais')
def lista_categorias(request):
    categorias = Categoria.objects.select_related('categoria_pai').all()
    termo = request.GET.get('q')
    if termo:
        categorias = categorias.filter(
            Q(nome__icontains=termo) |
            Q(codigo__icontains=termo) |
            Q(descricao__icontains=termo)
        )
    paginator = Paginator(categorias, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'estoque/lista_categorias.html', {
        'page_obj': page, 
        'termo': termo,
        'titulo': 'Categorias',
        'table_headers': ['Código', 'Nome']
    })


@login_required
@user_passes_test(is_admin)
@require_module_permission('materiais')
def criar_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Categoria criada com sucesso!'))
            if request.GET.get('popup'):
                return render(request, 'estoque/close_popup.html')
            return redirect('estoque:lista_categorias')
    else:
        form = CategoriaForm()
    return render(request, 'estoque/form_categoria.html', {'form': form})


@login_required
@user_passes_test(is_admin)
@require_module_permission('materiais')
def criar_subcategoria(request):
    if request.method == 'POST':
        form = SubcategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Subcategoria criada com sucesso!'))
            if request.GET.get('popup'):
                return render(request, 'estoque/close_popup.html')
            return render(request, 'estoque/close_popup.html') # Subcategoria sempre via popup no momento
    else:
        form = SubcategoriaForm()
    return render(request, 'estoque/form_subcategoria.html', {'form': form})


@login_required
@user_passes_test(is_admin)
@require_module_permission('materiais')
def editar_categoria(request, pk):
    obj = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, _('Categoria atualizada!'))
            return redirect('estoque:lista_categorias')
    else:
        form = CategoriaForm(instance=obj)
    return render(request, 'estoque/form_categoria.html', {'form': form, 'objeto': obj})


# =============================================================================
# UNIDADES DE MEDIDA
# =============================================================================

@login_required
@require_module_permission('materiais')
def lista_unidades_medida(request):
    qs = UnidadeMedida.objects.all()
    return render(request, 'estoque/lista_unidades.html', {
        'objetos': qs, 
        'titulo': 'Unidades de Medida',
        'table_headers': ['Sigla', 'Nome', 'Descrição', 'Status']
    })


@login_required
@user_passes_test(is_admin)
@require_module_permission('materiais')
def criar_unidade_medida(request):
    if request.method == 'POST':
        form = UnidadeMedidaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Unidade de medida criada!'))
            if request.GET.get('popup'):
                return render(request, 'estoque/close_popup.html')
            return redirect('estoque:lista_unidades_medida')
    else:
        form = UnidadeMedidaForm()
    return render(request, 'estoque/form_unidade_medida.html', {'form': form})


# =============================================================================
# UNIDADE DE FORNECIMENTO (PAP §1 — Somente Admin)
# =============================================================================

@login_required
@user_passes_test(is_admin)
@require_module_permission('materiais')
def lista_unidades_fornecimento(request):
    qs = UnidadeFornecimento.objects.all()
    return render(request, 'estoque/lista_unidades.html', {
        'objetos': qs, 
        'titulo': 'Unidades de Fornecimento', 
        'tipo': 'fornecimento',
        'table_headers': ['Nome', 'Descrição', 'Status']
    })


@login_required
@user_passes_test(is_admin)
@require_module_permission('materiais')
def criar_unidade_fornecimento(request):
    if request.method == 'POST':
        form = UnidadeFornecimentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Unidade de fornecimento criada!'))
            if request.GET.get('popup'):
                return render(request, 'estoque/close_popup.html')
            return redirect('estoque:lista_unidades_fornecimento')
    else:
        form = UnidadeFornecimentoForm()
    return render(request, 'estoque/form_unidade_fornecimento.html', {'form': form})


# =============================================================================
# COR (PAP §1)
# =============================================================================

@login_required
@require_module_permission('materiais')
def lista_cores(request):
    qs = Cor.objects.all()
    return render(request, 'estoque/lista_cores.html', {
        'objetos': qs,
        'titulo': 'Cores',
        'table_headers': ['Nome', 'Status']
    })


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def criar_cor(request):
    if request.method == 'POST':
        form = CorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Cor criada!'))
            if request.GET.get('popup'):
                return render(request, 'estoque/close_popup.html')
            return redirect('estoque:lista_cores')
    else:
        form = CorForm()
    return render(request, 'estoque/form_cor.html', {'form': form})


# =============================================================================
# CONTA PATRIMONIAL (PAP §1)
# =============================================================================

@login_required
@require_module_permission('materiais')
def lista_contas_patrimoniais(request):
    qs = ContaPatrimonial.objects.all()
    return render(request, 'estoque/lista_contas_patrimoniais.html', {
        'objetos': qs,
        'titulo': 'Contas Patrimoniais',
        'table_headers': ['Código', 'Descrição', 'Status']
    })


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def criar_conta_patrimonial(request):
    if request.method == 'POST':
        form = ContaPatrimonialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Conta patrimonial criada!'))
            if request.GET.get('popup'):
                return render(request, 'estoque/close_popup.html')
            return redirect('estoque:lista_contas_patrimoniais')
    else:
        form = ContaPatrimonialForm()
    return render(request, 'estoque/form_conta_patrimonial.html', {'form': form})


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def editar_conta_patrimonial(request, pk):
    obj = get_object_or_404(ContaPatrimonial, pk=pk)
    if request.method == 'POST':
        form = ContaPatrimonialForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, _('Conta patrimonial atualizada!'))
            return redirect('estoque:lista_contas_patrimoniais')
    else:
        form = ContaPatrimonialForm(instance=obj)
    return render(request, 'estoque/form_conta_patrimonial.html', {'form': form, 'objeto': obj})


# =============================================================================
# ÓRGÃO REQUISITANTE (PAP §1)
# =============================================================================

@login_required
@require_module_permission('materiais')
def lista_orgaos_requisitantes(request):
    qs = OrgaoRequisitante.objects.all()
    return render(request, 'estoque/lista_orgaos.html', {
        'objetos': qs, 
        'titulo': 'Órgãos Requisitantes',
        'table_headers': ['Sigla', 'Nome', 'Status']
    })


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def criar_orgao_requisitante(request):
    if request.method == 'POST':
        form = OrgaoRequisitanteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Órgão requisitante criado!'))
            if request.GET.get('popup'):
                return render(request, 'estoque/close_popup.html')
            return redirect('estoque:lista_orgaos_requisitantes')
    else:
        form = OrgaoRequisitanteForm()
    return render(request, 'estoque/form_orgao.html', {'form': form})


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def editar_orgao_requisitante(request, pk):
    obj = get_object_or_404(OrgaoRequisitante, pk=pk)
    if request.method == 'POST':
        form = OrgaoRequisitanteForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, _('Órgão atualizado!'))
            return redirect('estoque:lista_orgaos_requisitantes')
    else:
        form = OrgaoRequisitanteForm(instance=obj)
    return render(request, 'estoque/form_orgao.html', {'form': form, 'objeto': obj})


# =============================================================================
# LOCALIZAÇÃO FÍSICA (PAP §1)
# =============================================================================

@login_required
@require_module_permission('materiais')
def lista_localizacoes(request):
    qs = LocalizacaoFisica.objects.all()
    return render(request, 'estoque/lista_localizacoes.html', {
        'objetos': qs,
        'titulo': 'Localizações Físicas',
        'table_headers': ['Nome', 'Descrição', 'Status']
    })


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def criar_localizacao(request):
    if request.method == 'POST':
        form = LocalizacaoFisicaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Localização criada!'))
            if request.GET.get('popup'):
                return render(request, 'estoque/close_popup.html')
            return redirect('estoque:lista_localizacoes')
    else:
        form = LocalizacaoFisicaForm()
    return render(request, 'estoque/form_localizacao.html', {'form': form})


# =============================================================================
# MILITAR REQUISITANTE (PAP §1)
# =============================================================================

@login_required
@require_module_permission('materiais')
def lista_militares_requisitantes(request):
    qs = MilitarRequisitante.objects.select_related('orgao').all()
    termo = request.GET.get('q')
    if termo:
        qs = qs.filter(Q(re__icontains=termo) | Q(qra__icontains=termo) | Q(nome_completo__icontains=termo))
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'estoque/lista_militares.html', {'page_obj': page, 'termo': termo})


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def criar_militar_requisitante(request):
    if request.method == 'POST':
        form = MilitarRequisitanteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Militar requisitante cadastrado!'))
            if request.GET.get('popup'):
                return render(request, 'estoque/close_popup.html')
            return redirect('estoque:lista_militares_requisitantes')
    else:
        form = MilitarRequisitanteForm()
    return render(request, 'estoque/form_militar.html', {'form': form})


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def editar_militar_requisitante(request, pk):
    obj = get_object_or_404(MilitarRequisitante, pk=pk)
    if request.method == 'POST':
        form = MilitarRequisitanteForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, _('Militar atualizado!'))
            return redirect('estoque:lista_militares_requisitantes')
    else:
        form = MilitarRequisitanteForm(instance=obj)
    return render(request, 'estoque/form_militar.html', {'form': form, 'objeto': obj})


# =============================================================================
# FORNECEDORES
# =============================================================================

@login_required
@require_module_permission('materiais')
def lista_fornecedores(request):
    qs = Fornecedor.objects.all()
    termo = request.GET.get('q')
    if termo:
        qs = qs.filter(Q(nome__icontains=termo) | Q(documento__icontains=termo))
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'estoque/lista_fornecedores.html', {
        'page_obj': page, 
        'termo': termo,
        'titulo': 'Fornecedores',
        'table_headers': ['CPF/CNPJ', 'Nome/Razão Social', 'Tipo', 'Status']
    })


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def criar_fornecedor(request):
    if request.method == 'POST':
        form = FornecedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Fornecedor criado!'))
            if request.GET.get('popup'):
                return render(request, 'estoque/close_popup.html')
            return redirect('estoque:lista_fornecedores')
    else:
        form = FornecedorForm()
    return render(request, 'estoque/form_fornecedor.html', {'form': form})


@login_required
@require_module_permission('materiais')
def detalhe_fornecedor(request, pk):
    obj = get_object_or_404(Fornecedor, pk=pk)
    return render(request, 'estoque/detalhe_fornecedor.html', {'fornecedor': obj})


# =============================================================================
# PRODUTOS / MATERIAIS DE CONSUMO (PAP §1)
# =============================================================================

@login_required
@require_module_permission('materiais')
def lista_produtos(request):
    qs = Produto.objects.select_related('categoria', 'unidade_medida').all()
    termo = request.GET.get('q')
    categoria_id = request.GET.get('categoria')
    status = request.GET.get('status', 'ATIVO')

    if termo:
        qs = qs.filter(
            Q(codigo__icontains=termo) |
            Q(nome__icontains=termo) |
            Q(codigo_siafisico__icontains=termo) |
            Q(codigo_cat_mat__icontains=termo)
        )
    if categoria_id:
        qs = qs.filter(categoria_id=categoria_id)
    if status:
        qs = qs.filter(status=status)

    # Indicadores para o cabeçalho
    total_count = qs.count()
    active_count = qs.filter(status='ATIVO').count()
    low_stock_count = 0
    
    # Adiciona saldo calculado a cada produto
    for p in qs:
        p.saldo_atual = p.saldo_calculado
        p.alerta_reposicao = p.precisa_reposicao
        if p.alerta_reposicao and p.status == 'ATIVO':
            low_stock_count += 1

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    categorias = Categoria.objects.filter(ativo=True)
    
    return render(request, 'estoque/lista_produtos.html', {
        'page_obj': page,
        'termo': termo,
        'categorias': categorias,
        'status_filtro': status,
        'total_count': total_count,
        'active_count': active_count,
        'low_stock_count': low_stock_count,
    })


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def criar_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.criado_por = request.user
            produto._current_user = request.user
            produto.save()
            messages.success(request, _(f'Material "{produto.nome}" cadastrado com sucesso!'))
            return redirect('estoque:detalhe_produto', pk=produto.pk)
    else:
        form = ProdutoForm()
    return render(request, 'estoque/form_produto.html', {'form': form, 'titulo': 'Novo Material de Consumo'})


@login_required
@require_module_permission('materiais')
def detalhe_produto(request, pk):
    produto = get_object_or_404(
        Produto.objects.select_related('categoria', 'unidade_medida', 'fornecedor_padrao',
                                        'localizacao_fisica', 'conta_patrimonial'),
        pk=pk
    )
    movimentacoes = produto.movimentacoes_estoque.select_related(
        'usuario', 'orgao_requisitante', 'militar_requisitante'
    ).order_by('-data_hora')[:20]

    month_ago = (timezone.now() - timedelta(days=30)).date().isoformat()
    
    context = {
        'produto': produto,
        'saldo': produto.saldo_calculado,
        'movimentacoes': movimentacoes,
        'cotacao_vencida': produto.cotacao_vencida,
        'precisa_reposicao': produto.precisa_reposicao,
        'estoque_critico': produto.estoque_critico,
        'month_ago': month_ago,
    }
    return render(request, 'estoque/detalhe_produto.html', context)


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def editar_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        if form.is_valid():
            p = form.save(commit=False)
            p._current_user = request.user
            p.save()
            messages.success(request, _('Material atualizado!'))
            return redirect('estoque:detalhe_produto', pk=pk)
    else:
        form = ProdutoForm(instance=produto)
    return render(request, 'estoque/form_produto.html', {'form': form, 'objeto': produto, 'titulo': 'Editar Material'})


# =============================================================================
# MOVIMENTAÇÕES (listagem e form genérico legado)
# =============================================================================

@login_required
@require_module_permission('materiais')
def lista_movimentacoes(request):
    qs = MovimentacaoEstoque.objects.select_related(
        'produto', 'usuario', 'orgao_requisitante', 'militar_requisitante'
    ).order_by('-data_hora')

    subtipo = request.GET.get('subtipo')
    produto_id = request.GET.get('produto')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    termo = request.GET.get('q')

    if subtipo:
        qs = qs.filter(subtipo=subtipo)
    if produto_id:
        qs = qs.filter(produto_id=produto_id)
    if data_inicio:
        qs = qs.filter(data_movimentacao__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data_movimentacao__lte=data_fim)
    if termo:
        qs = qs.filter(Q(produto__nome__icontains=termo) | Q(observacoes__icontains=termo))

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'estoque/lista_movimentacoes.html', {
        'page_obj': page,
        'subtipo_filtro': subtipo,
        'subtipos': MovimentacaoEstoque.SUBTIPO_CHOICES,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'termo': termo,
    })


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def criar_movimentacao(request):
    """View genérica — redireciona para entrada ou saída específicas"""
    tipo = request.GET.get('tipo', 'entrada')
    if tipo == 'saida':
        return redirect('estoque:criar_saida_material')
    return redirect('estoque:criar_entrada_material')


# =============================================================================
# INVENTÁRIOS
# =============================================================================

@login_required
@require_module_permission('materiais')
def lista_inventarios(request):
    qs = Inventario.objects.select_related('responsavel').all()
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'estoque/lista_inventarios.html', {'page_obj': page})


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def criar_inventario(request):
    if request.method == 'POST':
        form = InventarioForm(request.POST)
        if form.is_valid():
            inv = form.save(commit=False)
            inv.save()
            messages.success(request, _('Inventário criado!'))
            return redirect('estoque:detalhe_inventario', pk=inv.pk)
    else:
        form = InventarioForm()
    return render(request, 'estoque/form_inventario.html', {'form': form})


@login_required
@require_module_permission('materiais')
def detalhe_inventario(request, pk):
    inv = get_object_or_404(Inventario.objects.select_related('responsavel'), pk=pk)
    itens = inv.itens_inventario.select_related('produto', 'contado_por').all()
    return render(request, 'estoque/detalhe_inventario.html', {'inventario': inv, 'itens': itens})


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def iniciar_inventario(request, pk):
    inv = get_object_or_404(Inventario, pk=pk)
    if inv.status == 'PLANEJADO':
        inv.status = 'EM_ANDAMENTO'
        inv.data_inicio = timezone.now()
        inv.save()
        # Cria itens para todos os produtos ativos
        for produto in Produto.objects.filter(status='ATIVO'):
            ItemInventario.objects.get_or_create(
                inventario=inv,
                produto=produto,
                lote=None,
                numero_serie=None,
                defaults={'quantidade_sistema': produto.saldo_calculado}
            )
        messages.success(request, _('Inventário iniciado!'))
    return redirect('estoque:detalhe_inventario', pk=pk)


@login_required
@user_passes_test(is_materiais)
@require_module_permission('materiais')
def contar_item_inventario(request, pk):
    item = get_object_or_404(ItemInventario, pk=pk)
    if request.method == 'POST':
        quantidade_contada = request.POST.get('quantidade_contada')
        justificativa = request.POST.get('justificativa_divergencia', '')
        try:
            item.quantidade_contada = Decimal(quantidade_contada)
            item.justificativa_divergencia = justificativa
            item.status_contagem = 'CONTADO'
            item.contado_por = request.user
            item.contado_em = timezone.now()
            item.save()
            messages.success(request, _('Contagem registrada!'))
        except Exception as e:
            messages.error(request, str(e))
    return redirect('estoque:detalhe_inventario', pk=item.inventario.pk)


# =============================================================================
# RELATÓRIOS (PAP §5)
# =============================================================================

@login_required
@require_module_permission('materiais')
def relatorio_estoque_materiais(request):
    """Relatório de Estoque de Materiais conforme PAP §5.1"""
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if data_inicio:
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except ValueError:
            data_inicio = None
    if data_fim:
        try:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except ValueError:
            data_fim = None

    materiais = Produto.objects.filter(status='ATIVO').select_related('categoria', 'unidade_medida')

    dados = []
    for m in materiais:
        saldo = m.saldo_calculado
        consumo = m.consumo_medio(data_inicio, data_fim)
        dados.append({
            'material': m,
            'saldo': saldo,
            'consumo_medio': consumo,
            'estoque_minimo': m.estoque_minimo,
            'alerta': saldo <= m.estoque_minimo,
            'cotacao_vencida': m.cotacao_vencida,
        })

    context = {
        'dados': dados,
        'data_emissao': timezone.now(),
        'responsavel': request.user,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    return render(request, 'estoque/relatorio_estoque.html', context)


@login_required
@require_module_permission('materiais')
def relatorio_estoque_baixo(request):
    produtos = [p for p in Produto.objects.filter(status='ATIVO').select_related('categoria') if p.precisa_reposicao]
    context = {
        'dados': [{'material': p, 'saldo': p.saldo_calculado, 'estoque_minimo': p.estoque_minimo, 'alerta': True} for p in produtos],
        'responsavel': request.user,
        'data_emissao': timezone.now(),
        'titulo_extra': 'MATERIAIS ABAIXO DO MÍNIMO',
    }
    return render(request, 'estoque/relatorio_estoque_baixo.html', context)


@login_required
@require_module_permission('materiais')
def relatorio_situacao_estoque(request):
    materiais = Produto.objects.filter(status='ATIVO').select_related('categoria', 'unidade_medida')
    dados = []
    for m in materiais:
        dados.append({
            'material': m,
            'saldo': m.saldo_calculado,
            'estoque_minimo': m.estoque_minimo,
            'alerta': m.precisa_reposicao,
        })
    context = {
        'dados': dados,
        'responsavel': request.user,
        'data_emissao': timezone.now(),
    }
    return render(request, 'estoque/relatorio_situacao.html', context)


@login_required
@require_module_permission('materiais')
def relatorio_movimentacoes_periodo(request):
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    qs = MovimentacaoEstoque.objects.select_related(
        'produto', 'usuario', 'orgao_requisitante', 'militar_requisitante'
    ).order_by('-data_movimentacao')
    if data_inicio:
        qs = qs.filter(data_movimentacao__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data_movimentacao__lte=data_fim)
    return render(request, 'estoque/relatorio_movimentacoes.html', {
        'movimentacoes': qs,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'responsavel': request.user,
        'data_emissao': timezone.now(),
    })


@login_required
@require_module_permission('materiais')
def relatorio_inventarios(request):
    inventarios = Inventario.objects.select_related('responsavel').all()
    return render(request, 'estoque/relatorio_inventarios.html', {
        'inventarios': inventarios,
        'responsavel': request.user,
        'data_emissao': timezone.now(),
    })


@login_required
@require_module_permission('materiais')
def relatorio_materiais_manutencao(request):
    """Compatibilidade com URL legada"""
    return relatorio_situacao_estoque(request)


@login_required
@require_module_permission('materiais')
def relatorio_baixas_materiais(request):
    """Relatório de saídas / baixas"""
    qs = MovimentacaoEstoque.objects.filter(
        subtipo__in=['REQUISICAO', 'DESCARTE']
    ).select_related('produto', 'usuario', 'orgao_requisitante', 'militar_requisitante').order_by('-data_movimentacao')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    if data_inicio:
        qs = qs.filter(data_movimentacao__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data_movimentacao__lte=data_fim)
    return render(request, 'estoque/relatorio_baixas.html', {
        'movimentacoes': qs,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'responsavel': request.user,
        'data_emissao': timezone.now(),
    })


# =============================================================================
# EXPORTAÇÃO
# =============================================================================

@login_required
@require_module_permission('materiais')
def exportar_produtos_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="materiais_consumo.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Código', 'Subcategoria', 'Categoria', 'Código SIAFÍSICO', 'Código CAT MAT',
        'Saldo', 'Unidade de Medida', 'Estoque Mínimo', 'Preço Médio',
        'Data Cotação', 'Conta Patrimonial', 'Status'
    ])
    for p in Produto.objects.select_related('categoria', 'unidade_medida', 'conta_patrimonial').all():
        writer.writerow([
            p.codigo, p.nome, p.categoria.nome if p.categoria else '',
            p.codigo_siafisico or '', p.codigo_cat_mat or '',
            p.saldo_calculado,
            p.unidade_medida.sigla if p.unidade_medida else '',
            p.estoque_minimo, p.preco_medio, p.data_cotacao or '',
            str(p.conta_patrimonial) if p.conta_patrimonial else '',
            p.get_status_display()
        ])
    return response


@login_required
@require_module_permission('materiais')
def exportar_movimentacoes_pdf(request):
    messages.info(request, _('Exportação PDF será implementada em breve.'))
    return redirect('estoque:lista_movimentacoes')


# =============================================================================
# AJAX
# =============================================================================

@login_required
@require_GET
def buscar_produtos_ajax(request):
    """Busca de produtos por nome/código para autocomplete"""
    q = request.GET.get('q', '')
    qs = Produto.objects.filter(
        Q(nome__icontains=q) | Q(codigo__icontains=q),
        status='ATIVO'
    )[:15]
    data = [{'id': p.pk, 'text': f'{p.codigo} — {p.nome}', 'saldo': str(p.saldo_calculado),
              'unidade': p.unidade_medida.sigla if p.unidade_medida else '',
              'preco': str(p.preco_medio)} for p in qs]
    return JsonResponse({'results': data})


@login_required
@require_GET
def buscar_produto_por_qr_ajax(request):
    """Busca produto por token de QR Code"""
    token = request.GET.get('token', '')
    try:
        p = Produto.objects.get(qr_code_token=token)
        return JsonResponse({
            'id': p.pk,
            'codigo': p.codigo,
            'nome': p.nome,
            'saldo': str(p.saldo_calculado),
        })
    except Produto.DoesNotExist:
        return JsonResponse({'error': 'Produto não encontrado'}, status=404)


@login_required
@require_GET
def buscar_lotes_ajax(request):
    """Busca lotes de um produto (PEPS — mais antigo primeiro)"""
    produto_id = request.GET.get('produto_id')
    qs = Lote.objects.filter(produto_id=produto_id, ativo=True).order_by('data_cadastro')
    data = [{'id': l.pk, 'text': f'Lote {l.numero_lote} — Qtd: {l.quantidade_atual}',
              'vencido': l.vencido, 'proximo_vencimento': l.proximo_vencimento} for l in qs]
    return JsonResponse({'lotes': data})


@login_required
@require_GET
def buscar_militar_por_re_ajax(request):
    """Busca policial por RE na tabela POLICIAIS (PAP §3)"""
    re = request.GET.get('re', '').strip()
    try:
        militar = Policial.objects.get(re=re, situacao='ATIVO')
        return JsonResponse({
            'id': militar.pk,
            're': militar.re,
            'qra': f"{militar.posto} {militar.nome}",
            'nome_completo': militar.nome,
        })
    except Policial.DoesNotExist:
        return JsonResponse({'error': f'RE {re} não encontrado na tabela de Policiais'}, status=404)


@login_required
@require_GET
def buscar_saldo_produto_ajax(request):
    """Retorna saldo disponível de um produto (para validação em tempo real na saída)"""
    produto_id = request.GET.get('produto_id')
    try:
        produto = Produto.objects.get(pk=produto_id)
        return JsonResponse({
            'saldo': str(produto.saldo_calculado),
            'estoque_minimo': str(produto.estoque_minimo),
            'precisa_reposicao': produto.precisa_reposicao,
            'unidade': produto.unidade_medida.sigla if produto.unidade_medida else '',
            'unidade_fornecimento': produto.unidade_fornecimento.nome if produto.unidade_fornecimento else 'Unidade',
        })
    except Produto.DoesNotExist:
        return JsonResponse({'error': 'Produto não encontrado'}, status=404)

@login_required
@require_module_permission('materiais')
def confirmacao_saida_material(request):
    """Tela de confirmação após registro de saída PAP §3"""
    mov_id = request.GET.get('id')
    mov = get_object_or_404(MovimentacaoEstoque, pk=mov_id)
    
    return render(request, 'estoque/confirmacao_saida.html', {
        'mov': mov,
        'policial': mov.militar_requisitante,
    })


@login_required
@require_module_permission('materiais')
def exportar_recibo_saida_pdf(request):
    """Gera recibo de saída PAP §3 em PDF (A5)"""
    mov_id = request.GET.get('id')
    mov = get_object_or_404(MovimentacaoEstoque, pk=mov_id)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A5, leftMargin=1*cm, rightMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
    elements = []
    
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=9, leading=11, alignment=1, textColor=colors.white, fontName='Helvetica-Bold')
    section_title = ParagraphStyle('SectionTitle', parent=styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=5)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=8, leading=10)
    
    # Cabeçalho
    header_data = [
        [Paragraph("BATALHÃO DE AÇÕES ESPECIAIS DE POLÍCIA - BAEP<br/>RECIBO DE SAÍDA DE MATERIAL (PAP §3)", header_style)]
    ]
    header_table = Table(header_data, colWidths=[12.8*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.navy),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # Info Recibo
    info_data = [
        [Paragraph(f"<b>Controle:</b> #{mov.pk:06d}", body_style), Paragraph(f"<b>Data:</b> {mov.data_movimentacao.strftime('%d/%m/%Y')}", body_style)],
        [Paragraph(f"<b>Usuário:</b> {mov.usuario.username}", body_style), Paragraph(f"<b>Finalidade:</b> {mov.subtipo}", body_style)]
    ]
    info_table = Table(info_data, colWidths=[6.4*cm, 6.4*cm])
    info_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(info_table)
    
    # Dados do Requisitante
    elements.append(Paragraph("DADOS DO REQUISITANTE", section_title))
    p = mov.militar_requisitante
    if p:
        pol_data = [
            [Paragraph(f"<b>Nome:</b> {p.nome}", body_style)],
            [Paragraph(f"<b>RE:</b> {p.re}          <b>Posto/Grad:</b> {p.get_posto_display()}", body_style)]
        ]
    else:
        pol_data = [
            [Paragraph(f"<b>Órgão:</b> {mov.orgao_requisitante.nome if mov.orgao_requisitante else 'Não informado'}", body_style)]
        ]
        
    pol_table = Table(pol_data, colWidths=[12.8*cm])
    pol_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(pol_table)
    
    # Materiais
    elements.append(Paragraph("MATERIAL FORNECIDO", section_title))
    mat_data = [
        ['Descrição do Material', 'Unidade', 'Qtd'],
        [Paragraph(f"<b>{mov.produto.nome}</b><br/>{mov.produto.codigo}", body_style), 
         str(mov.produto.unidade_medida.sigla if mov.produto.unidade_medida else 'UN'), 
         f"{mov.quantidade:g}"]
    ]
    
    mat_table = Table(mat_data, colWidths=[7.8*cm, 3*cm, 2*cm])
    mat_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(mat_table)
    
    # Assinaturas
    elements.append(Spacer(1, 1.5*cm))
    sig_data = [
        ["________________________________", "________________________________"],
        ["Assinatura do Recebedor", "Data e Hora Recebimento"],
        [f"RE/Nome: {'________________' if not p else p.re}", "___/___/_____  ___:___"]
    ]
    sig_table = Table(sig_data, colWidths=[6.4*cm, 6.4*cm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
    ]))
    elements.append(sig_table)
    
    elements.append(Spacer(1, 1.0*cm))
    sig_entrega = [
        ["________________________________"],
        ["Responsável pelo Almoxarifado (PAP)"],
        [f"{mov.usuario.get_full_name() or mov.usuario.username}"]
    ]
    entrega_table = Table(sig_entrega, colWidths=[12.8*cm])
    entrega_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
    ]))
    elements.append(entrega_table)
    
    # Rodapé fixo
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 6)
        canvas.drawCentredString(A5[0]/2.0, 0.5*cm, f"Controle de Estoque PAP §3 - BAEP - Página {doc.page}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="recibo_saida_{mov.pk}.pdf"'
    return response
