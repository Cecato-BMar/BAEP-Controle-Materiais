import os
import io
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils.translation import gettext as _

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.utils import ImageReader

from .models import Relatorio
from .forms import (
    RelatorioMateriaisForm, 
    RelatorioMovimentacoesForm, 
    RelatorioPatrimonioForm, 
    RelatorioFrotaForm,
    RelatorioEstoqueMovimentacoesForm,
    RelatorioSituacaoAtualForm
)
from .utils import PDFReportGenerator
from . import providers
from reserva_baep.decorators import require_module_permission

def _draw_logo(canvas_, doc_):
    try:
        from django.contrib.staticfiles import finders
        logo_path = finders.find('img/logo_baep.png')
        if not logo_path:
            return
        img = ImageReader(logo_path)
        iw, ih = img.getSize()
        target_h = 1.0 * cm
        target_w = (iw / float(ih)) * target_h
        x = doc_.leftMargin
        y = doc_.pagesize[1] - doc_.topMargin + (0.2 * cm)
        canvas_.drawImage(img, x, y, width=target_w, height=target_h, mask='auto')
    except Exception:
        return

def _gerar_pdf_unificado(request, tipo_chave, titulo, filters):
    """Função central para geração de PDFs usando o motor unificado"""
    provider_map = {
        'SITUACAO_ATUAL': providers.SituacaoAtualProvider,
        'MATERIAIS': providers.MateriaisProvider,
        'MATERIAIS_EM_USO': providers.MateriaisProvider,
        'MATERIAIS_DISPONIVEIS': providers.MateriaisProvider,
        'MOVIMENTACOES': providers.MovimentacoesProvider,
        'MOVIMENTACOES_DIA': providers.MovimentacoesProvider,
        'FROTA_GERAL': providers.FrotaGeralProvider,
        'ABASTECIMENTO': providers.FrotaAbastecimentoProvider,
        'MANUTENCAO': providers.FrotaManutencaoProvider,
        'PATRIMONIO_INVENTARIO': providers.PatrimonioProvider,
        'ESTOQUE_MOVIMENTACOES': providers.EstoqueMovimentacoesProvider,
    }
    
    provider_class = provider_map.get(tipo_chave)
    if not provider_class:
        return None
        
    buffer = io.BytesIO()
    generator = PDFReportGenerator(buffer, titulo, user=request.user)
    provider = provider_class(generator)
    
    # Gera o PDF
    elements = provider.get_elements(filters)
    generator.generate(elements)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    # Salva no banco de dados
    relatorio = Relatorio.objects.create(
        titulo=titulo,
        tipo=tipo_chave,
        modulo='RESERVA', # Ajustado dinamicamente abaixo se necessário
        gerado_por=request.user,
        observacoes=filters.get('observacoes', '')
    )
    
    # Define o módulo com base na chave
    if 'FROTA' in tipo_chave or tipo_chave in ['ABASTECIMENTO', 'MANUTENCAO']:
        relatorio.modulo = 'FROTA'
    elif 'PATRIMONIO' in tipo_chave:
        relatorio.modulo = 'PATRIMONIO'
    elif 'ESTOQUE' in tipo_chave:
        relatorio.modulo = 'ESTOQUE'
    relatorio.save()
    
    filename = f"{tipo_chave.lower()}_{relatorio.pk}.pdf"
    relatorio.arquivo_pdf.save(filename, io.BytesIO(pdf_content))
    return relatorio

@login_required
def lista_relatorios(request):
    modulos_acesso = []
    if request.user.is_superuser or request.user.groups.filter(name='reserva_armas').exists():
        modulos_acesso.append('RESERVA')
    if request.user.is_superuser or request.user.groups.filter(name='patrimonio').exists():
        modulos_acesso.append('PATRIMONIO')
    if request.user.is_superuser or request.user.groups.filter(name='estoque').exists():
        modulos_acesso.append('ESTOQUE')
    if request.user.is_superuser or request.user.groups.filter(name='frota').exists():
        modulos_acesso.append('FROTA')

    if not modulos_acesso:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Você não tem acesso a nenhum módulo de relatórios.")

    relatorios = Relatorio.objects.filter(modulo__in=modulos_acesso).order_by('-data_geracao')
    
    # Paginação
    paginator = Paginator(relatorios, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'relatorios/lista_relatorios.html', {
        'relatorios': page_obj,
        'page_obj': page_obj,
        'total_relatorios': relatorios.count(),
    })

@login_required
def detalhe_relatorio(request, relatorio_id):
    relatorio = get_object_or_404(Relatorio, pk=relatorio_id)
    return render(request, 'relatorios/detalhe_relatorio.html', {'relatorio': relatorio})

@login_required
def download_relatorio(request, relatorio_id):
    relatorio = get_object_or_404(Relatorio, pk=relatorio_id)
    if not relatorio.arquivo_pdf:
        messages.error(request, _('Arquivo PDF não encontrado.'))
        return redirect('relatorios:lista_relatorios')
    return FileResponse(open(relatorio.arquivo_pdf.path, 'rb'), content_type='application/pdf')

@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_situacao(request):
    if request.method == 'POST':
        form = RelatorioSituacaoAtualForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo') or "Situação Geral do Arsenal"
            relatorio = _gerar_pdf_unificado(request, 'SITUACAO_ATUAL', titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, 'Relatório Gerado com Sucesso!')
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioSituacaoAtualForm()
    
    from materiais.models import Material
    stats = {
        'total': Material.objects.count(),
        'disponiveis': Material.objects.filter(status='DISPONIVEL').count(),
        'em_uso': Material.objects.filter(status='EM_USO').count(),
        'manutencao': Material.objects.filter(status='MANUTENCAO').count(),
    }
    return render(request, 'relatorios/form_relatorio_situacao.html', {'form': form, 'stats': stats})

@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_materiais(request):
    if request.method == 'POST':
        form = RelatorioMateriaisForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data.get('tipo_relatorio', 'MATERIAIS')
            titulo = form.cleaned_data.get('titulo') or "Inventário de Materiais"
            relatorio = _gerar_pdf_unificado(request, tipo, titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, _('Relatório Gerado com Sucesso!'))
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioMateriaisForm()
    
    from materiais.models import Material
    return render(request, 'relatorios/form_relatorio_materiais.html', {
        'form': form,
        'total_carga': Material.objects.count(),
        'disponiveis': Material.objects.filter(status='DISPONIVEL').count(),
        'em_manutencao': Material.objects.filter(status='MANUTENCAO').count()
    })

@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_movimentacoes(request):
    if request.method == 'POST':
        form = RelatorioMovimentacoesForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data.get('tipo_relatorio', 'MOVIMENTACOES')
            titulo = form.cleaned_data.get('titulo') or "Histórico de Movimentações"
            relatorio = _gerar_pdf_unificado(request, tipo, titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, _('Relatório Gerado com Sucesso!'))
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioMovimentacoesForm()
    
    from movimentacoes.models import Movimentacao
    hoje = timezone.now().date()
    return render(request, 'relatorios/form_relatorio_movimentacoes.html', {
        'form': form,
        'movs_30_dias': Movimentacao.objects.filter(data_hora__date__gte=hoje - datetime.timedelta(days=30)).count(),
        'saidas_hoje': Movimentacao.objects.filter(data_hora__date=hoje, tipo='SAIDA').count()
    })

@login_required
@require_module_permission('materiais')
def gerar_relatorio_estoque_movimentacoes(request):
    if request.method == 'POST':
        form = RelatorioEstoqueMovimentacoesForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo') or "Relatório de Estoque"
            relatorio = _gerar_pdf_unificado(request, 'ESTOQUE_MOVIMENTACOES', titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, _('Relatório Gerado com Sucesso!'))
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioEstoqueMovimentacoesForm()
    
    from estoque.models import Produto, MovimentacaoEstoque
    return render(request, 'relatorios/form_relatorio_estoque_movimentacoes.html', {
        'form': form,
        'total_itens': Produto.objects.count(),
        'movs_estoque_30d': MovimentacaoEstoque.objects.filter(data_hora__date__gte=timezone.now().date() - datetime.timedelta(days=30)).count()
    })

@login_required
@require_module_permission('patrimonio')
def gerar_relatorio_patrimonio(request):
    if request.method == 'POST':
        form = RelatorioPatrimonioForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo') or "Inventário de Patrimônio"
            relatorio = _gerar_pdf_unificado(request, 'PATRIMONIO_INVENTARIO', titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, 'Relatório Gerado com Sucesso!')
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioPatrimonioForm()
    
    from patrimonio.models import ItemPatrimonial
    return render(request, 'relatorios/form_relatorio_patrimonio.html', {
        'form': form,
        'items_count': ItemPatrimonial.objects.count(),
        'localizacoes_count': ItemPatrimonial.objects.values('localizacao').distinct().count()
    })

@login_required
@require_module_permission('frota')
def gerar_relatorio_viaturas(request):
    if request.method == 'POST':
        form = RelatorioFrotaForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data.get('tipo_relatorio', 'FROTA_GERAL')
            titulo = form.cleaned_data.get('titulo') or "Relatório de Frota"
            relatorio = _gerar_pdf_unificado(request, tipo, titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, _('Relatório Gerado com Sucesso!'))
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioFrotaForm(initial={'titulo': f"Relatório de Frota - {timezone.now().strftime('%d/%m/%Y')}"})
    
    from viaturas.models import Viatura
    return render(request, 'relatorios/form_relatorio_frota.html', {
        'form': form,
        'viaturas_count': Viatura.objects.count(),
        'disponiveis_count': Viatura.objects.filter(status='DISPONIVEL').count(),
        'manutencao_count': Viatura.objects.filter(status='MANUTENCAO').count()
    })

@login_required
@require_module_permission('frota')
def gerar_relatorio_manutencoes(request):
    if request.method == 'POST':
        form = RelatorioFrotaForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data.get('tipo_relatorio', 'MANUTENCAO')
            titulo = form.cleaned_data.get('titulo') or "Relatório de Manutenções"
            relatorio = _gerar_pdf_unificado(request, tipo, titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, _('Relatório Gerado com Sucesso!'))
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioFrotaForm(initial={
            'titulo': f"Relatório de Manutenções - {timezone.now().strftime('%d/%m/%Y')}",
            'tipo_relatorio': 'MANUTENCAO'
        })
    
    from viaturas.models import Viatura
    return render(request, 'relatorios/form_relatorio_frota.html', {
        'form': form,
        'viaturas_count': Viatura.objects.count(),
        'disponiveis_count': Viatura.objects.filter(status='DISPONIVEL').count(),
        'manutencao_count': Viatura.objects.filter(status='MANUTENCAO').count()
    })

@login_required
@require_module_permission('frota')
def gerar_relatorio_individual_viatura(request, viatura_id):
    from viaturas.models import Viatura, Manutencao
    viatura = get_object_or_404(Viatura, pk=viatura_id)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = [Paragraph(f"FICHA TÉCNICA - {viatura.prefixo}", getSampleStyleSheet()['Heading1'])]
    doc.build(elements, onFirstPage=_draw_logo)
    return HttpResponse(buffer.getvalue(), content_type='application/pdf')
