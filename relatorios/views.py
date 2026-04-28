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
    RelatorioEstoqueMovimentacoesForm,
    RelatorioSituacaoAtualForm,
    RelatorioTelematicaForm
)
from .utils import PDFReportGenerator
from . import providers
from .providers import TelematicaProvider
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
        'ESTOQUE_SITUACAO': providers.EstoqueSituacaoProvider,
        'ESTOQUE_REPOSICAO': providers.EstoqueCriticoProvider,
        'TELEMATICA_GERAL': providers.TelematicaProvider,
        'TELEMATICA_INVENTARIO': providers.TelematicaProvider,
        'TELEMATICA_MANUTENCAO': providers.TelematicaProvider,
        'TELEMATICA_LINHAS': providers.TelematicaProvider,
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
    elif 'TELEMATICA' in tipo_chave:
        relatorio.modulo = 'TELEMATICA'
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
    if request.user.is_superuser or request.user.groups.filter(name='telematica').exists():
        modulos_acesso.append('TELEMATICA')

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
            tipo = form.cleaned_data.get('tipo_relatorio') or 'ESTOQUE_MOVIMENTACOES'
            titulo = form.cleaned_data.get('titulo') or "Relatório de Estoque"
            relatorio = _gerar_pdf_unificado(request, tipo, titulo, form.cleaned_data)
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
    from viaturas.models import Viatura
    viatura = get_object_or_404(Viatura, pk=viatura_id)
    
    buffer = io.BytesIO()
    generator = PDFReportGenerator(buffer, f"FICHA TÉCNICA DA VIATURA: {viatura.prefixo}", user=request.user)
    
    elements = []
    styles = generator.styles
    
    # Detalhes da Viatura
    elements.append(Paragraph("DADOS DA VIATURA", styles['SectionHeader']))
    dados = [
        ['Prefixo', viatura.prefixo],
        ['Placa', viatura.placa or 'N/A'],
        ['Chassi', viatura.chassi or 'N/A'],
        ['RENAVAM', viatura.renavam or 'N/A'],
        ['Número de Patrimônio', viatura.numero_patrimonio or 'N/A'],
        ['Marca', viatura.modelo.marca.nome],
        ['Modelo', viatura.modelo.nome],
        ['Tipo', viatura.tipo],
        ['Ano de Fabricação', str(viatura.ano_fabricacao) if viatura.ano_fabricacao else 'N/A'],
        ['Cor', viatura.cor],
        ['Tipo de Combustível', viatura.get_tipo_combustivel_display()],
        ['Capacidade do Tanque', f"{viatura.capacidade_tanque} L"],
        ['Odômetro Atual', f"{viatura.odometro_atual} km"],
        ['Status Atual', viatura.get_status_display()],
        ['Localização Atual', viatura.get_localizacao_display() if viatura.localizacao else 'N/A'],
    ]
    
    t = generator.create_table(dados, col_widths=[6*cm, 10*cm])
    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))
    
    if viatura.observacoes:
        elements.append(Paragraph("OBSERVAÇÕES ADICIONAIS", styles['SectionHeader']))
        elements.append(Paragraph(viatura.observacoes, styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
    # Últimos Despachos
    elements.append(Paragraph("ÚLTIMOS DESPACHOS", styles['SectionHeader']))
    despachos = viatura.despachos.select_related('motorista').order_by('-data_saida')[:10]
    
    if despachos.exists():
        dados_despachos = [['Data/Hora Saída', 'Motorista', 'Km Saída', 'Data Retorno', 'Km Retorno']]
        for desp in despachos:
            dados_despachos.append([
                desp.data_saida.strftime('%d/%m/%Y %H:%M'),
                str(desp.motorista.nome) if desp.motorista else 'N/A',
                str(desp.km_saida),
                desp.data_retorno.strftime('%d/%m/%Y %H:%M') if desp.data_retorno else 'Em curso',
                str(desp.km_retorno) if desp.km_retorno else '-'
            ])
        t_desp = generator.create_table(dados_despachos, col_widths=[3.5*cm, 4.5*cm, 2*cm, 3.5*cm, 2.5*cm])
        elements.append(t_desp)
    else:
        elements.append(Paragraph("Nenhum despacho registrado para esta viatura.", styles['Normal']))
        
    elements.append(Spacer(1, 0.5*cm))
    
    # Últimas Manutenções
    elements.append(Paragraph("ÚLTIMAS MANUTENÇÕES", styles['SectionHeader']))
    manutencoes = viatura.manutencoes.order_by('-data_inicio')[:10]
    
    if manutencoes.exists():
        dados_manut = [['Tipo', 'Início', 'Conclusão', 'Oficina', 'Custo Total']]
        for manut in manutencoes:
            dados_manut.append([
                manut.get_tipo_display(),
                manut.data_inicio.strftime('%d/%m/%Y'),
                manut.data_conclusao.strftime('%d/%m/%Y') if manut.data_conclusao else 'Aberta',
                str(manut.oficina_fk) if manut.oficina_fk else str(manut.oficina or '-'),
                f"R$ {manut.custo_total:.2f}"
            ])
        t_manut = generator.create_table(dados_manut, col_widths=[3.5*cm, 2.5*cm, 2.5*cm, 4.5*cm, 3*cm])
        elements.append(t_manut)
    else:
        elements.append(Paragraph("Nenhuma manutenção registrada para esta viatura.", styles['Normal']))
    
    generator.generate(elements)
    
    pdf_content = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="ficha_viatura_{viatura.prefixo}.pdf"'
    return response

@login_required
@require_module_permission('patrimonio')
def gerar_relatorio_individual_patrimonio(request, item_id):
    from patrimonio.models import ItemPatrimonial
    item = get_object_or_404(ItemPatrimonial, pk=item_id)
    
    buffer = io.BytesIO()
    generator = PDFReportGenerator(buffer, f"FICHA TÉCNICA DO PATRIMÔNIO: {item.numero_patrimonio}", user=request.user)
    
    elements = []
    styles = generator.styles
    
    # Detalhes do item
    elements.append(Paragraph("DADOS GERAIS", styles['SectionHeader']))
    dados = [
        ['Número de Patrimônio', item.numero_patrimonio],
        ['Descrição/Nome', item.bem.nome],
        ['Categoria', item.bem.categoria.nome],
        ['Número de Série', item.numero_serie or 'N/A'],
        ['Marca', item.bem.marca or 'N/A'],
        ['Modelo', item.bem.modelo_referencia or 'N/A'],
        ['Status Atual', item.get_status_display()],
        ['Estado de Conservação', item.get_estado_conservacao_display()],
        ['Localização Atual', str(item.localizacao) if item.localizacao else 'Geral'],
        ['Responsável (Cautela)', str(item.responsavel_atual) if item.responsavel_atual else 'N/A'],
        ['Data de Aquisição', item.data_aquisicao.strftime('%d/%m/%Y') if item.data_aquisicao else 'N/A'],
    ]
    
    t = generator.create_table(dados, col_widths=[6*cm, 10*cm])
    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))
    
    if item.observacoes:
        elements.append(Paragraph("OBSERVAÇÕES ADICIONAIS", styles['SectionHeader']))
        elements.append(Paragraph(item.observacoes, styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
    
    # Histórico de Movimentações
    elements.append(Paragraph("HISTÓRICO DE MOVIMENTAÇÕES", styles['SectionHeader']))
    
    historico = item.historico.select_related('policial', 'local_destino', 'registrado_por').order_by('-data_hora')
    
    if historico.exists():
        dados_hist = [['Data/Hora', 'Tipo', 'Envolvido/Destino', 'Registrado Por', 'Obs']]
        for mov in historico:
            envolvido = str(mov.policial) if mov.policial else (str(mov.local_destino) if mov.local_destino else '-')
            dados_hist.append([
                mov.data_hora.strftime('%d/%m/%Y %H:%M'),
                mov.get_tipo_display(),
                envolvido,
                mov.registrado_por.username,
                mov.observacoes or '-'
            ])
            
        t_hist = generator.create_table(dados_hist, col_widths=[3*cm, 4*cm, 4*cm, 3*cm, 2*cm])
        elements.append(t_hist)
    else:
        elements.append(Paragraph("Nenhuma movimentação registrada para este item.", styles['Normal']))
    
    generator.generate(elements)
    
    pdf_content = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="ficha_patrimonio_{item.numero_patrimonio}.pdf"'
    return response

@login_required
@require_module_permission('frota')
def gerar_relatorio_individual_manutencao(request, manutencao_id):
    from viaturas.models import Manutencao
    manutencao = get_object_or_404(Manutencao, pk=manutencao_id)
    
    buffer = io.BytesIO()
    generator = PDFReportGenerator(buffer, f"FICHA DE MANUTENÇÃO: {manutencao.viatura.prefixo}", user=request.user)
    
    elements = []
    styles = generator.styles
    
    # Detalhes da Viatura e Manutencao
    elements.append(Paragraph("DADOS GERAIS", styles['SectionHeader']))
    dados = [
        ['Viatura', manutencao.viatura.prefixo],
        ['Tipo de Manutenção', manutencao.get_tipo_display()],
        ['Status', manutencao.get_status_display()],
        ['Odômetro na Manutenção', f"{manutencao.odometro} km"],
        ['Data de Início', manutencao.data_inicio.strftime('%d/%m/%Y')],
        ['Data de Conclusão', manutencao.data_conclusao.strftime('%d/%m/%Y') if manutencao.data_conclusao else 'N/A'],
        ['Oficina/Empresa', str(manutencao.oficina_fk) if manutencao.oficina_fk else str(manutencao.oficina or 'N/A')],
        ['Ordem de Serviço (O.S.)', manutencao.ordem_servico or 'N/A'],
        ['Registrado Por', manutencao.registrado_por.get_full_name() or manutencao.registrado_por.username],
    ]
    
    t = generator.create_table(dados, col_widths=[6*cm, 10*cm])
    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))

    # Financeiro
    elements.append(Paragraph("RESUMO FINANCEIRO", styles['SectionHeader']))
    dados_fin = [
        ['Custo com Peças', f"R$ {manutencao.custo_pecas:.2f}"],
        ['Custo Mão de Obra', f"R$ {manutencao.custo_mao_obra:.2f}"],
        ['Custo Total', f"R$ {manutencao.custo_total:.2f}"],
    ]
    t_fin = generator.create_table(dados_fin, col_widths=[6*cm, 10*cm])
    elements.append(t_fin)
    elements.append(Spacer(1, 0.5*cm))
    
    # Descrições e Auditoria
    elements.append(Paragraph("DESCRIÇÃO DOS SERVIÇOS (ABERTURA)", styles['SectionHeader']))
    elements.append(Paragraph(manutencao.descricao or 'Nenhuma descrição inicial registrada.', styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    elements.append(Paragraph("CONTROLE DE QUALIDADE E GARANTIA", styles['SectionHeader']))
    aprovado = "SIM" if manutencao.servicos_executados_corretamente else "NÃO / PENDENTE"
    dados_garantia = [
        ['Serviço Aprovado?', aprovado],
        ['Validade Garantia (Data)', manutencao.data_validade_garantia.strftime('%d/%m/%Y') if manutencao.data_validade_garantia else 'N/A'],
        ['Validade Garantia (Km)', f"{manutencao.km_validade_garantia} km" if manutencao.km_validade_garantia else 'N/A'],
    ]
    t_garantia = generator.create_table(dados_garantia, col_widths=[6*cm, 10*cm])
    elements.append(t_garantia)
    elements.append(Spacer(1, 0.2*cm))
    
    elements.append(Paragraph("DETALHAMENTO DOS SERVIÇOS EXECUTADOS (PÓS-MANUTENÇÃO)", styles['Heading3']))
    elements.append(Paragraph(manutencao.detalhamento_servicos or 'Nenhum detalhamento pós-manutenção registrado.', styles['Normal']))
    elements.append(Spacer(1, 0.3*cm))
    
    elements.append(Paragraph("PEÇAS TROCADAS / CONDIÇÕES DE GARANTIA", styles['Heading3']))
    elements.append(Paragraph(manutencao.detalhamento_pecas_garantia or 'Nenhum detalhamento de peças registrado.', styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Anexos
    elements.append(Paragraph("ANEXOS OFICIAIS (SISTEMA BAEP)", styles['SectionHeader']))
    dados_anexos = [
        ['Nota Fiscal anexada?', 'SIM' if manutencao.nota_fiscal else 'NÃO'],
        ['Termo de Garantia anexado?', 'SIM' if manutencao.termo_garantia else 'NÃO'],
    ]
    t_anexos = generator.create_table(dados_anexos, col_widths=[8*cm, 8*cm])
    elements.append(t_anexos)
    
    generator.generate(elements)
    
    pdf_content = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="ficha_manutencao_OS_{manutencao.ordem_servico or manutencao.pk}.pdf"'
    return response

@login_required
@require_module_permission('telematica')
def gerar_relatorio_telematica(request):
    if request.method == 'POST':
        form = RelatorioTelematicaForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data.get('tipo_relatorio', 'TELEMATICA_GERAL')
            titulo = form.cleaned_data.get('titulo') or "Relatório de Telemática"
            relatorio = _gerar_pdf_unificado(request, tipo, titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, 'Relatório Gerado com Sucesso!')
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioTelematicaForm()
    
    from telematica.models import Equipamento, ManutencaoTI
    return render(request, 'relatorios/form_relatorio_telematica.html', {
        'form': form,
        'total_ativos': Equipamento.objects.count(),
        'em_manutencao': Equipamento.objects.filter(status='MANUTENCAO').count(),
        'manut_abertas': ManutencaoTI.objects.filter(concluida=False).count()
    })
