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
    RelatorioMovimentacoesForm
)
from materiais.models import Material
from movimentacoes.models import Movimentacao, Retirada, Devolucao
from policiais.models import Policial


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
@require_module_permission('reserva_armas')
def lista_relatorios(request):
    relatorios = Relatorio.objects.all().order_by('-data_geracao')
    
    # Filtragem
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
    
    # Paginação
    paginator = Paginator(relatorios, 20)  # 20 itens por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'relatorios/lista_relatorios.html', {
        'relatorios': page_obj,
        'page_obj': page_obj,
        'total_relatorios': relatorios.count(),
    })

@login_required
@require_module_permission('reserva_armas')
def detalhe_relatorio(request, relatorio_id):
    relatorio = get_object_or_404(Relatorio, pk=relatorio_id)
    preview_data = None
    preview_type = None
    # Se não existe PDF, buscar dados para pré-visualização
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
                ['Materiais Disponíveis', materiais_disponiveis],
                ['Materiais em Uso', materiais_em_uso],
                ['Materiais em Manutenção', materiais_manutencao],
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
            # Filtros possíveis: por policial, material, período, tipo
            if relatorio.periodo_inicio:
                movs = movs.filter(data_hora__gte=relatorio.periodo_inicio)
            if relatorio.periodo_fim:
                movs = movs.filter(data_hora__lte=relatorio.periodo_fim)
            preview_data = list(movs.values_list('data_hora', 'tipo', 'material__identificacao', 'policial__nome', 'quantidade'))
            preview_type = 'movimentacoes'
    return render(request, 'relatorios/detalhe_relatorio.html', {
        'relatorio': relatorio,
        'preview_data': preview_data,
        'preview_type': preview_type,
    })

@login_required
@require_module_permission('reserva_armas')
def download_relatorio(request, relatorio_id):
    relatorio = get_object_or_404(Relatorio, pk=relatorio_id)
    
    if not relatorio.arquivo_pdf or not os.path.exists(relatorio.arquivo_pdf.path):
        messages.error(request, _('Arquivo PDF não encontrado.'))
        return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    
    # Renderiza a página de opções de download
    return render(request, 'relatorios/download_relatorio.html', {
        'relatorio': relatorio,
    })

@login_required
@require_module_permission('reserva_armas')
def download_relatorio_arquivo(request, relatorio_id):
    relatorio = get_object_or_404(Relatorio, pk=relatorio_id)
    
    if not relatorio.arquivo_pdf or not os.path.exists(relatorio.arquivo_pdf.path):
        messages.error(request, _('Arquivo PDF não encontrado.'))
        return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    
    if request.method == 'POST':
        # Obter o nome do arquivo personalizado
        nome_arquivo = request.POST.get('nome_arquivo', f'relatorio_{relatorio.id}')
        formato = request.POST.get('formato', 'pdf')
        
        # Sanitizar o nome do arquivo para evitar caracteres inválidos
        nome_arquivo = ''.join(c for c in nome_arquivo if c.isalnum() or c in '-_')
        
        # Se o nome estiver vazio após a sanitização, use um nome padrão
        if not nome_arquivo:
            nome_arquivo = f'relatorio_{relatorio.id}'
        
        # Adicionar a extensão correta
        filename = f'{nome_arquivo}.{formato}'
        
        # Retornar o arquivo para download
        return FileResponse(
            open(relatorio.arquivo_pdf.path, 'rb'),
            content_type='application/pdf',
            as_attachment=True,
            filename=filename
        )
    else:
        # Se não for um POST, redirecionar para a página de download
        return redirect('relatorios:download_relatorio', relatorio_id=relatorio.pk)

@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_situacao_atual(request):
    if request.method == 'POST':
        form = RelatorioSituacaoAtualForm(request.POST)
        if form.is_valid():
            # Gera o relatório PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            
            # Estilos
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            subtitle_style = styles['Heading2']
            normal_style = styles['Normal']
            
            # Título
            titulo = form.cleaned_data.get('titulo', 'Relatório de Situação Atual')
            elements.append(Paragraph(titulo, title_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Data e hora
            data_hora = timezone.now().strftime('%d/%m/%Y %H:%M')
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
                ['Materiais Disponíveis', materiais_disponiveis],
                ['Materiais em Uso', materiais_em_uso],
                ['Materiais em Manutenção', materiais_manutencao],
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
            
            # Mapeamento de códigos para nomes de tipos
            tipo_map = dict(Material.TIPO_CHOICES)
            
            data = [
                ['Tipo de Material', 'Total', 'Disponíveis', 'Em Uso', 'Manutenção', 'Inativos'],
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
            
            # Observações
            if form.cleaned_data.get('observacoes'):
                elements.append(Spacer(1, 1*cm))
                elements.append(Paragraph('Observações:', subtitle_style))
                elements.append(Paragraph(form.cleaned_data.get('observacoes'), normal_style))
            
            # Gera o PDF
            def _on_page(canvas_, doc_):
                canvas_.saveState()
                _draw_logo(canvas_, doc_)
                canvas_.restoreState()

            doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
            pdf = buffer.getvalue()
            buffer.close()
            
            # Salva o relatório no banco de dados
            relatorio = Relatorio(
                titulo=titulo,
                tipo='SITUACAO_ATUAL',
                gerado_por=request.user,
                observacoes=form.cleaned_data.get('observacoes', ''),
                periodo_inicio=timezone.now(),
                periodo_fim=timezone.now()
            )
            
            # Salva o arquivo PDF temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf)
                temp_path = temp_file.name
            
            # Associa o arquivo ao relatório
            with open(temp_path, 'rb') as f:
                relatorio.arquivo_pdf.save(f'relatorio_situacao_{timezone.now().strftime("%Y%m%d%H%M%S")}.pdf', 
                                          io.BytesIO(f.read()))
            
            # Remove o arquivo temporário
            os.unlink(temp_path)
            
            messages.success(request, _('Relatório gerado com sucesso!'))
            return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioSituacaoAtualForm(initial={'titulo': f'Relatório de Situação Atual - {timezone.now().strftime("%d/%m/%Y")}'})    
    
    return render(request, 'relatorios/form_relatorio_situacao.html', {'form': form})

@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_materiais(request):
    if request.method == 'POST':
        form = RelatorioMateriaisForm(request.POST)
        if form.is_valid():
            # Obtém os dados do formulário
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
            
            # Gera o relatório PDF
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
            
            # Cabeçalho do relatório
            elements.append(Paragraph(titulo, title_style))
            elements.append(Spacer(1, 0.3*cm))
            
            # Informações de geração
            data_hora = timezone.now().strftime('%d/%m/%Y às %H:%M')
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
            elements.append(Paragraph('📊 RESUMO EXECUTIVO', subtitle_style))
            
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
                ['', 'Itens', 'Quantidade Total', 'Disponível', 'Em Uso'],
                ['📦 Total Geral', total_materiais, total_quantidade, total_disponivel, total_em_uso],
                ['✅ Disponíveis', materiais_disponiveis, '', '', ''],
                ['🔄 Em Uso', materiais_em_uso, '', '', ''],
                ['🔧 Manutenção', materiais_manutencao, '', '', ''],
                ['🚫 Apreendidos', materiais_apreendidos, '', '', ''],
                ['📉 Baixados', materiais_baixados, '', '', '']
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
            
            # Materiais em Uso (com detalhes dos policiais responsáveis)
            materiais_em_uso_list = materiais.filter(status='EM_USO')
            if materiais_em_uso_list.exists():
                elements.append(Paragraph('👥 MATERIAIS EM USO', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                # Busca informações dos policiais responsáveis
                materiais_com_policiais = []
                for material in materiais_em_uso_list:
                    # Busca a última retirada não devolvida
                    ultima_retirada = Movimentacao.objects.filter(
                        material=material,
                        tipo='RETIRADA'
                    ).exclude(
                        id__in=Movimentacao.objects.filter(
                            material=material,
                            tipo='DEVOLUCAO'
                        ).values_list('id', flat=True)
                    ).order_by('-data_hora').first()
                    
                    policial_info = "Não identificado"
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
                    ['Identificação', 'Tipo', 'Qtd. Em Uso', 'Policial Responsável', 'Data Retirada', 'Finalidade']
                ]
                
                for item in materiais_com_policiais:
                    material = item['material']
                    uso_data.append([
                        material.identificacao,
                        material.get_tipo_display(),
                        material.quantidade_em_uso,
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
            
            # Materiais em Estoque (Disponíveis)
            materiais_disponiveis_list = materiais.filter(status='DISPONIVEL')
            if materiais_disponiveis_list.exists():
                elements.append(Paragraph('📦 MATERIAIS EM ESTOQUE', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                # Tabela de materiais disponíveis
                estoque_data = [
                    ['Identificação', 'Tipo', 'Qtd. Total', 'Qtd. Disponível', 'Estado']
                ]
                
                for material in materiais_disponiveis_list:
                    estoque_data.append([
                        material.identificacao,
                        material.get_tipo_display(),
                        material.quantidade,
                        material.quantidade_disponivel,
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
            
            # Materiais em Manutenção
            materiais_manutencao_list = materiais.filter(status='MANUTENCAO')
            if materiais_manutencao_list.exists():
                elements.append(Paragraph('🔧 MATERIAIS EM MANUTENÇÃO', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                manutencao_data = [
                    ['Identificação', 'Tipo', 'Estado', 'Observações']
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
                elements.append(Paragraph('🚫 MATERIAIS APREENDIDOS', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                apreendidos_data = [
                    ['Identificação', 'Tipo', 'Estado', 'Observações']
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
                elements.append(Paragraph('📉 MATERIAIS BAIXADOS', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                baixados_data = [
                    ['Identificação', 'Tipo', 'Estado', 'Observações']
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
            
            # Observações
            if observacoes:
                elements.append(Paragraph('📝 OBSERVAÇÕES', subtitle_style))
                elements.append(Paragraph(observacoes, normal_style))
                elements.append(Spacer(1, 0.5*cm))
            
            # Rodapé
            elements.append(Paragraph('--- Relatório gerado automaticamente pelo Sistema de Reserva BAEP ---', normal_style))
            
            # Gera o PDF
            def _on_page(canvas_, doc_):
                canvas_.saveState()
                _draw_logo(canvas_, doc_)
                canvas_.restoreState()

            doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
            pdf = buffer.getvalue()
            buffer.close()
            
            # Determina o tipo de relatório com base nos filtros
            tipo_relatorio = 'MATERIAIS'
            if status == 'EM_USO':
                tipo_relatorio = 'MATERIAIS_EM_USO'
            elif status == 'DISPONIVEL':
                tipo_relatorio = 'MATERIAIS_DISPONIVEIS'
            
            # Salva o relatório no banco de dados
            relatorio = Relatorio(
                titulo=titulo,
                tipo=tipo_relatorio,
                gerado_por=request.user,
                observacoes=observacoes,
                periodo_inicio=timezone.now(),
                periodo_fim=timezone.now()
            )
            
            # Salva o arquivo PDF temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf)
                temp_path = temp_file.name
            
            # Associa o arquivo ao relatório
            with open(temp_path, 'rb') as f:
                relatorio.arquivo_pdf.save(f'relatorio_materiais_{timezone.now().strftime("%Y%m%d%H%M%S")}.pdf', 
                                          io.BytesIO(f.read()))
            
            # Remove o arquivo temporário
            os.unlink(temp_path)
            
            messages.success(request, _('Relatório gerado com sucesso!'))
            return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioMateriaisForm(initial={'titulo': f'Relatório de Materiais - {timezone.now().strftime("%d/%m/%Y")}'})    
    
    return render(request, 'relatorios/form_relatorio_materiais.html', {'form': form})

@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_movimentacoes(request):
    if request.method == 'POST':
        form = RelatorioMovimentacoesForm(request.POST)
        if form.is_valid():
            # Obtém os dados do formulário
            titulo = form.cleaned_data.get('titulo')
            tipo_movimentacao = form.cleaned_data.get('tipo_movimentacao')
            data_inicio = form.cleaned_data.get('data_inicio')
            data_fim = form.cleaned_data.get('data_fim')
            policial = form.cleaned_data.get('policial')
            material = form.cleaned_data.get('material')
            observacoes = form.cleaned_data.get('observacoes', '')
            
            # Filtra as movimentações
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
            
            # Gera o relatório PDF
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
            
            # Cabeçalho do relatório
            elements.append(Paragraph(titulo, title_style))
            elements.append(Spacer(1, 0.3*cm))
            
            # Informações de geração
            data_hora = timezone.now().strftime('%d/%m/%Y às %H:%M')
            elements.append(Paragraph(f'<b>Gerado em:</b> {data_hora}', normal_style))
            elements.append(Paragraph(f'<b>Gerado por:</b> {request.user.get_full_name() or request.user.username}', normal_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Filtros aplicados
            filtros = []
            if tipo_movimentacao:
                tipo_display = dict(Movimentacao.TIPO_CHOICES).get(tipo_movimentacao, tipo_movimentacao)
                filtros.append(f'Tipo: {tipo_display}')
            if data_inicio:
                filtros.append(f'Data Início: {data_inicio.strftime("%d/%m/%Y")}')
            if data_fim:
                filtros.append(f'Data Fim: {data_fim.strftime("%d/%m/%Y")}')
            if policial:
                filtros.append(f'Policial: {policial.nome} (RE: {policial.re})')
            if material:
                filtros.append(f'Material: {material.identificacao}')
            
            if filtros:
                elements.append(Paragraph('<b>Filtros aplicados:</b> ' + ', '.join(filtros), normal_style))
                elements.append(Spacer(1, 0.3*cm))
            
            # Período do relatório
            if data_inicio and data_fim:
                elements.append(Paragraph(f'<b>Período:</b> {data_inicio.strftime("%d/%m/%Y")} a {data_fim.strftime("%d/%m/%Y")}', normal_style))
                elements.append(Spacer(1, 0.3*cm))
            
            # Resumo executivo
            elements.append(Paragraph('📊 RESUMO EXECUTIVO', subtitle_style))
            
            total_movimentacoes = movimentacoes.count()
            total_retiradas = movimentacoes.filter(tipo='RETIRADA').count()
            total_devolucoes = movimentacoes.filter(tipo='DEVOLUCAO').count()
            
            # Calcula totais de quantidade
            total_quantidade_retirada = movimentacoes.filter(tipo='RETIRADA').aggregate(Sum('quantidade'))['quantidade__sum'] or 0
            total_quantidade_devolvida = movimentacoes.filter(tipo='DEVOLUCAO').aggregate(Sum('quantidade'))['quantidade__sum'] or 0
            
            # Tabela de resumo
            resumo_data = [
                ['', 'Movimentações', 'Quantidade'],
                ['📤 Retiradas', total_retiradas, total_quantidade_retirada],
                ['📥 Devoluções', total_devolucoes, total_quantidade_devolvida],
                ['📊 Total Geral', total_movimentacoes, total_quantidade_retirada + total_quantidade_devolvida]
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
                elements.append(Paragraph('📤 RETIRADAS', subtitle_style))
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
                        mov.quantidade,
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
                elements.append(Paragraph('📥 DEVOLUÇÕES', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                devolucoes = movimentacoes.filter(tipo='DEVOLUCAO')
                devolucoes_data = [
                    ['Data/Hora', 'Material', 'Policial', 'Qtd.', 'Estado Devolução', 'Retirada Ref.', 'Registrado Por']
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
                        mov.quantidade,
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
            
            # Estatísticas por policial (se não houver filtro específico)
            if not policial and total_movimentacoes > 0:
                elements.append(Paragraph('👥 ESTATÍSTICAS POR POLICIAL', subtitle_style))
                elements.append(Spacer(1, 0.3*cm))
                
                # Agrupa movimentações por policial
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
                    ['Policial', 'RE', 'Retiradas', 'Devoluções', 'Qtd. Retirada', 'Qtd. Devolvida']
                ]
                
                for stats in policiais_stats.values():
                    policiais_data.append([
                        stats['nome'],
                        stats['re'],
                        stats['retiradas'],
                        stats['devolucoes'],
                        stats['qtd_retirada'],
                        stats['qtd_devolvida']
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
            
            # Observações
            if observacoes:
                elements.append(Paragraph('📝 OBSERVAÇÕES', subtitle_style))
                elements.append(Paragraph(observacoes, normal_style))
                elements.append(Spacer(1, 0.5*cm))
            
            # Rodapé
            elements.append(Paragraph('--- Relatório gerado automaticamente pelo Sistema de Reserva BAEP ---', normal_style))
            
            # Gera o PDF
            def _on_page(canvas_, doc_):
                canvas_.saveState()
                _draw_logo(canvas_, doc_)
                canvas_.restoreState()

            doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
            pdf = buffer.getvalue()
            buffer.close()
            
            # Determina o tipo de relatório com base nos filtros
            tipo_relatorio = 'MOVIMENTACOES'
            
            # Se não houver filtros específicos, é um relatório geral
            if data_inicio and data_fim and data_inicio == data_fim:
                tipo_relatorio = 'MOVIMENTACOES_DIA'
            elif data_inicio and data_fim:
                tipo_relatorio = 'MOVIMENTACOES_PERIODO'
            elif policial:
                tipo_relatorio = 'MOVIMENTACOES_POLICIAL'
            elif material:
                tipo_relatorio = 'MOVIMENTACOES_MATERIAL'
            
            # Salva o relatório no banco de dados
            relatorio = Relatorio(
                titulo=titulo,
                tipo=tipo_relatorio,
                gerado_por=request.user,
                observacoes=observacoes,
                periodo_inicio=data_inicio,
                periodo_fim=data_fim
            )
            
            # Salva o arquivo PDF temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf)
                temp_path = temp_file.name
            
            # Associa o arquivo ao relatório
            with open(temp_path, 'rb') as f:
                relatorio.arquivo_pdf.save(f'relatorio_movimentacoes_{timezone.now().strftime("%Y%m%d%H%M%S")}.pdf', 
                                          io.BytesIO(f.read()))
            
            # Remove o arquivo temporário
            os.unlink(temp_path)
            
            messages.success(request, _('Relatório gerado com sucesso!'))
            return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioMovimentacoesForm(initial={
            'titulo': f'Relatório de Movimentações - {timezone.now().strftime("%d/%m/%Y")}',
            'data_inicio': timezone.now().date(),
            'data_fim': timezone.now().date()
        })    
    
    return render(request, 'relatorios/form_relatorio_movimentacoes.html', {'form': form})
