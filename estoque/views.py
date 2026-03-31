from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from reserva_baep.decorators import require_module_permission
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Sum, Count, F, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
# from weasyprint import HTML  # Comentado temporariamente devido a dependências do Windows
import json
import csv
from datetime import datetime, timedelta
from decimal import Decimal

from .models import (
    Categoria, UnidadeMedida, Fornecedor, Produto, Lote, NumeroSerie,
    MovimentacaoEstoque, Inventario, ItemInventario, AjusteEstoque
)
from .forms import (
    CategoriaForm, UnidadeMedidaForm, FornecedorForm, ProdutoForm, LoteForm, NumeroSerieForm,
    MovimentacaoEstoqueForm, InventarioForm, ItemInventarioForm, AjusteEstoqueForm
)


def is_admin_or_gestor(user):
    """Verifica se usuário é admin ou gestor"""
    return (user.is_superuser or 
            (hasattr(user, 'perfil') and user.perfil.nivel_acesso in ['ADMIN', 'GESTOR']))


@login_required
@require_module_permission('materiais')
def dashboard_estoque(request):
    """Dashboard principal do estoque"""
    # Estatísticas gerais
    total_produtos = Produto.objects.count()
    produtos_ativos = Produto.objects.filter(status='ATIVO').count()
    
    # Estatísticas de estoque
    estoque_total_valor = Produto.objects.aggregate(
        total=Sum(F('estoque_atual') * F('valor_unitario'))
    )['total'] or Decimal('0.00')
    
    # Produtos com estoque baixo
    produtos_estoque_baixo = 0
    produtos_criticos = 0
    
    for produto in Produto.objects.all():
        estoque_disponivel = produto.estoque_disponivel
        if estoque_disponivel <= produto.estoque_minimo:
            produtos_estoque_baixo += 1
        if estoque_disponivel <= (produto.estoque_minimo * Decimal('0.5')):
            produtos_criticos += 1
    
    # Movimentações recentes
    movimentacoes_recentes = MovimentacaoEstoque.objects.select_related(
        'produto', 'usuario'
    ).order_by('-data_hora')[:10]
    
    # Lotes próximos ao vencimento
    from django.utils import timezone
    data_limite = timezone.now().date() + timedelta(days=30)
    lotes_vencendo = Lote.objects.filter(
        data_validade__lte=data_limite,
        ativo=True
    ).count()
    
    context = {
        'total_produtos': total_produtos,
        'produtos_ativos': produtos_ativos,
        'estoque_total_valor': estoque_total_valor,
        'produtos_estoque_baixo': produtos_estoque_baixo,
        'produtos_criticos': produtos_criticos,
        'movimentacoes_recentes': movimentacoes_recentes,
        'lotes_vencendo': lotes_vencendo,
    }
    
    return render(request, 'estoque/dashboard.html', context)


# === CATEGORIAS ===
@login_required
@user_passes_test(is_admin_or_gestor)
@require_module_permission('materiais')
def lista_categorias(request):
    categorias = Categoria.objects.select_related('categoria_pai').all()
    
    termo_busca = request.GET.get('q')
    if termo_busca:
        categorias = categorias.filter(
            Q(nome__icontains=termo_busca) |
            Q(codigo__icontains=termo_busca) |
            Q(descricao__icontains=termo_busca)
        )
    
    paginator = Paginator(categorias, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'estoque/categorias/lista.html', {
        'page_obj': page_obj,
        'total_categorias': categorias.count(),
    })


@login_required
@user_passes_test(is_admin_or_gestor)
@require_module_permission('materiais')
def criar_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Categoria criada com sucesso!'))
            return redirect('estoque:lista_categorias')
    else:
        form = CategoriaForm()
    
    return render(request, 'estoque/categorias/form.html', {
        'form': form,
        'title': _('Nova Categoria'),
    })


@login_required
@user_passes_test(is_admin_or_gestor)
@require_module_permission('materiais')
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, _('Categoria atualizada com sucesso!'))
            return redirect('estoque:lista_categorias')
    else:
        form = CategoriaForm(instance=categoria)
    
    return render(request, 'estoque/categorias/form.html', {
        'form': form,
        'title': _('Editar Categoria'),
        'categoria': categoria,
    })


# === UNIDADES DE MEDIDA ===
@login_required
@user_passes_test(is_admin_or_gestor)
@require_module_permission('materiais')
def lista_unidades_medida(request):
    unidades = UnidadeMedida.objects.all()
    
    termo_busca = request.GET.get('q')
    if termo_busca:
        unidades = unidades.filter(
            Q(nome__icontains=termo_busca) |
            Q(sigla__icontains=termo_busca)
        )
    
    paginator = Paginator(unidades, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'estoque/unidades_medida/lista.html', {
        'page_obj': page_obj,
        'total_unidades': unidades.count(),
    })


@login_required
@user_passes_test(is_admin_or_gestor)
@require_module_permission('materiais')
def criar_unidade_medida(request):
    if request.method == 'POST':
        form = UnidadeMedidaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Unidade de medida criada com sucesso!'))
            return redirect('estoque:lista_unidades_medida')
    else:
        form = UnidadeMedidaForm()
    
    return render(request, 'estoque/unidades_medida/form.html', {
        'form': form,
        'title': _('Nova Unidade de Medida'),
    })


# === FORNECEDORES ===
@login_required
@require_module_permission('materiais')
def lista_fornecedores(request):
    fornecedores = Fornecedor.objects.all()
    
    termo_busca = request.GET.get('q')
    if termo_busca:
        fornecedores = fornecedores.filter(
            Q(nome__icontains=termo_busca) |
            Q(documento__icontains=termo_busca) |
            Q(email__icontains=termo_busca)
        )
    
    paginator = Paginator(fornecedores, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'estoque/fornecedores/lista.html', {
        'page_obj': page_obj,
        'total_fornecedores': fornecedores.count(),
    })


@login_required
@user_passes_test(is_admin_or_gestor)
@require_module_permission('materiais')
def criar_fornecedor(request):
    if request.method == 'POST':
        form = FornecedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Fornecedor criado com sucesso!'))
            return redirect('estoque:lista_fornecedores')
    else:
        form = FornecedorForm()
    
    return render(request, 'estoque/fornecedores/form.html', {
        'form': form,
        'title': _('Novo Fornecedor'),
    })


@login_required
@require_module_permission('materiais')
def detalhe_fornecedor(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    
    # Produtos fornecidos
    produtos = Produto.objects.filter(fornecedor_padrao=fornecedor)
    
    # Movimentações com este fornecedor
    movimentacoes = MovimentacaoEstoque.objects.filter(
        fornecedor=fornecedor
    ).order_by('-data_hora')[:10]
    
    return render(request, 'estoque/fornecedores/detalhe.html', {
        'fornecedor': fornecedor,
        'produtos': produtos,
        'movimentacoes': movimentacoes,
    })


# === PRODUTOS ===
@login_required
@require_module_permission('materiais')
def lista_produtos(request):
    produtos = Produto.objects.select_related('categoria', 'unidade_medida').all()
    
    termo_busca = request.GET.get('q')
    categoria_filter = request.GET.get('categoria')
    tipo_filter = request.GET.get('tipo')
    status_filter = request.GET.get('status')
    
    if termo_busca:
        produtos = produtos.filter(
            Q(nome__icontains=termo_busca) |
            Q(codigo__icontains=termo_busca) |
            Q(descricao__icontains=termo_busca)
        )
    
    if categoria_filter:
        produtos = produtos.filter(categoria_id=categoria_filter)
    
    if tipo_filter:
        produtos = produtos.filter(tipo_produto=tipo_filter)
    
    if status_filter:
        produtos = produtos.filter(status=status_filter)
    
    paginator = Paginator(produtos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for produto in page_obj:
        estoque_disp = produto.estoque_disponivel
        produto.estoque_baixo = estoque_disp <= produto.estoque_minimo
    
    # Filtros para o template
    categorias = Categoria.objects.filter(ativo=True)
    
    return render(request, 'estoque/produtos/lista.html', {
        'page_obj': page_obj,
        'total_produtos': produtos.count(),
        'categorias': categorias,
    })


@login_required
@user_passes_test(is_admin_or_gestor)
@require_module_permission('materiais')
def criar_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.criado_por = request.user
            produto.save()
            messages.success(request, _('Produto criado com sucesso!'))
            return redirect('estoque:lista_produtos')
    else:
        form = ProdutoForm()
    
    return render(request, 'estoque/produtos/form.html', {
        'form': form,
        'title': _('Novo Produto'),
    })


@login_required
@require_module_permission('materiais')
def detalhe_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    
    # Lotes do produto
    lotes = Lote.objects.filter(produto=produto, ativo=True)
    
    # Números de série do produto
    numeros_serie = NumeroSerie.objects.filter(produto=produto)
    
    # Movimentações recentes
    movimentacoes = MovimentacaoEstoque.objects.filter(
        produto=produto
    ).select_related('usuario').order_by('-data_hora')[:10]
    
    # Histórico de estoque (últimos 30 dias)
    from django.utils import timezone
    data_limite = timezone.now() - timedelta(days=30)
    historico = MovimentacaoEstoque.objects.filter(
        produto=produto,
        data_hora__gte=data_limite
    ).order_by('data_hora')
    
    return render(request, 'estoque/produtos/detalhe.html', {
        'produto': produto,
        'lotes': lotes,
        'numeros_serie': numeros_serie,
        'movimentacoes': movimentacoes,
        'historico': historico,
    })


@login_required
@user_passes_test(is_admin_or_gestor)
@require_module_permission('materiais')
def editar_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, _('Produto atualizado com sucesso!'))
            return redirect('estoque:detalhe_produto', pk=produto.pk)
    else:
        form = ProdutoForm(instance=produto)
    
    return render(request, 'estoque/produtos/form.html', {
        'form': form,
        'title': _('Editar Produto'),
        'produto': produto,
    })


# === MOVIMENTAÇÕES ===
@login_required
@require_module_permission('materiais')
def lista_movimentacoes(request):
    movimentacoes = MovimentacaoEstoque.objects.select_related(
        'produto', 'usuario', 'fornecedor', 'solicitante'
    ).all().order_by('-data_hora')
    
    termo_busca = request.GET.get('q')
    tipo_filter = request.GET.get('tipo')
    motivo_filter = request.GET.get('motivo')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if termo_busca:
        movimentacoes = movimentacoes.filter(
            Q(produto__nome__icontains=termo_busca) |
            Q(documento_referencia__icontains=termo_busca)
        )
    
    if tipo_filter:
        movimentacoes = movimentacoes.filter(tipo_movimentacao=tipo_filter)
    
    if motivo_filter:
        movimentacoes = movimentacoes.filter(motivo=motivo_filter)
    
    if data_inicio:
        movimentacoes = movimentacoes.filter(data_hora__date__gte=data_inicio)
    
    if data_fim:
        movimentacoes = movimentacoes.filter(data_hora__date__lte=data_fim)
    
    paginator = Paginator(movimentacoes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'estoque/movimentacoes/lista.html', {
        'page_obj': page_obj,
        'total_movimentacoes': movimentacoes.count(),
    })


@login_required
@user_passes_test(is_admin_or_gestor)
@require_module_permission('materiais')
def criar_movimentacao(request):
    if request.method == 'POST':
        form = MovimentacaoEstoqueForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.usuario = request.user
            movimentacao._request = request
            movimentacao.save()
            messages.success(request, _('Movimentação registrada com sucesso!'))
            return redirect('estoque:lista_movimentacoes')
    else:
        form = MovimentacaoEstoqueForm()
    
    return render(request, 'estoque/movimentacoes/form.html', {
        'form': form,
        'title': _('Nova Movimentação'),
    })


# === INVENTÁRIO ===
@login_required
@require_module_permission('materiais')
def lista_inventarios(request):
    inventarios = Inventario.objects.select_related('responsavel').all().order_by('-data_cadastro')
    
    termo_busca = request.GET.get('q')
    status_filter = request.GET.get('status')
    
    if termo_busca:
        inventarios = inventarios.filter(
            Q(numero__icontains=termo_busca) |
            Q(descricao__icontains=termo_busca)
        )
    
    if status_filter:
        inventarios = inventarios.filter(status=status_filter)
    
    paginator = Paginator(inventarios, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'estoque/inventarios/lista.html', {
        'page_obj': page_obj,
        'total_inventarios': inventarios.count(),
    })


@login_required
@user_passes_test(is_admin_or_gestor)
@require_module_permission('materiais')
def criar_inventario(request):
    if request.method == 'POST':
        form = InventarioForm(request.POST)
        if form.is_valid():
            inventario = form.save(commit=False)
            inventario.responsavel = request.user
            inventario.save()
            messages.success(request, _('Inventário criado com sucesso!'))
            return redirect('estoque:detalhe_inventario', pk=inventario.pk)
    else:
        form = InventarioForm()
    
    return render(request, 'estoque/inventarios/form.html', {
        'form': form,
        'title': _('Novo Inventário'),
    })


@login_required
@require_module_permission('materiais')
def detalhe_inventario(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    
    # Itens do inventário
    itens = ItemInventario.objects.select_related(
        'produto', 'contado_por'
    ).filter(inventario=inventario)
    
    # Estatísticas
    total_itens = itens.count()
    itens_contados = itens.filter(contado_em__isnull=False).count()
    itens_com_diferenca = itens.exclude(diferenca=0).count()
    
    return render(request, 'estoque/inventarios/detalhe.html', {
        'inventario': inventario,
        'itens': itens,
        'total_itens': total_itens,
        'itens_contados': itens_contados,
        'itens_com_diferenca': itens_com_diferenca,
    })


@login_required
@user_passes_test(is_admin_or_gestor)
@require_module_permission('materiais')
def iniciar_inventario(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    
    if inventario.status != 'PLANEJADO':
        messages.error(request, _('Apenas inventários planejados podem ser iniciados.'))
        return redirect('estoque:detalhe_inventario', pk=pk)
    
    # Adicionar todos os produtos ao inventário
    produtos = Produto.objects.filter(status='ATIVO')
    
    for produto in produtos:
        ItemInventario.objects.get_or_create(
            inventario=inventario,
            produto=produto,
            defaults={
                'quantidade_sistema': produto.estoque_atual,
            }
        )
    
    inventario.status = 'EM_ANDAMENTO'
    inventario.data_inicio = timezone.now()
    inventario.save()
    
    messages.success(request, _('Inventário iniciado com sucesso!'))
    return redirect('estoque:detalhe_inventario', pk=pk)


@login_required
@require_module_permission('materiais')
def contar_item_inventario(request, pk):
    """View para contagem de item do inventário via AJAX"""
    item = get_object_or_404(ItemInventario, pk=pk)
    
    if request.method == 'POST':
        quantidade_contada = request.POST.get('quantidade_contada')
        observacoes = request.POST.get('observacoes', '')
        
        try:
            quantidade_contada = Decimal(quantidade_contada)
        except (ValueError, TypeError):
            return JsonResponse({'error': _('Quantidade inválida.')}, status=400)
        
        item.quantidade_contada = quantidade_contada
        item.observacoes = observacoes
        item.contado_por = request.user
        item.contado_em = timezone.now()
        item.status_contagem = 'CONTRADO'
        item.save()

        inventario = item.inventario
        redirect_url = None
        if inventario.status == 'CONCLUIDO':
            redirect_url = f"/estoque/produtos/?inventario_concluido={inventario.pk}"
        
        return JsonResponse({
            'success': True,
            'diferenca': str(item.diferenca),
            'status_contagem': item.status_contagem,
            'inventario_status': inventario.status,
            'redirect_url': redirect_url,
        })
    
    return JsonResponse({'error': _('Método não permitido.')}, status=405)


# === RELATÓRIOS ===
@login_required
@require_module_permission('materiais')
def relatorio_estoque_baixo(request):
    """Relatório de produtos com estoque baixo"""
    produtos_baixo = []
    produtos_criticos = []
    
    for produto in Produto.objects.select_related('categoria', 'unidade_medida').all():
        estoque_disponivel = produto.estoque_disponivel
        if estoque_disponivel <= produto.estoque_minimo:
            produtos_baixo.append(produto)
        if estoque_disponivel <= (produto.estoque_minimo * Decimal('0.5')):
            produtos_criticos.append(produto)
    
    context = {
        'produtos_baixo': produtos_baixo,
        'produtos_criticos': produtos_criticos,
    }
    
    return render(request, 'estoque/relatorios/estoque_baixo.html', context)


@login_required
@require_module_permission('materiais')
def relatorio_movimentacoes_periodo(request):
    """Relatório de movimentações por período"""
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    gerado_em = timezone.localtime(timezone.now())
    gerado_por = request.user
    
    movimentacoes = MovimentacaoEstoque.objects.all()
    
    if data_inicio:
        movimentacoes = movimentacoes.filter(data_hora__date__gte=data_inicio)
    
    if data_fim:
        movimentacoes = movimentacoes.filter(data_hora__date__lte=data_fim)
    
    # Agrupar por tipo
    resumo = movimentacoes.values('tipo_movimentacao').annotate(
        total_quantidade=Sum('quantidade'),
        total_valor=Sum('valor_total')
    ).order_by('tipo_movimentacao')
    
    return render(request, 'estoque/relatorios/movimentacoes_periodo.html', {
        'movimentacoes': movimentacoes.select_related('produto', 'usuario'),
        'resumo': resumo,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'gerado_em': gerado_em,
        'gerado_por': gerado_por,
    })


@login_required
@require_module_permission('materiais')
def exportar_produtos_csv(request):
    """Exporta lista de produtos para CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="produtos.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Código', 'Número do empenho', 'Nome', 'Categoria', 'Estoque Atual', 'Estoque Mínimo', 'Valor Unitário', 'Valor Total'])
    
    produtos = Produto.objects.select_related('categoria').all()
    for produto in produtos:
        writer.writerow([
            produto.codigo,
            produto.codigo_barras or '',
            produto.nome,
            produto.categoria.nome if produto.categoria else '',
            produto.estoque_atual,
            produto.estoque_minimo,
            produto.valor_unitario,
            produto.valor_total,
        ])
    
    return response


@login_required
@require_module_permission('materiais')
def exportar_movimentacoes_pdf(request):
    """Exporta movimentações para PDF"""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.styles import ParagraphStyle
    except ImportError:
        messages.warning(request, _('Para exportar PDF, instale a dependência: pip install reportlab'))
        return redirect('estoque:lista_movimentacoes')

    from io import BytesIO

    termo_busca = request.GET.get('q')
    tipo_filter = request.GET.get('tipo')
    motivo_filter = request.GET.get('motivo')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    movimentacoes = MovimentacaoEstoque.objects.select_related('produto', 'usuario').all().order_by('-data_hora')

    gerado_em = timezone.now()
    gerado_por = request.user

    if termo_busca:
        movimentacoes = movimentacoes.filter(
            Q(produto__nome__icontains=termo_busca) |
            Q(documento_referencia__icontains=termo_busca)
        )

    if tipo_filter:
        movimentacoes = movimentacoes.filter(tipo_movimentacao=tipo_filter)

    if motivo_filter:
        movimentacoes = movimentacoes.filter(motivo=motivo_filter)

    if data_inicio:
        movimentacoes = movimentacoes.filter(data_hora__date__gte=data_inicio)

    if data_fim:
        movimentacoes = movimentacoes.filter(data_hora__date__lte=data_fim)

    buffer = BytesIO()
    pagesize = landscape(A4)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title=str(_('Movimentações de Estoque')),
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TitleCentered',
        parent=styles['Title'],
        alignment=TA_CENTER,
    )

    elements = []
    elements.append(Paragraph(str(_('Movimentações de Estoque')), title_style))
    if data_inicio or data_fim:
        periodo = f"{data_inicio or ''} - {data_fim or ''}".strip()
        elements.append(Paragraph(f"{_('Período')}: {periodo}", styles['Normal']))
    elements.append(Spacer(1, 12))

    header = [
        str(_('Data/Hora')),
        str(_('Produto')),
        str(_('Tipo')),
        str(_('Motivo')),
        str(_('Qtd')),
        str(_('Usuário')),
    ]
    data = [header]

    cell_style = ParagraphStyle(
        name='Cell',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
    )

    for mov in movimentacoes:
        data.append([
            timezone.localtime(mov.data_hora).strftime('%d/%m/%Y %H:%M') if mov.data_hora else '',
            Paragraph(f"{mov.produto.codigo} - {mov.produto.nome}", cell_style) if mov.produto else '',
            mov.get_tipo_movimentacao_display() if hasattr(mov, 'get_tipo_movimentacao_display') else str(mov.tipo_movimentacao),
            mov.get_motivo_display() if hasattr(mov, 'get_motivo_display') else str(mov.motivo),
            str(mov.quantidade),
            mov.usuario.get_username() if getattr(mov, 'usuario', None) else '',
        ])

    available_width = pagesize[0] - (doc.leftMargin + doc.rightMargin)
    col_ratios = [0.13, 0.40, 0.12, 0.15, 0.07, 0.13]
    col_widths = [available_width * r for r in col_ratios]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
    ]))

    elements.append(table)

    def _footer(canvas, doc_):
        canvas.saveState()

        try:
            from django.contrib.staticfiles import finders

            logo_path = finders.find('img/logo_baep.png')
            if logo_path:
                img = ImageReader(logo_path)
                iw, ih = img.getSize()
                target_h = 1.1 * cm
                target_w = (iw / float(ih)) * target_h
                x = doc_.leftMargin
                y = doc_.pagesize[1] - doc_.topMargin - target_h - (0.3 * cm)
                canvas.drawImage(img, x, y, width=target_w, height=target_h, mask='auto')
        except Exception:
            pass

        canvas.setFont('Helvetica', 8)
        usuario = gerado_por.get_username() if gerado_por else ''
        texto = f"Gerado em {gerado_em.strftime('%d/%m/%Y %H:%M')} por {usuario}"
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(doc_.pagesize[0] - doc_.rightMargin, 0.75 * cm, texto)
        canvas.restoreState()

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="movimentacoes.pdf"'
    return response
    
    # Código comentado até resolver dependências do weasyprint
    """
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    movimentacoes = MovimentacaoEstoque.objects.all()
    
    if data_inicio:
        movimentacoes = movimentacoes.filter(data_hora__date__gte=data_inicio)
    
    if data_fim:
        movimentacoes = movimentacoes.filter(data_hora__date__lte=data_fim)
    
    movimentacoes = movimentacoes.select_related('produto', 'usuario').order_by('-data_hora')
    
    html_string = render_to_string('estoque/relatorios/movimentacoes_pdf.html', {
        'movimentacoes': movimentacoes,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'request': request,
    })
    
    html = HTML(string=html_string)
    pdf = html.write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="movimentacoes.pdf"'
    
    return response
    """


# === AJAX ===
@login_required
@require_module_permission('materiais')
def buscar_produtos_ajax(request):
    """Busca produtos via AJAX para selects"""
    termo = request.GET.get('q', '')
    produtos = Produto.objects.filter(
        Q(nome__icontains=termo) |
        Q(codigo__icontains=termo)
    ).filter(status='ATIVO')[:20]
    
    data = []
    for produto in produtos:
        data.append({
            'id': produto.pk,
            'text': f"{produto.codigo} - {produto.nome}",
            'estoque_atual': str(produto.estoque_atual),
            'estoque_disponivel': str(produto.estoque_disponivel),
        })
    
    return JsonResponse(data, safe=False)


@login_required
@require_module_permission('materiais')
def buscar_lotes_ajax(request):
    """Busca lotes de um produto via AJAX"""
    produto_id = request.GET.get('produto_id')
    if not produto_id:
        return JsonResponse({'lotes': []})
    
    lotes = Lote.objects.filter(
        produto_id=produto_id,
        ativo=True,
        quantidade_atual__gt=0
    ).order_by('-data_cadastro')
    
    lotes_data = []
    for lote in lotes:
        lotes_data.append({
            'id': lote.id,
            'text': str(lote),
            'quantidade_atual': float(lote.quantidade_atual),
            'data_validade': lote.data_validade.strftime('%Y-%m-%d') if lote.data_validade else None,
            'vencido': lote.vencido,
        })
    
    return JsonResponse({'lotes': lotes_data})


@login_required
@require_module_permission('materiais')
def buscar_produto_por_qr_ajax(request):
    """Busca produto pelo token do QR Code (UUID)"""
    token = (request.GET.get('token') or '').strip()
    if not token:
        return JsonResponse({'found': False, 'error': _('Token não informado.')}, status=400)

    try:
        produto = Produto.objects.get(qr_code_token=token)
    except Produto.DoesNotExist:
        return JsonResponse({'found': False, 'error': _('Produto não encontrado para este QR Code.')}, status=404)
    except Exception:
        return JsonResponse({'found': False, 'error': _('Token inválido.')}, status=400)

    return JsonResponse({
        'found': True,
        'id': produto.id,
        'codigo': produto.codigo,
        'nome': produto.nome,
    })


@login_required
@require_module_permission('materiais')
def relatorio_materiais_manutencao(request):
    """Relatório de materiais em manutenção"""
    # Filtros
    categoria_id = request.GET.get('categoria')
    status = request.GET.get('status', 'todos')
    
    produtos = Produto.objects.all()
    
    # Filtrar por categoria
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    
    # Filtrar por status
    if status != 'todos':
        produtos = produtos.filter(status=status)
    
    # Buscar números de série em manutenção
    numeros_manutencao = NumeroSerie.objects.filter(status='MANUTENCAO').select_related('produto')
    
    # Produtos com controle de número de série
    produtos_com_numeros = []
    for num_serie in numeros_manutencao:
        produtos_com_numeros.append({
            'codigo': num_serie.produto.codigo,
            'nome': num_serie.produto.nome,
            'categoria': num_serie.produto.categoria.nome if num_serie.produto.categoria else '',
            'numero_serie': num_serie.numero_serie,
            'patrimonio': num_serie.patrimonio or '',
            'localizacao': num_serie.localizacao or '',
            'responsavel': str(num_serie.responsavel) if num_serie.responsavel else '',
            'conta_contabil': num_serie.produto.conta_contabil or '',
            'localizacao_fisica': num_serie.produto.localizacao_fisica or '',
            'data_cadastro': num_serie.data_cadastro.strftime('%d/%m/%Y'),
        })
    
    # Produtos sem controle de número de série (status MANUTENCAO)
    produtos_sem_numeros = produtos.filter(
        status='MANUTENCAO',
        controla_numero_serie=False
    ).select_related('categoria')
    
    for produto in produtos_sem_numeros:
        produtos_com_numeros.append({
            'codigo': produto.codigo,
            'nome': produto.nome,
            'categoria': produto.categoria.nome if produto.categoria else '',
            'numero_serie': 'N/A',
            'patrimonio': 'N/A',
            'localizacao': 'N/A',
            'responsavel': 'N/A',
            'conta_contabil': produto.conta_contabil or '',
            'localizacao_fisica': produto.localizacao_fisica or '',
            'data_cadastro': 'N/A',
        })
    
    # Ordenar por nome
    produtos_com_numeros.sort(key=lambda x: x['nome'])
    
    context = {
        'produtos': produtos_com_numeros,
        'categorias': Categoria.objects.all(),
        'categoria_filtro': categoria_id,
        'status_filtro': status,
        'total': len(produtos_com_numeros),
    }
    
    return render(request, 'estoque/relatorios/materiais_manutencao.html', context)


@login_required
@require_module_permission('materiais')
def relatorio_baixas_materiais(request):
    """Relatório de baixas de materiais"""
    # Filtros
    categoria_id = request.GET.get('categoria')
    status = request.GET.get('status', 'todos')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    produtos = Produto.objects.all()
    
    # Filtrar por categoria
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    
    # Filtrar por status
    if status != 'todos':
        produtos = produtos.filter(status=status)
    else:
        # Por padrão, mostrar apenas baixados e obsoletos
        produtos = produtos.filter(status__in=['BAIXADO', 'OBSOLETO'])
    
    # Filtrar por período
    if data_inicio:
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            produtos = produtos.filter(data_atualizacao__date__gte=data_inicio)
        except ValueError:
            pass
    
    if data_fim:
        try:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            produtos = produtos.filter(data_atualizacao__date__lte=data_fim)
        except ValueError:
            pass
    
    # Buscar números de série baixados
    numeros_baixados = NumeroSerie.objects.filter(
        status__in=['BAIXADO', 'OBSOLETO']
    ).select_related('produto')
    
    # Produtos com controle de número de série
    produtos_baixados = []
    for num_serie in numeros_baixados:
        produtos_baixados.append({
            'codigo': num_serie.produto.codigo,
            'nome': num_serie.produto.nome,
            'categoria': num_serie.produto.categoria.nome if num_serie.produto.categoria else '',
            'numero_serie': num_serie.numero_serie,
            'patrimonio': num_serie.patrimonio or '',
            'status': num_serie.get_status_display(),
            'localizacao': num_serie.localizacao or '',
            'responsavel': str(num_serie.responsavel) if num_serie.responsavel else '',
            'conta_contabil': num_serie.produto.conta_contabil or '',
            'localizacao_fisica': num_serie.produto.localizacao_fisica or '',
            'data_baixa': num_serie.data_atualizacao.strftime('%d/%m/%Y') if num_serie.data_atualizacao else '',
            'motivo_baixa': 'Baixa registrada no sistema',
        })
    
    # Produtos sem controle de número de série (status BAIXADO/OBSOLETO)
    produtos_sem_numeros = produtos.filter(
        status__in=['BAIXADO', 'OBSOLETO'],
        controla_numero_serie=False
    ).select_related('categoria')
    
    for produto in produtos_sem_numeros:
        produtos_baixados.append({
            'codigo': produto.codigo,
            'nome': produto.nome,
            'categoria': produto.categoria.nome if produto.categoria else '',
            'numero_serie': 'N/A',
            'patrimonio': 'N/A',
            'status': produto.get_status_display(),
            'localizacao': 'N/A',
            'responsavel': 'N/A',
            'conta_contabil': produto.conta_contabil or '',
            'localizacao_fisica': produto.localizacao_fisica or '',
            'data_baixa': produto.data_atualizacao.strftime('%d/%m/%Y') if produto.data_atualizacao else '',
            'motivo_baixa': 'Baixa registrada no sistema',
        })
    
    # Ordenar por data de baixa (mais recentes primeiro)
    produtos_baixados.sort(key=lambda x: x['data_baixa'], reverse=True)
    
    context = {
        'produtos': produtos_baixados,
        'categorias': Categoria.objects.all(),
        'categoria_filtro': categoria_id,
        'status_filtro': status,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total': len(produtos_baixados),
    }
    
    return render(request, 'estoque/relatorios/baixas_materiais.html', context)


@login_required
@require_module_permission('materiais')
def relatorio_situacao_estoque(request):
    """Relatório de situação atual do estoque"""
    # Filtros
    categoria_id = request.GET.get('categoria')
    status = request.GET.get('status', 'todos')
    tipo_produto = request.GET.get('tipo_produto', 'todos')
    estoque_baixo = request.GET.get('estoque_baixo') == 'on'
    
    produtos = Produto.objects.all().select_related('categoria', 'fornecedor_padrao')
    
    # Filtrar por categoria
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    
    # Filtrar por status
    if status != 'todos':
        produtos = produtos.filter(status=status)
    
    # Filtrar por tipo de produto
    if tipo_produto != 'todos':
        produtos = produtos.filter(tipo_produto=tipo_produto)
    
    # Filtrar estoque baixo
    if estoque_baixo:
        produtos = produtos.filter(estoque_disponivel__lte=models.F('estoque_minimo'))
    
    # Montar dados do relatório
    produtos_situacao = []
    valor_total_estoque = 0
    
    for produto in produtos:
        # Calcular valor total em estoque
        valor_total = float(produto.estoque_atual) * float(produto.valor_unitario)
        valor_total_estoque += valor_total
        
        # Status do estoque
        if produto.estoque_disponivel <= 0:
            status_estoque = 'ESGOTADO'
            cor_status = 'danger'
        elif produto.estoque_critico:
            status_estoque = 'CRÍTICO'
            cor_status = 'warning'
        elif produto.precisa_reposicao:
            status_estoque = 'BAIXO'
            cor_status = 'info'
        else:
            status_estoque = 'NORMAL'
            cor_status = 'success'
        
        produtos_situacao.append({
            'codigo': produto.codigo,
            'codigo_barras': produto.codigo_barras or '',
            'nome': produto.nome,
            'categoria': produto.categoria.nome if produto.categoria else '',
            'tipo_produto': produto.get_tipo_produto_display(),
            'status': produto.get_status_display(),
            'estoque_atual': float(produto.estoque_atual),
            'estoque_minimo': float(produto.estoque_minimo),
            'estoque_maximo': float(produto.estoque_maximo),
            'estoque_reservado': float(produto.estoque_reservado),
            'estoque_disponivel': float(produto.estoque_disponivel),
            'valor_unitario': float(produto.valor_unitario),
            'valor_total': valor_total,
            'status_estoque': status_estoque,
            'cor_status': cor_status,
            'conta_contabil': produto.conta_contabil or '',
            'localizacao_fisica': produto.localizacao_fisica or '',
            'fornecedor': produto.fornecedor_padrao.nome if produto.fornecedor_padrao else '',
        })
    
    # Ordenar por nome
    produtos_situacao.sort(key=lambda x: x['nome'])
    
    # Estatísticas
    total_produtos = len(produtos_situacao)
    produtos_esgotados = len([p for p in produtos_situacao if p['status_estoque'] == 'ESGOTADO'])
    produtos_criticos = len([p for p in produtos_situacao if p['status_estoque'] == 'CRÍTICO'])
    produtos_baixo = len([p for p in produtos_situacao if p['status_estoque'] == 'BAIXO'])
    produtos_normais = len([p for p in produtos_situacao if p['status_estoque'] == 'NORMAL'])
    
    context = {
        'produtos': produtos_situacao,
        'categorias': Categoria.objects.all(),
        'categoria_filtro': categoria_id,
        'status_filtro': status,
        'tipo_produto_filtro': tipo_produto,
        'estoque_baixo_filtro': estoque_baixo,
        'total_produtos': total_produtos,
        'produtos_esgotados': produtos_esgotados,
        'produtos_criticos': produtos_criticos,
        'produtos_baixo': produtos_baixo,
        'produtos_normais': produtos_normais,
        'valor_total_estoque': valor_total_estoque,
        'TIPO_PRODUTO_CHOICES': Produto.TIPO_PRODUTO_CHOICES,
        'STATUS_CHOICES': Produto.STATUS_CHOICES,
    }
    
    return render(request, 'estoque/relatorios/situacao_estoque.html', context)


@login_required
@require_module_permission('materiais')
def relatorio_inventarios(request):
    """Relatório de inventários"""
    # Filtros
    status = request.GET.get('status', 'todos')
    tipo_inventario = request.GET.get('tipo_inventario', 'todos')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    inventarios = Inventario.objects.all().select_related('responsavel')
    
    # Filtrar por status
    if status != 'todos':
        inventarios = inventarios.filter(status=status)
    
    # Filtrar por tipo de inventário
    if tipo_inventario != 'todos':
        inventarios = inventarios.filter(tipo_inventario=tipo_inventario)
    
    # Filtrar por período
    if data_inicio:
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            inventarios = inventarios.filter(data_cadastro__date__gte=data_inicio)
        except ValueError:
            pass
    
    if data_fim:
        try:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            inventarios = inventarios.filter(data_cadastro__date__lte=data_fim)
        except ValueError:
            pass
    
    # Montar dados do relatório
    inventarios_dados = []
    
    for inventario in inventarios:
        # Contar itens
        total_itens = inventario.itens.count()
        itens_contados = inventario.itens.filter(quantidade_contada__isnull=False).count()
        itens_pendentes = total_itens - itens_contados
        
        # Calcular diferenças
        itens_com_diferenca = 0
        valor_total_diferenca = 0
        
        for item in inventario.itens.all():
            if item.quantidade_contada is not None:
                diferenca = item.quantidade_contada - item.quantidade_sistema
                if diferenca != 0:
                    itens_com_diferenca += 1
                    valor_total_diferenca += abs(diferenca) * item.produto.valor_unitario
        
        # Progresso
        progresso = (itens_contados / total_itens * 100) if total_itens > 0 else 0
        
        inventarios_dados.append({
            'numero': inventario.numero,
            'descricao': inventario.descricao,
            'tipo_inventario': inventario.get_tipo_inventario_display(),
            'status': inventario.get_status_display(),
            'responsavel': str(inventario.responsavel) if inventario.responsavel else '',
            'data_cadastro': inventario.data_cadastro.strftime('%d/%m/%Y %H:%M') if inventario.data_cadastro else '',
            'data_prevista_fim': inventario.data_prevista_fim.strftime('%d/%m/%Y %H:%M') if inventario.data_prevista_fim else '',
            'data_conclusao': inventario.data_conclusao.strftime('%d/%m/%Y %H:%M') if inventario.data_conclusao else '',
            'total_itens': total_itens,
            'itens_contados': itens_contados,
            'itens_pendentes': itens_pendentes,
            'itens_com_diferenca': itens_com_diferenca,
            'valor_total_diferenca': valor_total_diferenca,
            'progresso': progresso,
            'observacoes': inventario.observacoes or '',
        })
    
    # Ordenar por data de cadastro (mais recentes primeiro)
    inventarios_dados.sort(key=lambda x: x['data_cadastro'], reverse=True)
    
    # Estatísticas
    total_inventarios = len(inventarios_dados)
    inventarios_em_andamento = len([i for i in inventarios_dados if i['status'] == 'Em Andamento'])
    inventarios_concluidos = len([i for i in inventarios_dados if i['status'] == 'Concluído'])
    inventarios_pendentes = len([i for i in inventarios_dados if i['status'] == 'Pendente'])
    
    context = {
        'inventarios': inventarios_dados,
        'status_filtro': status,
        'tipo_inventario_filtro': tipo_inventario,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total_inventarios': total_inventarios,
        'inventarios_em_andamento': inventarios_em_andamento,
        'inventarios_concluidos': inventarios_concluidos,
        'inventarios_pendentes': inventarios_pendentes,
        'TIPO_INVENTARIO_CHOICES': Inventario.TIPO_INVENTARIO_CHOICES,
        'STATUS_INVENTARIO_CHOICES': Inventario.STATUS_CHOICES,
    }
    
    return render(request, 'estoque/relatorios/inventarios.html', context)

