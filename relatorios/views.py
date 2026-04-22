from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from reserva_baep.decorators import require_module_permission
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.http import HttpResponse, FileResponse
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
import os
import io
import datetime
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch, cm

from .models import Relatorio
from .forms import (
    RelatorioSituacaoAtualForm, RelatorioMateriaisForm, 
    RelatorioMovimentacoesForm, RelatorioEstoqueMovimentacoesForm,
    RelatorioPatrimonioForm, RelatorioFrotaForm
)
from estoque.models import MovimentacaoEstoque, Produto
from materiais.models import Material
from movimentacoes.models import Movimentacao, Retirada, Devolucao
from policiais.models import Policial
from patrimonio.models import ItemPatrimonial
from viaturas.models import Viatura, Manutencao, Oficina
from .utils import PDFReportGenerator
from .providers import (
    SituacaoAtualProvider, EstoqueCriticoProvider, FrotaGeralProvider,
    FrotaAbastecimentoProvider, FrotaManutencaoProvider,
    MateriaisProvider, MovimentacoesProvider, PatrimonioProvider
)

# Mapeamento de Provedores de Relatórios
REPORT_PROVIDERS = {
    'SITUACAO_ATUAL': SituacaoAtualProvider,
    'MATERIAIS': MateriaisProvider,
    'MATERIAIS_EM_USO': MateriaisProvider,
    'MATERIAIS_DISPONIVEIS': MateriaisProvider,
    'MOVIMENTACOES': MovimentacoesProvider,
    'MOVIMENTACOES_DIA': MovimentacoesProvider,
    'MOVIMENTACOES_PERIODO': MovimentacoesProvider,
    'MOVIMENTACOES_POLICIAL': MovimentacoesProvider,
    'MOVIMENTACOES_MATERIAL': MovimentacoesProvider,
    'ESTOQUE_CRITICO': EstoqueCriticoProvider,
    'FROTA_GERAL': FrotaGeralProvider,
    'FROTA_ABASTECIMENTO': FrotaAbastecimentoProvider,
    'FROTA_MANUTENCAO': FrotaManutencaoProvider,
    'PATRIMONIO_INVENTARIO': PatrimonioProvider,
}

def _gerar_pdf_unificado(request, tipo_relatorio, titulo, form_data=None):
    """Função auxiliar para gerar PDF usando o novo motor unificado"""
    import io
    from django.core.files.base import ContentFile
    
    buffer = io.BytesIO()
    generator = PDFReportGenerator(buffer, titulo, user=request.user)
    
    provider_class = REPORT_PROVIDERS.get(tipo_relatorio)
    if not provider_class:
        return None
        
    provider = provider_class(generator)
    elements = provider.get_elements()
    
    generator.generate(elements)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    # Determinar módulo automaticamente com base no tipo
    modulo = 'RESERVA'
    if 'ESTOQUE' in tipo_relatorio: modulo = 'ESTOQUE'
    elif 'PATRIMONIO' in tipo_relatorio: modulo = 'PATRIMONIO'
    elif 'FROTA' in tipo_relatorio: modulo = 'FROTA'
    
    # Criar registro no banco de dados
    relatorio = Relatorio.objects.create(
        titulo=titulo,
        tipo=tipo_relatorio,
        modulo=modulo,
        gerado_por=request.user,
        observacoes=request.POST.get('observacoes', '')
    )
    
    # Salvar o arquivo
    filename = f"relatorio_{tipo_relatorio}_{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
    relatorio.arquivo_pdf.save(filename, ContentFile(pdf_content))
    
    return relatorio


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

@login_required
def lista_relatorios(request):
    # Determina quais módulos o usuário pode acessar
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
    
    # Filtragem adicional
    tipo = request.GET.get('tipo')
    titulo = request.GET.get('titulo')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    usuario = request.GET.get('usuario')
    
    if tipo:
        relatorios = relatorios.filter(tipo=tipo)
    
    if titulo:
        relatorios = relatorios.filter(titulo__icontains=titulo)
    
    if data_inicio:
        try:
            data_inicio = datetime.datetime.strptime(data_inicio, '%Y-%m-%d').date()
            relatorios = relatorios.filter(data_geracao__date__gte=data_inicio)
        except ValueError:
            pass
    
    if data_fim:
        try:
            data_fim = datetime.datetime.strptime(data_fim, '%Y-%m-%d').date()
            relatorios = relatorios.filter(data_geracao__date__lte=data_fim)
        except ValueError:
            pass
    
    if usuario:
        relatorios = relatorios.filter(
            Q(gerado_por__username__icontains=usuario) |
            Q(gerado_por__first_name__icontains=usuario) |
            Q(gerado_por__last_name__icontains=usuario)
        )
    
    # EstatÃÂ­sticas para o cabeÃÂ§alho
    hoje = timezone.now().date()
    reports_today = relatorios.filter(data_geracao__date=hoje).count()
    
    # UsuÃÂ¡rio mais ativo (quem gerou mais relatÃÂ³rios)
    most_active_user_data = relatorios.values('gerado_por__username').annotate(total=Count('id')).order_by('-total').first()
    most_active_user = most_active_user_data['gerado_por__username'] if most_active_user_data else "N/A"
    
    last_report = relatorios.first()
    last_report_date = last_report.data_geracao if last_report else None

    # PaginaÃÂ§ÃÂ£o
    paginator = Paginator(relatorios, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'relatorios/lista_relatorios.html', {
        'relatorios': page_obj,
        'page_obj': page_obj,
        'total_relatorios': relatorios.count(),
        'reports_today': reports_today,
        'most_active_user': most_active_user,
        'last_report_date': last_report_date,
    })

@login_required
def detalhe_relatorio(request, relatorio_id):
    relatorio = get_object_or_404(Relatorio, pk=relatorio_id)
    
    # Verifica permissão específica para o módulo do relatório
    modulo_map = {
        'RESERVA': 'reserva_armas',
        'PATRIMONIO': 'patrimonio',
        'ESTOQUE': 'estoque'
    }
    required_group = modulo_map.get(relatorio.modulo)
    
    if not request.user.is_superuser:
        if not request.user.groups.filter(name=required_group).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied(f"Acesso negado: Este relatÃÂ³rio pertence ao mÃÂ³dulo {relatorio.get_modulo_display()}.")

    preview_data = None
    preview_type = None
    # Se não existe PDF, buscar dados para pré-visualização
    if not relatorio.arquivo_pdf:
        if relatorio.tipo == 'SITUACAO_ATUAL':
            total_materiais = Material.objects.count()
            materiais_disponiveis = Material.objects.filter(status='DISPONIVEL').count()
            materiais_em_uso = Material.objects.filter(status='EM_USO').count()
            materiais_manutencao = Material.objects.filter(status='MANUTENCAO').count()
            materiais_inativo = Material.objects.filter(status='INATIVO').count()
            preview_data = [
                ['Item', 'Quantidade'],
                ['Total de Materiais', total_materiais],
                ['Materiais Disponíveis', materiais_disponiveis],
                ['Materiais em Uso', materiais_em_uso],
                ['Materiais em Manutenção', materiais_manutencao],
                ['Materiais Inativos', materiais_inativo],
            ]
            preview_type = 'situacao_atual'
        elif relatorio.tipo in ['MATERIAIS', 'MATERIAIS_EM_USO', 'MATERIAIS_DISPONIVEIS']:
            materiais = Material.objects.all()
            if relatorio.tipo == 'MATERIAIS_EM_USO':
                materiais = materiais.filter(status='EM_USO')
            elif relatorio.tipo == 'MATERIAIS_DISPONIVEIS':
                materiais = materiais.filter(status='DISPONIVEL')
            preview_data = list(materiais.values_list('identificacao', 'nome', 'tipo', 'quantidade', 'quantidade_disponivel', 'status', 'estado'))
            preview_type = 'materiais'
        elif relatorio.tipo.startswith('MOVIMENTACOES'):
            from movimentacoes.models import Movimentacao
            movs = Movimentacao.objects.all().order_by('-data_hora')
            # Filtros possíveis: por policial, material, período, tipo
            if relatorio.periodo_inicio:
                movs = movs.filter(data_hora__gte=relatorio.periodo_inicio)
            if relatorio.periodo_fim:
                movs = movs.filter(data_hora__lte=relatorio.periodo_fim)
            preview_data = list(movs.values_list('data_hora', 'tipo', 'material__identificacao', 'policial__nome', 'quantidade'))
            preview_type = 'movimentacoes'
        elif relatorio.tipo == 'PATRIMONIO_INVENTARIO':
            from patrimonio.models import ItemPatrimonial
            itens = ItemPatrimonial.objects.select_related('bem', 'localizacao').all().order_by('numero_patrimonio')
            preview_data = [['PatrimÃÂ´nio', 'Bem', 'Status', 'LocalizaÃÂ§ÃÂ£o']]
            for item in itens[:10]: # Limita o preview
                preview_data.append([item.numero_patrimonio, item.bem.nome, item.get_status_display(), item.localizacao.nome if item.localizacao else '-'])
            preview_type = 'patrimonio'
    return render(request, 'relatorios/detalhe_relatorio.html', {
        'relatorio': relatorio,
        'preview_data': preview_data,
        'preview_type': preview_type,
    })

@login_required
def download_relatorio(request, relatorio_id):
    relatorio = get_object_or_404(Relatorio, pk=relatorio_id)
    
    # Verifica permissÃÂ£o baseada no mÃÂ³dulo
    modulo_map = {'RESERVA': 'reserva_armas', 'PATRIMONIO': 'patrimonio', 'ESTOQUE': 'estoque'}
    required_group = modulo_map.get(relatorio.modulo)
    
    if not request.user.is_superuser:
        if not request.user.groups.filter(name=required_group).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied(f"Sem permissÃÂ£o para baixar relatÃÂ³rios do mÃÂ³dulo {relatorio.get_modulo_display()}.")
    
    if not relatorio.arquivo_pdf or not os.path.exists(relatorio.arquivo_pdf.path):
        messages.error(request, _('Arquivo PDF nÃÂ£o encontrado.'))
        return redirect('relatorios:lista_relatorios')
    
    # Retornar o arquivo diretamente para download
    return FileResponse(
        open(relatorio.arquivo_pdf.path, 'rb'),
        content_type='application/pdf',
        as_attachment=True,
        filename=f"{relatorio.titulo.replace(' ', '_').lower()}_{relatorio.pk}.pdf"
    )

@login_required
def download_relatorio_arquivo(request, relatorio_id):
    relatorio = get_object_or_404(Relatorio, pk=relatorio_id)
    
    # Verifica permissÃÂ£o baseada no mÃÂ³dulo
    modulo_map = {'RESERVA': 'reserva_armas', 'PATRIMONIO': 'patrimonio', 'ESTOQUE': 'estoque'}
    required_group = modulo_map.get(relatorio.modulo)
    
    if not request.user.is_superuser:
        if not request.user.groups.filter(name=required_group).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied(f"Sem permissÃÂ£o para acessar relatÃÂ³rios do mÃÂ³dulo {relatorio.get_modulo_display()}.")
    
    if not relatorio.arquivo_pdf or not os.path.exists(relatorio.arquivo_pdf.path):
        messages.error(request, _('Arquivo PDF nÃÂ£o encontrado.'))
        return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    
    if request.method == 'POST':
        # Obter o nome do arquivo personalizado
        nome_arquivo = request.POST.get('nome_arquivo', f'relatorio_{relatorio.id}')
        formato = request.POST.get('formato', 'pdf')
        
        # Sanitizar o nome do arquivo para evitar caracteres invÃÂ¡lidos
        nome_arquivo = ''.join(c for c in nome_arquivo if c.isalnum() or c in '-_')
        
        # Se o nome estiver vazio apÃÂ³s a sanitizaÃÂ§ÃÂ£o, use um nome padrÃÂ£o
        if not nome_arquivo:
            nome_arquivo = f'relatorio_{relatorio.id}'
        
        # Adicionar a extensÃÂ£o correta
        filename = f'{nome_arquivo}.{formato}'
        
        # Retornar o arquivo para download
        return FileResponse(
            open(relatorio.arquivo_pdf.path, 'rb'),
            content_type='application/pdf',
            as_attachment=True,
            filename=filename
        )
    else:
        # Se nÃÂ£o for um POST, redirecionar para a pÃÂ¡gina de download
        return redirect('relatorios:download_relatorio', relatorio_id=relatorio.pk)

@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_situacao_atual(request):
    """Gera relatório de situação do arsenal usando o motor unificado"""
    if request.method == 'POST':
        form = RelatorioSituacaoAtualForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo')
            relatorio = _gerar_pdf_unificado(request, 'SITUACAO_ATUAL', titulo, form.cleaned_data)
            
            if relatorio:
                messages.success(request, _('Relatório de Situação Gerado com Sucesso!'))
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
            else:
                messages.error(request, _('Erro ao processar provedor de dados.'))
    else:
        # Busca estatísticas para o dashboard de pré-emissão
        stats = {
            'total': Material.objects.count(),
            'disponiveis': Material.objects.filter(status='DISPONIVEL').count(),
            'em_uso': Material.objects.filter(status='EM_USO').count(),
            'manutencao': Material.objects.filter(status='MANUTENCAO').count(),
        }
        form = RelatorioSituacaoAtualForm(initial={'titulo': f'Situação Geral do Arsenal - {timezone.now().strftime("%d/%m/%Y")}'})    
    
    return render(request, 'relatorios/form_relatorio_situacao.html', {'form': form, 'stats': stats})

@login_required
@require_module_permission('reserva_armas')
@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_materiais(request):
    """Gera relatório detalhado de materiais usando o motor unificado"""
    if request.method == 'POST':
        form = RelatorioMateriaisForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data.get('tipo_relatorio', 'MATERIAIS')
            titulo = form.cleaned_data.get('titulo') or "Relatório de Materiais"
            relatorio = _gerar_pdf_unificado(request, tipo, titulo, form.cleaned_data)
            
            if relatorio:
                messages.success(request, _('Relatório de Materiais Gerado com Sucesso!'))
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioMateriaisForm()
    return render(request, 'relatorios/form_relatorio_materiais.html', {'form': form})

@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_movimentacoes(request):
    """Gera relatório de movimentações de arsenal usando o motor unificado"""
    if request.method == 'POST':
        form = RelatorioMovimentacoesForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data.get('tipo_relatorio', 'MOVIMENTACOES')
            titulo = form.cleaned_data.get('titulo') or "Relatório de Movimentações"
            relatorio = _gerar_pdf_unificado(request, tipo, titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, 'Relatório de Movimentações Gerado com Sucesso!')
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioMovimentacoesForm()
    return render(request, 'relatorios/form_relatorio_movimentacoes.html', {'form': form})

def gerar_relatorio_estoque_movimentacoes(request):
    """Gera relatÃÂ³rio de movimentaÃÂ§ÃÂµes do estoque (MATERIAL DE CONSUMO Ã‚Â§2/Ã‚Â§3)"""
    if request.method == 'POST':
        form = RelatorioEstoqueMovimentacoesForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo')
            tipo_mov = form.cleaned_data.get('tipo_movimentacao')
            produto = form.cleaned_data.get('produto')
            data_inicio = form.cleaned_data.get('data_inicio')
            data_fim = form.cleaned_data.get('data_fim')
            observacoes = form.cleaned_data.get('observacoes', '')
            
            # Filtra as movimentaÃÂ§ÃÂµes
            movimentacoes = MovimentacaoEstoque.objects.all().order_by('-data_movimentacao', '-data_hora')
            
            if tipo_mov:
                movimentacoes = movimentacoes.filter(tipo_movimentacao=tipo_mov)
            if data_inicio:
                movimentacoes = movimentacoes.filter(data_movimentacao__gte=data_inicio)
            if data_fim:
                movimentacoes = movimentacoes.filter(data_movimentacao__lte=data_fim)
            if produto:
                movimentacoes = movimentacoes.filter(produto=produto)
            
            # Gera o PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1*cm, rightMargin=1*cm, topMargin=2*cm)
            elements = []
            
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=20)
            subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=12, spaceBefore=15, spaceAfter=10)
            normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=9)
            table_cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=7, leading=8)
            
            elements.append(Paragraph(titulo, title_style))
            elements.append(Paragraph(f"<b>Emissor:</b> {request.user.get_full_name() or request.user.username}", normal_style))
            elements.append(Paragraph(f"<b>Data de GeraÃÂ§ÃÂ£o:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
            
            periodo_str = f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}" if data_inicio and data_fim else "Todo o perÃÂ­odo"
            elements.append(Paragraph(f"<b>PerÃÂ­odo:</b> {periodo_str}", normal_style))
            elements.append(Spacer(1, 0.5*cm))

            # Resumo
            elements.append(Paragraph("Ã°Å¸â€œÅ  Resumo do PerÃÂ­odo", subtitle_style))
            total_movs = movimentacoes.count()
            entradas = movimentacoes.filter(tipo_movimentacao='ENTRADA').count()
            saidas = movimentacoes.filter(tipo_movimentacao='SAIDA').count()
            
            resumo_data = [
                ['Tipo', 'Qtd. OperaÃÂ§ÃÂµes'],
                ['Entradas', entradas],
                ['SaÃÂ­das', saidas],
                ['Total Geral', total_movs]
            ]
            res_table = Table(resumo_data, colWidths=[4*cm, 3*cm])
            res_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.navy),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
            ]))
            elements.append(res_table)
            elements.append(Spacer(1, 1*cm))

            # Detalhamento
            elements.append(Paragraph("Ã°Å¸â€œÂ  Detalhamento de MovimentaÃÂ§ÃÂµes", subtitle_style))
            mov_data = [['Data', 'Tipo', 'Material', 'Qtd', 'V. Unit', 'Militar (SaÃÂ­da) / Fornec. (Entrada)']]
            
            for m in movimentacoes:
                requisitante = str(m.militar_requisitante) if m.militar_requisitante else (str(m.fornecedor) if m.fornecedor else '-')
                mov_data.append([
                    m.data_movimentacao.strftime('%d/%m/%Y'),
                    m.get_subtipo_display(),
                    Paragraph(m.produto.nome, table_cell_style),
                    f"{'+' if m.tipo_movimentacao == 'ENTRADA' else '-'}{m.quantidade:.2f}",
                    f"R$ {m.valor_unitario:,.2f}",
                    Paragraph(requisitante, table_cell_style)
                ])
            
            # Ajuste de larguras para somar exatamente 18.5cm (A4 tem 21cm - 2cm margem = 19cm max)
            col_widths = [2.2*cm, 2.5*cm, 4.0*cm, 1.8*cm, 2.2*cm, 5.8*cm]
            table = Table(mov_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white])
            ]))
            elements.append(table)
            
            if observacoes:
                elements.append(Spacer(1, 1*cm))
                elements.append(Paragraph("<b>ObservaÃÂ§ÃÂµes:</b>", normal_style))
                elements.append(Paragraph(observacoes, normal_style))

            doc.build(elements, onFirstPage=_draw_logo, onLaterPages=_draw_logo)
            pdf = buffer.getvalue()
            buffer.close()
            
            relatorio = Relatorio.objects.create(
                titulo=titulo,
                tipo='MOVIMENTACOES_PERIODO',
                modulo='ESTOQUE',
                gerado_por=request.user,
                periodo_inicio=timezone.make_aware(datetime.datetime.combine(data_inicio, datetime.time.min)) if data_inicio else None,
                periodo_fim=timezone.make_aware(datetime.datetime.combine(data_fim, datetime.time.max)) if data_fim else None,
                observacoes=observacoes
            )
            relatorio.arquivo_pdf.save(f"movimentacao_estoque_{relatorio.pk}.pdf", io.BytesIO(pdf))
            
            messages.success(request, _('RelatÃÂ³rio gerado com sucesso!'))
            return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
            
    else:
        form = RelatorioEstoqueMovimentacoesForm()
    
    return render(request, 'relatorios/form_relatorio_estoque_movimentacoes.html', {'form': form})


@login_required
@require_module_permission('patrimonio')
@login_required
@require_module_permission('patrimonio')
def gerar_relatorio_patrimonio(request):
    """Gera relatório de patrimônio usando o motor unificado"""
    if request.method == 'POST':
        form = RelatorioPatrimonioForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo') or "Relatório de Patrimônio"
            relatorio = _gerar_pdf_unificado(request, 'PATRIMONIO_INVENTARIO', titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, 'Relatório de Patrimônio Gerado com Sucesso!')
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioPatrimonioForm()
    
    # Dados para o mini dashboard
    items_count = ItemPatrimonial.objects.count()
    localizacoes_count = ItemPatrimonial.objects.values('localizacao').distinct().count()
    
    return render(request, 'relatorios/form_relatorio_patrimonio.html', {
        'form': form,
        'items_count': items_count,
        'localizacoes_count': localizacoes_count
    })

@login_required
@require_module_permission('patrimonio')
def gerar_relatorio_viaturas(request):
    """Gera relatório de frota usando o motor unificado"""
    if request.method == 'POST':
        form = RelatorioFrotaForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data.get('tipo_relatorio', 'FROTA_GERAL')
            titulo = form.cleaned_data.get('titulo')
            
            relatorio = _gerar_pdf_unificado(request, tipo, titulo, form.cleaned_data)
            
            if relatorio:
                messages.success(request, _('Relatório de Frota gerado com sucesso!'))
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
            else:
                messages.error(request, _('Erro ao gerar relatório. Provedor não encontrado.'))
    else:
        form = RelatorioFrotaForm(initial={'titulo': f"Relatório de Frota - {timezone.now().strftime('%d/%m/%Y')}"})
    
    return render(request, 'relatorios/form_relatorio_frota.html', {'form': form})

@login_required
@require_module_permission('frota')
def gerar_relatorio_manutencoes(request):
    """Gera relatório de manutenções no período"""
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    qs = Manutencao.objects.all().order_by('-data_inicio')
    if data_inicio: qs = qs.filter(data_inicio__gte=data_inicio)
    if data_fim: qs = qs.filter(data_inicio__lte=data_fim)
        
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=20)
    style_header = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', alignment=1, textColor=colors.whitesmoke)
    style_cell = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, alignment=1)
    
    elements.append(Paragraph("RELAÇÃO DE MANUTENÇÕES", style_title))
    if data_inicio or data_fim:
        periodo = f"Período: {data_inicio or 'Início'} até {data_fim or 'Hoje'}"
        elements.append(Paragraph(periodo, styles['Normal']))
    elements.append(Spacer(1, 12))
    
    headers = [
        Paragraph('Viatura', style_header),
        Paragraph('Oficina', style_header),
        Paragraph('Início', style_header),
        Paragraph('Conclusão', style_header),
        Paragraph('Valor Total', style_header)
    ]
    data = [headers]
    for m in qs:
        oficina = m.oficina_fk.nome if m.oficina_fk else (m.oficina or '-')
        data.append([
            Paragraph(m.viatura.prefixo, style_cell),
            Paragraph(oficina, style_cell),
            Paragraph(m.data_inicio.strftime('%d/%m/%Y'), style_cell),
            Paragraph(m.data_conclusao.strftime('%d/%m/%Y') if m.data_conclusao else 'Aberta', style_cell),
            Paragraph(f"R$ {m.custo_total}", style_cell)
        ])
    
    table = Table(data, colWidths=[2.5*cm, 5.5*cm, 3.0*cm, 3.5*cm, 3.5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(table)
    doc.build(elements, onFirstPage=_draw_logo, onLaterPages=_draw_logo)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="relatorio_manutencoes.pdf"'
    response.write(pdf)
    return response

@login_required
@require_module_permission('frota')
def gerar_relatorio_individual_viatura(request, viatura_id):
    """Gera ficha detalhada de uma viatura específica"""
    from viaturas.models import Viatura, Manutencao
    viatura = get_object_or_404(Viatura, pk=viatura_id)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=20)
    style_subtitle = ParagraphStyle('SubtitleStyle', parent=styles['Heading2'], fontSize=12, spaceBefore=12, spaceAfter=6)
    style_header = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', alignment=1, textColor=colors.black)
    style_cell = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, alignment=1)
    
    elements.append(Paragraph(f"FICHA TÉCNICA E HISTÓRICO - {viatura.prefixo}", style_title))
    
    # Dados Técnicos
    data = [
        [Paragraph('Prefixo:', style_header), Paragraph(viatura.prefixo, style_cell), Paragraph('Placa:', style_header), Paragraph(viatura.placa or '-', style_cell)],
        [Paragraph('Modelo:', style_header), Paragraph(viatura.modelo.nome, style_cell), Paragraph('Marca:', style_header), Paragraph(viatura.modelo.marca.nome, style_cell)],
        [Paragraph('Chassi:', style_header), Paragraph(viatura.chassi or '-', style_cell), Paragraph('RENAVAM:', style_header), Paragraph(viatura.renavam or '-', style_cell)],
        [Paragraph('Status:', style_header), Paragraph(viatura.get_status_display(), style_cell), Paragraph('Odômetro:', style_header), Paragraph(f"{viatura.odometro_atual} km", style_cell)]
    ]
    t = Table(data, colWidths=[3*cm, 5.5*cm, 3*cm, 5.5*cm])
    t.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t)
    
    # Manutenções
    elements.append(Paragraph("Últimas Manutenções", style_subtitle))
    manutencoes = Manutencao.objects.filter(viatura=viatura).order_by('-data_inicio')[:15]
    if manutencoes:
        data_m = [[Paragraph('Data', style_header), Paragraph('Oficina', style_header), Paragraph('Descrição', style_header), Paragraph('Valor', style_header)]]
        for m in manutencoes:
            ofic = m.oficina_fk.nome if m.oficina_fk else (m.oficina or '-')
            data_m.append([
                Paragraph(m.data_inicio.strftime('%d/%m/%Y'), style_cell),
                Paragraph(ofic, style_cell),
                Paragraph(m.descricao or '-', style_cell),
                Paragraph(f"R$ {m.custo_total}", style_cell)
            ])
        tm = Table(data_m, colWidths=[2.5*cm, 4.5*cm, 7.5*cm, 2.5*cm])
        tm.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(tm)
    else:
        elements.append(Paragraph("Nenhuma manutenção registrada.", styles['Normal']))
    
    doc.build(elements, onFirstPage=_draw_logo, onLaterPages=_draw_logo)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="ficha_{viatura.prefixo}.pdf"'
    response.write(pdf)
    return response


