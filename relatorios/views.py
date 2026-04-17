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
    RelatorioPatrimonioForm
)
from estoque.models import MovimentacaoEstoque, Produto
from materiais.models import Material
from movimentacoes.models import Movimentacao, Retirada, Devolucao
from policiais.models import Policial
from patrimonio.models import ItemPatrimonial
from viaturas.models import Viatura, Manutencao, Oficina


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
    # Determina quais mÃÂ³dulos o usuÃÂ¡rio pode acessar
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
        raise PermissionDenied("VocÃÂª nÃÂ£o tem acesso a nenhum mÃÂ³dulo de relatÃÂ³rios.")

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
    
    # Verifica permissÃÂ£o especÃÂ­fica para o mÃÂ³dulo do relatÃÂ³rio
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
    # Se nÃÂ£o existe PDF, buscar dados para prÃÂ©-visualizaÃÂ§ÃÂ£o
    if not relatorio.arquivo_pdf:
        if relatorio.tipo == 'SITUACAO_ATUAL':
            from materiais.models import Material
            total_materiais = Material.objects.count()
            materiais_disponiveis = Material.objects.filter(status='DISPONIVEL').count()
            materiais_em_uso = Material.objects.filter(status='EM_USO').count()
            materiais_manutencao = Material.objects.filter(status='MANUTENCAO').count()
            materiais_inativo = Material.objects.filter(status='INATIVO').count()
            preview_data = [
                ['Item', 'Quantidade'],
                ['Total de Materiais', total_materiais],
                ['Materiais DisponÃÂ­veis', materiais_disponiveis],
                ['Materiais em Uso', materiais_em_uso],
                ['Materiais em ManutenÃÂ§ÃÂ£o', materiais_manutencao],
                ['Materiais Inativos', materiais_inativo],
            ]
            preview_type = 'situacao_atual'
        elif relatorio.tipo in ['MATERIAIS', 'MATERIAIS_EM_USO', 'MATERIAIS_DISPONIVEIS']:
            from materiais.models import Material
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
            # Filtros possÃÂ­veis: por policial, material, perÃÂ­odo, tipo
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
    if request.method == 'POST':
        form = RelatorioSituacaoAtualForm(request.POST)
        if form.is_valid():
            # Gera o relatÃÂ³rio PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            
            # Estilos
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            subtitle_style = styles['Heading2']
            normal_style = styles['Normal']
            
            # TÃÂ­tulo
            titulo = form.cleaned_data.get('titulo', 'RelatÃÂ³rio de SituaÃÂ§ÃÂ£o Atual')
            elements.append(Paragraph(titulo, title_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Data e hora
            data_hora = timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')
            elements.append(Paragraph(f'Gerado em: {data_hora}', normal_style))
            elements.append(Paragraph(f'Gerado por: {request.user.get_full_name() or request.user.username}', normal_style))
            elements.append(Spacer(1, 1*cm))
            
            # Resumo geral
            elements.append(Paragraph('Resumo Geral', subtitle_style))
            
            total_materiais = Material.objects.count()
            materiais_disponiveis = Material.objects.filter(status='DISPONIVEL').count()
            materiais_em_uso = Material.objects.filter(status='EM_USO').count()
            materiais_manutencao = Material.objects.filter(status='MANUTENCAO').count()
            materiais_inativo = Material.objects.filter(status='INATIVO').count()
            
            data = [
                ['Item', 'Quantidade'],
                ['Total de Materiais', total_materiais],
                ['Materiais DisponÃÂ­veis', materiais_disponiveis],
                ['Materiais em Uso', materiais_em_uso],
                ['Materiais em ManutenÃÂ§ÃÂ£o', materiais_manutencao],
                ['Materiais Inativos', materiais_inativo],
            ]
            
            table = Table(data, colWidths=[10*cm, 5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (1, 0), 12),
                ('BACKGROUND', (0, 1), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 1*cm))
            
            # Detalhamento por tipo de material
            elements.append(Paragraph('Detalhamento por Tipo de Material', subtitle_style))
            
            tipos_materiais = Material.objects.values('tipo').annotate(
                total=Count('id'),
                disponiveis=Count('id', filter=Q(status='DISPONIVEL')),
                em_uso=Count('id', filter=Q(status='EM_USO')),
                manutencao=Count('id', filter=Q(status='MANUTENCAO')),
                inativos=Count('id', filter=Q(status='INATIVO'))
            )
            
            # Mapeamento de cÃÂ³digos para nomes de tipos
            tipo_map = dict(Material.TIPO_CHOICES)
            
            data = [
                ['Tipo de Material', 'Total', 'DisponÃÂ­veis', 'Em Uso', 'ManutenÃÂ§ÃÂ£o', 'Inativos'],
            ]
            
            for tipo in tipos_materiais:
                tipo_nome = tipo_map.get(tipo['tipo'], tipo['tipo'])
                data.append([
                    tipo_nome,
                    tipo['total'],
                    tipo['disponiveis'],
                    tipo['em_uso'],
                    tipo['manutencao'],
                    tipo['inativos']
                ])
            
            table = Table(data, colWidths=[5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ]))
            elements.append(table)
            
            # ObservaÃÂ§ÃÂµes
            if form.cleaned_data.get('observacoes'):
                elements.append(Spacer(1, 1*cm))
                elements.append(Paragraph('ObservaÃÂ§ÃÂµes:', subtitle_style))
                elements.append(Paragraph(form.cleaned_data.get('observacoes'), normal_style))
            
            # Gera o PDF
            def _on_page(canvas_, doc_):
                canvas_.saveState()
                _draw_logo(canvas_, doc_)
                canvas_.restoreState()

            doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
            pdf = buffer.getvalue()
            buffer.close()
            
            # Salva o relatÃÂ³rio no banco de dados
            relatorio = Relatorio(
                titulo=titulo,
                tipo='SITUACAO_ATUAL',
                modulo='RESERVA',
                gerado_por=request.user,
                observacoes=form.cleaned_data.get('observacoes', ''),
                periodo_inicio=timezone.now(),
                periodo_fim=timezone.now()
            )
            
            # Salva o arquivo PDF temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf)
                temp_path = temp_file.name
            
            # Associa o arquivo ao relatÃÂ³rio
            with open(temp_path, 'rb') as f:
                relatorio.arquivo_pdf.save(f'relatorio_situacao_{timezone.now().strftime("%Y%m%d%H%M%S")}.pdf', 
                                          io.BytesIO(f.read()))
            
            # Remove o arquivo temporÃÂ¡rio
            os.unlink(temp_path)
            
            messages.success(request, _('RelatÃÂ³rio gerado com sucesso!'))
            return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioSituacaoAtualForm(initial={'titulo': f'RelatÃÂ³rio de SituaÃÂ§ÃÂ£o Atual - {timezone.now().strftime("%d/%m/%Y")}'})    
    
    return render(request, 'relatorios/form_relatorio_situacao.html', {'form': form})

@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_materiais(request):
    if request.method == 'POST':
        form = RelatorioMateriaisForm(request.POST)
        if form.is_valid():
            # ObtÃÂ©m os dados do formulÃÂ¡rio
            titulo = form.cleaned_data.get('titulo')
            status = form.cleaned_data.get('status')
            tipo = form.cleaned_data.get('tipo')
            observacoes = form.cleaned_data.get('observacoes', '')
            
            # Filtra os materiais
            materiais = Material.objects.all()
            
            if status:
                materiais = materiais.filter(status=status)
                
            if tipo:
                materiais = materiais.filter(tipo=tipo)
            
            # Gera o relatÃÂ³rio PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1*cm, rightMargin=1*cm)
            elements = []
            
            # Estilos modernos
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=20,
                textColor=colors.HexColor('#2c3e50'),
                alignment=1  # Centralizado
            )
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.HexColor('#34495e'),
                spaceBefore=20
            )
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                textColor=colors.HexColor('#2c3e50')
            )
            header_style = ParagraphStyle(
                'HeaderStyle',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.white,
                alignment=1
            )
            
            # CabeÃÂ§alho do relatÃÂ³rio
            elements.append(Paragraph(titulo, title_style))
            elements.append(Spacer(1, 0.3*cm))
            
            # InformaÃÂ§ÃÂµes de geraÃÂ§ÃÂ£o
            data_hora = timezone.localtime(timezone.now()).strftime('%d/%m/%Y ÃÂ s %H:%M')
            elements.append(Paragraph(f'<b>Gerado em:</b> {data_hora}', normal_style))
            elements.append(Paragraph(f'<b>Gerado por:</b> {request.user.get_full_name() or request.user.username}', normal_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Filtros aplicados
            filtros = []
            if status:
                status_display = dict(Material.STATUS_CHOICES).get(status, status)
                filtros.append(f'Status: {status_display}')
            if tipo:
                tipo_display = dict(Material.TIPO_CHOICES).get(tipo, tipo)
                filtros.append(f'Tipo: {tipo_display}')
            
            if filtros:
                elements.append(Paragraph('<b>Filtros aplicados:</b> ' + ', '.join(filtros), normal_style))
                elements.append(Spacer(1, 0.3*cm))
            
            # Resumo executivo
            elements.append(Paragraph('Ã°Å¸â€œÅ  RESUMO EXECUTIVO', subtitle_style))
            
            total_materiais = materiais.count()
            materiais_disponiveis = materiais.filter(status='DISPONIVEL').count()
            materiais_em_uso = materiais.filter(status='EM_USO').count()
            materiais_manutencao = materiais.filter(status='MANUTENCAO').count()
            materiais_apreendidos = materiais.filter(status='APREENDIDO').count()
            materiais_baixados = materiais.filter(status='BAIXADO').count()
            
            total_quantidade = materiais.aggregate(Sum('quantidade'))['quantidade__sum'] or 0
            total_disponivel = materiais.aggregate(Sum('quantidade_disponivel'))['quantidade_disponivel__sum'] or 0
            total_em_uso = materiais.aggregate(Sum('quantidade_em_uso'))['quantidade_em_uso__sum'] or 0
            
            # Tabela de resumo
            resumo_data = [
                ['', 'Itens', 'Quantidade Total', 'DisponÃÂ­vel', 'Em Uso'],
                ['Ã°Å¸â€œÂ¦ Total Geral', total_materiais, f"{total_quantidade:.2f}", f"{total_disponivel:.2f}", f"{total_em_uso:.2f}"],
                ['Ã¢Å“â€¦ DisponÃÂ­veis', materiais_disponiveis, '', '', ''],
                ['Ã°Å¸â€ â€ž Em Uso', materiais_em_uso, '', '', ''],
                ['Ã°Å¸â€ Â§ ManutenÃÂ§ÃÂ£o', materiais_manutencao, '', '', ''],
                ['Ã°Å¸Å¡Â« Apreendidos', materiais_apreendidos, '', '', ''],
                ['Ã°Å¸â€œâ€° Baixados', materiais_baixados, '', '', '']
            ]
            
            resumo_table = Table(resumo_data, colWidths=[4*cm, 2*cm, 3*cm, 3*cm, 3*cm])
            resumo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ecf0f1'), colors.white]),
            ]))
            elements.append(resumo_table)
            elements.append(Spacer(1, 1*cm))
            
            # Materiais em Uso (com detalhes dos policiais responsÃÂ¡veis)
            materiais_em_uso_list = materiais.filter(status='EM_USO')
            if materiais_em_uso_list.exists():
                elements.append(Paragraph('Ã°Å¸â€˜Â¥ MATERIAIS EM USO', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                # Busca informaÃÂ§ÃÂµes dos policiais responsÃÂ¡veis
                materiais_com_policiais = []
                for material in materiais_em_uso_list:
                    # Busca a última retirada nÃÂ£o devolvida
                    ultima_retirada = Movimentacao.objects.filter(
                        material=material,
                        tipo='RETIRADA'
                    ).exclude(
                        id__in=Movimentacao.objects.filter(
                            material=material,
                            tipo='DEVOLUCAO'
                        ).values_list('id', flat=True)
                    ).order_by('-data_hora').first()
                    
                    policial_info = "NÃÂ£o identificado"
                    data_retirada = "N/A"
                    finalidade = "N/A"
                    
                    if ultima_retirada:
                        policial_info = f"{ultima_retirada.policial.nome} (RE: {ultima_retirada.policial.re})"
                        data_retirada = ultima_retirada.data_hora.strftime('%d/%m/%Y %H:%M')
                        try:
                            finalidade = ultima_retirada.retirada.finalidade
                        except:
                            finalidade = "N/A"
                    
                    materiais_com_policiais.append({
                        'material': material,
                        'policial': policial_info,
                        'data_retirada': data_retirada,
                        'finalidade': finalidade
                    })
                
                # Tabela de materiais em uso
                uso_data = [
                    ['IdentificaÃÂ§ÃÂ£o', 'Tipo', 'Qtd. Em Uso', 'Policial ResponsÃÂ¡vel', 'Data Retirada', 'Finalidade']
                ]
                
                for item in materiais_com_policiais:
                    material = item['material']
                    uso_data.append([
                        material.identificacao,
                        material.get_tipo_display(),
                        f"{material.quantidade_em_uso:.2f}",
                        item['policial'],
                        item['data_retirada'],
                        item['finalidade']
                    ])
                
                uso_table = Table(uso_data, colWidths=[4*cm, 2*cm, 1.5*cm, 4*cm, 2.5*cm, 3*cm])
                uso_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fdf2e9')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e67e22')),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (3, -1), 'CENTER'),
                    ('ALIGN', (4, 1), (4, -1), 'LEFT'),
                    ('ALIGN', (5, 1), (5, -1), 'CENTER'),
                    ('ALIGN', (6, 1), (6, -1), 'LEFT'),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fdf2e9'), colors.white]),
                ]))
                elements.append(uso_table)
                elements.append(Spacer(1, 1*cm))
            
            # Materiais em Estoque (DisponÃÂ­veis)
            materiais_disponiveis_list = materiais.filter(status='DISPONIVEL')
            if materiais_disponiveis_list.exists():
                elements.append(Paragraph('Ã°Å¸â€œÂ¦ MATERIAIS EM ESTOQUE', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                # Tabela de materiais disponÃÂ­veis
                estoque_data = [
                    ['IdentificaÃÂ§ÃÂ£o', 'Tipo', 'Qtd. Total', 'Qtd. DisponÃÂ­vel', 'Estado']
                ]
                
                for material in materiais_disponiveis_list:
                    estoque_data.append([
                        material.identificacao,
                        material.get_tipo_display(),
                        f"{material.quantidade:.2f}",
                        f"{material.quantidade_disponivel:.2f}",
                        material.get_estado_display()
                    ])
                
                estoque_table = Table(estoque_data, colWidths=[5*cm, 2*cm, 2*cm, 2*cm, 3*cm])
                estoque_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#e8f5e8')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#27ae60')),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#e8f5e8'), colors.white]),
                ]))
                elements.append(estoque_table)
                elements.append(Spacer(1, 1*cm))
            
            # Materiais em ManutenÃÂ§ÃÂ£o
            materiais_manutencao_list = materiais.filter(status='MANUTENCAO')
            if materiais_manutencao_list.exists():
                elements.append(Paragraph('Ã°Å¸â€Â§ MATERIAIS EM MANUTENÃâ€¡ÃÆ’O', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                manutencao_data = [
                    ['IdentificaÃÂ§ÃÂ£o', 'Tipo', 'Estado', 'ObservaÃÂ§ÃÂµes']
                ]
                
                for material in materiais_manutencao_list:
                    manutencao_data.append([
                        material.identificacao,
                        material.get_tipo_display(),
                        material.get_estado_display(),
                        material.observacoes[:50] + '...' if material.observacoes and len(material.observacoes) > 50 else material.observacoes or '-'
                    ])
                
                manutencao_table = Table(manutencao_data, colWidths=[5*cm, 2*cm, 2*cm, 7*cm])
                manutencao_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f39c12')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef9e7')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#f39c12')),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (3, -1), 'CENTER'),
                    ('ALIGN', (4, 1), (4, -1), 'LEFT'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fef9e7'), colors.white]),
                ]))
                elements.append(manutencao_table)
                elements.append(Spacer(1, 1*cm))
            
            # Materiais Apreendidos
            materiais_apreendidos_list = materiais.filter(status='APREENDIDO')
            if materiais_apreendidos_list.exists():
                elements.append(Paragraph('Ã°Å¸Å¡Â« MATERIAIS APREENDIDOS', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                apreendidos_data = [
                    ['IdentificaÃÂ§ÃÂ£o', 'Tipo', 'Estado', 'ObservaÃÂ§ÃÂµes']
                ]
                
                for material in materiais_apreendidos_list:
                    apreendidos_data.append([
                        material.identificacao,
                        material.get_tipo_display(),
                        material.get_estado_display(),
                        material.observacoes[:50] + '...' if material.observacoes and len(material.observacoes) > 50 else material.observacoes or '-'
                    ])
                
                apreendidos_table = Table(apreendidos_data, colWidths=[5*cm, 2*cm, 2*cm, 7*cm])
                apreendidos_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fdf2f2')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e74c3c')),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (3, -1), 'CENTER'),
                    ('ALIGN', (4, 1), (4, -1), 'LEFT'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fdf2f2'), colors.white]),
                ]))
                elements.append(apreendidos_table)
                elements.append(Spacer(1, 1*cm))
            
            # Materiais Baixados
            materiais_baixados_list = materiais.filter(status='BAIXADO')
            if materiais_baixados_list.exists():
                elements.append(Paragraph('Ã°Å¸â€œâ€° MATERIAIS BAIXADOS', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                baixados_data = [
                    ['IdentificaÃÂ§ÃÂ£o', 'Tipo', 'Estado', 'ObservaÃÂ§ÃÂµes']
                ]
                
                for material in materiais_baixados_list:
                    baixados_data.append([
                        material.identificacao,
                        material.get_tipo_display(),
                        material.get_estado_display(),
                        material.observacoes[:50] + '...' if material.observacoes and len(material.observacoes) > 50 else material.observacoes or '-'
                    ])
                
                baixados_table = Table(baixados_data, colWidths=[5*cm, 2*cm, 2*cm, 7*cm])
                baixados_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#95a5a6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#95a5a6')),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (3, -1), 'CENTER'),
                    ('ALIGN', (4, 1), (4, -1), 'LEFT'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8f9fa'), colors.white]),
                ]))
                elements.append(baixados_table)
                elements.append(Spacer(1, 1*cm))
            
            # ObservaÃÂ§ÃÂµes
            if observacoes:
                elements.append(Paragraph('Ã°Å¸â€œÂ OBSERVAÃâ€¡Ãâ€¢ES', subtitle_style))
                elements.append(Paragraph(observacoes, normal_style))
                elements.append(Spacer(1, 0.5*cm))
            
            # RodapÃÂ©
            elements.append(Paragraph('--- RelatÃÂ³rio gerado automaticamente pelo SIS LOGÃÂSTICA 2Ã‚ºBAEP ---', normal_style))
            
            # Gera o PDF
            def _on_page(canvas_, doc_):
                canvas_.saveState()
                _draw_logo(canvas_, doc_)
                canvas_.restoreState()

            doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
            pdf = buffer.getvalue()
            buffer.close()
            
            # Determina o tipo de relatÃÂ³rio com base nos filtros
            tipo_relatorio = 'MATERIAIS'
            if status == 'EM_USO':
                tipo_relatorio = 'MATERIAIS_EM_USO'
            elif status == 'DISPONIVEL':
                tipo_relatorio = 'MATERIAIS_DISPONIVEIS'
            
            # Salva o relatÃÂ³rio no banco de dados
            relatorio = Relatorio(
                titulo=titulo,
                tipo=tipo_relatorio,
                modulo='RESERVA',
                gerado_por=request.user,
                observacoes=observacoes,
                periodo_inicio=timezone.now(),
                periodo_fim=timezone.now()
            )
            
            # Salva o arquivo PDF temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf)
                temp_path = temp_file.name
            
            # Associa o arquivo ao relatÃÂ³rio
            with open(temp_path, 'rb') as f:
                relatorio.arquivo_pdf.save(f'relatorio_materiais_{timezone.localtime(timezone.now()).strftime("%Y%m%d%H%M%S")}.pdf', 
                                          io.BytesIO(f.read()))
            
            # Remove o arquivo temporÃÂ¡rio
            os.unlink(temp_path)
            
            messages.success(request, _('RelatÃÂ³rio gerado com sucesso!'))
            return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioMateriaisForm(initial={'titulo': f'RelatÃÂ³rio de Materiais - {timezone.localtime(timezone.now()).strftime("%d/%m/%Y")}'})    
    
    return render(request, 'relatorios/form_relatorio_materiais.html', {'form': form})

@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_movimentacoes(request):
    if request.method == 'POST':
        form = RelatorioMovimentacoesForm(request.POST)
        if form.is_valid():
            # ObtÃÂ©m os dados do formulÃÂ¡rio
            titulo = form.cleaned_data.get('titulo')
            tipo_movimentacao = form.cleaned_data.get('tipo_movimentacao')
            data_inicio = form.cleaned_data.get('data_inicio')
            data_fim = form.cleaned_data.get('data_fim')
            policial = form.cleaned_data.get('policial')
            material = form.cleaned_data.get('material')
            observacoes = form.cleaned_data.get('observacoes', '')
            
            # Filtra as movimentaÃÂ§ÃÂµes
            movimentacoes = Movimentacao.objects.all().order_by('-data_hora')
            
            if tipo_movimentacao:
                movimentacoes = movimentacoes.filter(tipo=tipo_movimentacao)
                
            if data_inicio:
                movimentacoes = movimentacoes.filter(data_hora__date__gte=data_inicio)
                
            if data_fim:
                movimentacoes = movimentacoes.filter(data_hora__date__lte=data_fim)
                
            if policial:
                movimentacoes = movimentacoes.filter(policial=policial)
                
            if material:
                movimentacoes = movimentacoes.filter(material=material)
            
            # Gera o relatÃÂ³rio PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1*cm, rightMargin=1*cm)
            elements = []
            
            # Estilos modernos
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=20,
                textColor=colors.HexColor('#2c3e50'),
                alignment=1  # Centralizado
            )
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.HexColor('#34495e'),
                spaceBefore=20
            )
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                textColor=colors.HexColor('#2c3e50')
            )
            
            # CabeÃÂ§alho do relatÃÂ³rio
            elements.append(Paragraph(titulo, title_style))
            elements.append(Spacer(1, 0.3*cm))
            
            # InformaÃÂ§ÃÂµes de geraÃÂ§ÃÂ£o
            data_hora = timezone.now().strftime('%d/%m/%Y ÃÂ s %H:%M')
            elements.append(Paragraph(f'<b>Gerado em:</b> {data_hora}', normal_style))
            elements.append(Paragraph(f'<b>Gerado por:</b> {request.user.get_full_name() or request.user.username}', normal_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Filtros aplicados
            filtros = []
            if tipo_movimentacao:
                tipo_display = dict(Movimentacao.TIPO_CHOICES).get(tipo_movimentacao, tipo_movimentacao)
                filtros.append(f'Tipo: {tipo_display}')
            if data_inicio:
                filtros.append(f'Data InÃÂ­cio: {data_inicio.strftime("%d/%m/%Y")}')
            if data_fim:
                filtros.append(f'Data Fim: {data_fim.strftime("%d/%m/%Y")}')
            if policial:
                filtros.append(f'Policial: {policial.nome} (RE: {policial.re})')
            if material:
                filtros.append(f'Material: {material.identificacao}')
            
            if filtros:
                elements.append(Paragraph('<b>Filtros aplicados:</b> ' + ', '.join(filtros), normal_style))
                elements.append(Spacer(1, 0.3*cm))
            
            # PerÃÂ­odo do relatÃÂ³rio
            if data_inicio and data_fim:
                elements.append(Paragraph(f'<b>PerÃÂ­odo:</b> {data_inicio.strftime("%d/%m/%Y")} a {data_fim.strftime("%d/%m/%Y")}', normal_style))
                elements.append(Spacer(1, 0.3*cm))
            
            # Resumo executivo
            elements.append(Paragraph('Ã°Å¸â€œÅ  RESUMO EXECUTIVO', subtitle_style))
            
            total_movimentacoes = movimentacoes.count()
            total_retiradas = movimentacoes.filter(tipo='RETIRADA').count()
            total_devolucoes = movimentacoes.filter(tipo='DEVOLUCAO').count()
            
            # Calcula totais de quantidade
            total_quantidade_retirada = movimentacoes.filter(tipo='RETIRADA').aggregate(Sum('quantidade'))['quantidade__sum'] or 0
            total_quantidade_devolvida = movimentacoes.filter(tipo='DEVOLUCAO').aggregate(Sum('quantidade'))['quantidade__sum'] or 0
            
            # Tabela de resumo
            resumo_data = [
                ['', 'MovimentaÃÂ§ÃÂµes', 'Quantidade'],
                ['Ã°Å¸â€œÂ¤ Retiradas', total_retiradas, total_quantidade_retirada],
                ['Ã°Å¸â€œÂ¥ DevoluÃÂ§ÃÂµes', total_devolucoes, total_quantidade_devolvida],
                ['Ã°Å¸â€œÅ  Total Geral', total_movimentacoes, total_quantidade_retirada + total_quantidade_devolvida]
            ]
            
            resumo_table = Table(resumo_data, colWidths=[6*cm, 4*cm, 4*cm])
            resumo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ecf0f1'), colors.white]),
            ]))
            elements.append(resumo_table)
            elements.append(Spacer(1, 1*cm))
            
            # Detalhamento por tipo
            if total_retiradas > 0:
                elements.append(Paragraph('Ã°Å¸â€œÂ¤ RETIRADAS', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                retiradas = movimentacoes.filter(tipo='RETIRADA')
                retiradas_data = [
                    ['Data/Hora', 'Material', 'Policial', 'Qtd.', 'Finalidade', 'Local', 'Registrado Por']
                ]
                
                for mov in retiradas:
                    try:
                        finalidade = mov.retirada.finalidade
                        local = mov.retirada.local_uso or '-'
                    except:
                        finalidade = 'N/A'
                        local = 'N/A'
                    
                    retiradas_data.append([
                        mov.data_hora.strftime('%d/%m/%Y %H:%M'),
                        mov.material.identificacao,
                        f'{mov.policial.nome} (RE: {mov.policial.re})',
                        f"{mov.quantidade:.2f}",
                        finalidade,
                        local,
                        mov.registrado_por.get_full_name() or mov.registrado_por.username
                    ])
                
                retiradas_table = Table(retiradas_data, colWidths=[2.5*cm, 3.5*cm, 3*cm, 1*cm, 2.5*cm, 2*cm, 2.5*cm])
                retiradas_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fdf2e9')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e67e22')),
                    ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                    ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                    ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                    ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                    ('ALIGN', (4, 1), (4, -1), 'LEFT'),
                    ('ALIGN', (5, 1), (5, -1), 'LEFT'),
                    ('ALIGN', (6, 1), (6, -1), 'LEFT'),
                    ('FONTSIZE', (0, 1), (-1, -1), 6),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fdf2e9'), colors.white]),
                ]))
                elements.append(retiradas_table)
                elements.append(Spacer(1, 1*cm))
            
            if total_devolucoes > 0:
                elements.append(Paragraph('Ã°Å¸â€œÂ¥ DEVOLUÃâ€¡Ãâ€¢ES', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                devolucoes = movimentacoes.filter(tipo='DEVOLUCAO')
                devolucoes_data = [
                    ['Data/Hora', 'Material', 'Policial', 'Qtd.', 'Estado DevoluÃÂ§ÃÂ£o', 'Retirada Ref.', 'Registrado Por']
                ]
                
                for mov in devolucoes:
                    try:
                        estado_devolucao = mov.devolucao.estado_devolucao
                        retirada_ref = f"#{mov.devolucao.retirada_referencia.id}"
                    except:
                        estado_devolucao = 'N/A'
                        retirada_ref = 'N/A'
                    
                    devolucoes_data.append([
                        mov.data_hora.strftime('%d/%m/%Y %H:%M'),
                        mov.material.identificacao,
                        f'{mov.policial.nome} (RE: {mov.policial.re})',
                        f"{mov.quantidade:.2f}",
                        estado_devolucao,
                        retirada_ref,
                        mov.registrado_por.get_full_name() or mov.registrado_por.username
                    ])
                
                devolucoes_table = Table(devolucoes_data, colWidths=[2.5*cm, 3.5*cm, 3*cm, 1*cm, 2.5*cm, 2*cm, 2.5*cm])
                devolucoes_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#e8f5e8')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#27ae60')),
                    ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                    ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                    ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                    ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                    ('ALIGN', (4, 1), (4, -1), 'LEFT'),
                    ('ALIGN', (5, 1), (5, -1), 'CENTER'),
                    ('ALIGN', (6, 1), (6, -1), 'LEFT'),
                    ('FONTSIZE', (0, 1), (-1, -1), 6),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#e8f5e8'), colors.white]),
                ]))
                elements.append(devolucoes_table)
                elements.append(Spacer(1, 1*cm))
            
            
            # EstatÃÂ­sticas por policial (se nÃÂ£o houver filtro especÃÂ­fico)
            if not policial and total_movimentacoes > 0:
                elements.append(Paragraph('Ã°Å¸â€˜Â¥ ESTATÃÂ STICAS POR POLICIAL', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                # Agrupa movimentaÃÂ§ÃÂµes por policial
                policiais_stats = {}
                for mov in movimentacoes:
                    policial_id = mov.policial.id
                    if policial_id not in policiais_stats:
                        policiais_stats[policial_id] = {
                            'nome': mov.policial.nome,
                            're': mov.policial.re,
                            'retiradas': 0,
                            'devolucoes': 0,
                            'qtd_retirada': 0,
                            'qtd_devolvida': 0
                        }
                    
                    if mov.tipo == 'RETIRADA':
                        policiais_stats[policial_id]['retiradas'] += 1
                        policiais_stats[policial_id]['qtd_retirada'] += mov.quantidade
                    else:
                        policiais_stats[policial_id]['devolucoes'] += 1
                        policiais_stats[policial_id]['qtd_devolvida'] += mov.quantidade
                
                policiais_data = [
                    ['Policial', 'RE', 'Retiradas', 'DevoluÃÂ§ÃÂµes', 'Qtd. Retirada', 'Qtd. Devolvida']
                ]
                
                for stats in policiais_stats.values():
                    policiais_data.append([
                        stats['nome'],
                        stats['re'],
                        stats['retiradas'],
                        stats['devolucoes'],
                        f"{stats['qtd_retirada']:.2f}",
                        f"{stats['qtd_devolvida']:.2f}"
                    ])
                
                policiais_table = Table(policiais_data, colWidths=[4*cm, 2*cm, 2*cm, 2*cm, 2.5*cm, 2.5*cm])
                policiais_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f4f1f7')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#9b59b6')),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f4f1f7'), colors.white]),
                ]))
                elements.append(policiais_table)
                elements.append(Spacer(1, 1*cm))
            
            # ObservaÃÂ§ÃÂµes
            if observacoes:
                elements.append(Paragraph('Ã°Å¸â€œÂ  OBSERVAÃâ€¡Ãâ€¢ES', subtitle_style))
                elements.append(Paragraph(observacoes, normal_style))
                elements.append(Spacer(1, 0.5*cm))
            
            # RodapÃÂ©
            elements.append(Paragraph('--- RelatÃÂ³rio gerado automaticamente pelo SIS LOGÃÂ STICA 2Ã‚ºBAEP ---', normal_style))
            
            # Gera o PDF
            def _on_page(canvas_, doc_):
                canvas_.saveState()
                _draw_logo(canvas_, doc_)
                canvas_.restoreState()

            doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
            pdf = buffer.getvalue()
            buffer.close()
            
            # Determina o tipo de relatÃÂ³rio com base nos filtros
            tipo_relatorio = 'MOVIMENTACOES'
            
            # Se nÃÂ£o houver filtros especÃÂ­ficos, ÃÂ© um relatÃÂ³rio geral
            if data_inicio and data_fim and data_inicio == data_fim:
                tipo_relatorio = 'MOVIMENTACOES_DIA'
            elif data_inicio and data_fim:
                tipo_relatorio = 'MOVIMENTACOES_PERIODO'
            elif policial:
                tipo_relatorio = 'MOVIMENTACOES_POLICIAL'
            elif material:
                tipo_relatorio = 'MOVIMENTACOES_MATERIAL'
            
            # Salva o relatÃÂ³rio no banco de dados
            relatorio = Relatorio(
                titulo=titulo,
                tipo=tipo_relatorio,
                modulo='RESERVA',
                gerado_por=request.user,
                observacoes=observacoes,
                periodo_inicio=data_inicio,
                periodo_fim=data_fim
            )
            
            # Salva o arquivo PDF temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf)
                temp_path = temp_file.name
            
            # Associa o arquivo ao relatÃÂ³rio
            with open(temp_path, 'rb') as f:
                relatorio.arquivo_pdf.save(f'relatorio_movimentacoes_{timezone.now().strftime("%Y%m%d%H%M%S")}.pdf', 
                                          io.BytesIO(f.read()))
            
            # Remove o arquivo temporÃÂ¡rio
            os.unlink(temp_path)
            
            messages.success(request, _('RelatÃÂ³rio gerado com sucesso!'))
            return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioMovimentacoesForm(initial={
            'titulo': f'RelatÃÂ³rio de MovimentaÃÂ§ÃÂµes - {timezone.now().strftime("%d/%m/%Y")}',
            'data_inicio': timezone.now().date(),
            'data_fim': timezone.now().date()
        })    
    
    return render(request, 'relatorios/form_relatorio_movimentacoes.html', {'form': form})


@login_required
@require_module_permission('materiais')
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
def gerar_relatorio_patrimonio(request):
    if request.method == 'POST':
        form = RelatorioPatrimonioForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo')
            status = form.cleaned_data.get('status')
            categoria = form.cleaned_data.get('categoria')
            observacoes = form.cleaned_data.get('observacoes', '')

            # Filtra os itens
            itens = ItemPatrimonial.objects.select_related(
                'bem', 'bem__categoria', 'localizacao', 'responsavel_atual'
            ).all()

            if status:
                itens = itens.filter(status=status)
            if categoria:
                itens = itens.filter(bem__categoria=categoria)

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
            elements.append(Paragraph(f"<b>Data de Geração:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
            elements.append(Spacer(1, 0.5*cm))

            # Tabela de itens
            elements.append(Paragraph("Lista de Bens Patrimoniais", subtitle_style))

            if itens.exists():
                header = ['Nº Patrimônio', 'Bem', 'Categoria', 'Status', 'Localização', 'Responsável']
                data = [header]
                for item in itens:
                    data.append([
                        Paragraph(item.numero_patrimonio or '-', table_cell_style),
                        Paragraph(item.bem.nome if item.bem else '-', table_cell_style),
                        Paragraph(item.bem.categoria.nome if item.bem and item.bem.categoria else '-', table_cell_style),
                        Paragraph(item.get_status_display(), table_cell_style),
                        Paragraph(str(item.localizacao) if item.localizacao else '-', table_cell_style),
                        Paragraph(str(item.responsavel_atual) if item.responsavel_atual else '-', table_cell_style),
                    ])
                col_widths = [3*cm, 5*cm, 3.5*cm, 2.5*cm, 3*cm, 2.5*cm]
                table = Table(data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ]))
                elements.append(table)
            else:
                elements.append(Paragraph("Nenhum item encontrado com os filtros aplicados.", normal_style))

            if observacoes:
                elements.append(Spacer(1, 0.5*cm))
                elements.append(Paragraph(f"<b>Observações:</b> {observacoes}", normal_style))

            doc.build(elements, onFirstPage=_draw_logo, onLaterPages=_draw_logo)
            pdf = buffer.getvalue()
            buffer.close()

            relatorio = Relatorio.objects.create(
                titulo=titulo,
                tipo='PATRIMONIO',
                modulo='PATRIMONIO',
                gerado_por=request.user,
                observacoes=observacoes,
            )
            relatorio.arquivo_pdf.save(f"patrimonio_{relatorio.pk}.pdf", io.BytesIO(pdf))

            messages.success(request, _('Relatório gerado com sucesso!'))
            return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioPatrimonioForm()

    return render(request, 'relatorios/form_relatorio_patrimonio.html', {'form': form})


@login_required
@require_module_permission('materiais')
def gerar_relatorio_estoque_movimentacoes(request):
    """Gera relatório de movimentações do estoque (MATERIAL DE CONSUMO §2/§3)"""
    if request.method == 'POST':
        form = RelatorioEstoqueMovimentacoesForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo')
            tipo_mov = form.cleaned_data.get('tipo_movimentacao')
            produto = form.cleaned_data.get('produto')
            data_inicio = form.cleaned_data.get('data_inicio')
            data_fim = form.cleaned_data.get('data_fim')
            observacoes = form.cleaned_data.get('observacoes', '')
            
            # Filtra as movimentações
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
            elements.append(Paragraph(f"<b>Data de Geração:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
            
            periodo_str = f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}" if data_inicio and data_fim else "Todo o período"
            elements.append(Paragraph(f"<b>Período:</b> {periodo_str}", normal_style))
            elements.append(Spacer(1, 0.5*cm))

            # Resumo
            elements.append(Paragraph("📊 Resumo do Período", subtitle_style))
            total_movs = movimentacoes.count()
            entradas = movimentacoes.filter(tipo_movimentacao='ENTRADA').count()
            saidas = movimentacoes.filter(tipo_movimentacao='SAIDA').count()
            
            resumo_data = [
                ['Tipo', 'Qtd. Operações'],
                ['Entradas', entradas],
                ['Saídas', saidas],
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
            elements.append(Paragraph("📦 Detalhamento de Movimentações", subtitle_style))
            mov_data = [['Data', 'Tipo', 'Material', 'Qtd', 'V. Unit', 'Militar (Saída) / Fornec. (Entrada)']]
            
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
                elements.append(Paragraph("<b>Observações:</b>", normal_style))
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
            
            messages.success(request, _('Relatório gerado com sucesso!'))
            return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
            
    else:
        form = RelatorioEstoqueMovimentacoesForm()
    
    return render(request, 'relatorios/form_relatorio_estoque_movimentacoes.html', {'form': form})


@login_required
@require_module_permission('patrimonio')
def gerar_relatorio_patrimonio(request):
    if request.method == 'POST':
        form = RelatorioPatrimonioForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo')
            status = form.cleaned_data.get('status')
            categoria = form.cleaned_data.get('categoria')
            observacoes = form.cleaned_data.get('observacoes', '')
            
            # Filtra os itens
            itens = ItemPatrimonial.objects.select_related('bem', 'bem__categoria', 'localizacao', 'responsavel_atual').all()
            
            if status:
                itens = itens.filter(status=status)
            if categoria:
                itens = itens.filter(bem__categoria=categoria)
                
            # Gera o relatório PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1*cm, rightMargin=1*cm, topMargin=2*cm, bottomMargin=2*cm)
            elements = []
            
            # Estilos
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=20)
            subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=12, spaceAfter=10)
            normal_style = styles['Normal']
            
            # Título e Cabeçalho
            elements.append(Paragraph(titulo, title_style))
            elements.append(Paragraph(f"<b>Data de Geração:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
            elements.append(Paragraph(f"<b>Gerado por:</b> {request.user.get_full_name() or request.user.username}", normal_style))
            
            filtros = []
            if status: filtros.append(f"Status: {dict(ItemPatrimonial.STATUS_CHOICES).get(status)}")
            if categoria: filtros.append(f"Categoria: {categoria.nome}")
            if filtros:
                elements.append(Paragraph(f"<b>Filtros:</b> {', '.join(filtros)}", normal_style))
            
            elements.append(Spacer(1, 1*cm))
            
            # Resumo
            elements.append(Paragraph("Resumo do Inventário", subtitle_style))
            total = itens.count()
            data_resumo = [
                ['Status', 'Quantidade'],
            ]
            for s_code, s_name in ItemPatrimonial.STATUS_CHOICES:
                count = itens.filter(status=s_code).count()
                if count > 0 or not status:
                    data_resumo.append([s_name, count])
            
            data_resumo.append(['TOTAL', total])
            
            table_resumo = Table(data_resumo, colWidths=[6*cm, 3*cm])
            table_resumo.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ]))
            elements.append(table_resumo)
            elements.append(Spacer(1, 1*cm))
            
            # Tabela de Itens
            elements.append(Paragraph("Detalhamento dos Itens", subtitle_style))
            data_itens = [
                ['Patrimônio', 'Bem / Descrição', 'Série', 'Status', 'Localização']
            ]
            
            for item in itens:
                data_itens.append([
                    item.numero_patrimonio,
                    Paragraph(f"<b>{item.bem.nome}</b><br/><small>{item.bem.categoria.nome}</small>", styles['Normal']),
                    item.numero_serie or '-',
                    item.get_status_display(),
                    item.localizacao.nome if item.localizacao else '-'
                ])
            
            table_itens = Table(data_itens, colWidths=[3*cm, 7*cm, 3*cm, 3*cm, 3*cm])
            table_itens.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elements.append(table_itens)
            
            if observacoes:
                elements.append(Spacer(1, 1*cm))
                elements.append(Paragraph("Observações", subtitle_style))
                elements.append(Paragraph(observacoes, normal_style))
            
            # Gera o PDF
            def _on_page(canvas_, doc_):
                canvas_.saveState()
                _draw_logo(canvas_, doc_)
                canvas_.restoreState()

            doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
            pdf = buffer.getvalue()
            buffer.close()
            
            # Salva no banco
            relatorio = Relatorio(
                titulo=titulo,
                tipo='PATRIMONIO_INVENTARIO',
                modulo='PATRIMONIO',
                gerado_por=request.user,
                observacoes=observacoes,
                data_geracao=timezone.now()
            )
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf)
                temp_path = temp_file.name
            
            with open(temp_path, 'rb') as f:
                relatorio.arquivo_pdf.save(f"inventario_patrimonio_{timezone.now().strftime('%Y%m%d%H%M')}.pdf", io.BytesIO(f.read()))
            
            os.unlink(temp_path)
            
            messages.success(request, _('Relatório de Patrimônio gerado com sucesso!'))
            return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioPatrimonioForm()
        
    return render(request, 'relatorios/form_relatorio_patrimonio.html', {'form': form})

@login_required
@require_module_permission('frota')
def gerar_relatorio_viaturas(request):
    """Gera relatório em PDF de todas as viaturas da frota"""
    viaturas = Viatura.objects.all().order_by('modelo__tipo', 'prefixo')
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=20)
    style_header = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', alignment=1, textColor=colors.whitesmoke)
    style_cell = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, alignment=1)
    
    # Cabeçalho
    elements.append(Paragraph("POLÍCIA MILITAR DO ESTADO DE SÃO PAULO", style_title))
    elements.append(Paragraph("2º BATALHÃO DE AÇÕES ESPECIAIS DE POLÍCIA", style_title))
    elements.append(Paragraph(f"RELATÓRIO GERAL DA FROTA - {timezone.now().strftime('%d/%m/%Y %H:%M')}", style_title))
    elements.append(Spacer(1, 12))
    
    headers = [
        Paragraph('Prefixo', style_header),
        Paragraph('Modelo', style_header),
        Paragraph('Placa', style_header),
        Paragraph('Status', style_header),
        Paragraph('Odômetro', style_header)
    ]
    data = [headers]
    for v in viaturas:
        data.append([
            Paragraph(v.prefixo, style_cell),
            Paragraph(v.modelo.nome, style_cell),
            Paragraph(v.placa or '-', style_cell),
            Paragraph(v.get_status_display(), style_cell),
            Paragraph(f"{v.odometro_atual} km", style_cell)
        ])
    
    table = Table(data, colWidths=[2.5*cm, 5.0*cm, 2.5*cm, 6.0*cm, 3.0*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Total de Viaturas: {viaturas.count()}", styles['Normal']))
    
    doc.build(elements, onFirstPage=_draw_logo, onLaterPages=_draw_logo)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="relatorio_frota.pdf"'
    response.write(pdf)
    return response

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


