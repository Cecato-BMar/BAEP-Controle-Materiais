from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
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
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
from django.conf import settings
from django.http import HttpResponse, FileResponse

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
                created_mov_ids = []
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
                    created_mov_ids.append(str(movimentacao.id))
                    
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
                    if material.status == 'DISPONIVEL':
                        material.status = 'EM_USO'
                    material.save()
                
                messages.success(request, _('Retirada registrada com sucesso!'))
                return redirect(f"{reverse('movimentacoes:confirmacao_retirada')}?ids={','.join(created_mov_ids)}")
                
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
    
    from estoque.models import LocalizacaoFisica
    localizacoes = LocalizacaoFisica.objects.filter(ativo=True)
    
    return render(request, 'movimentacoes/form_retirada.html', {
        'form': form,
        'materiais': materiais_disponiveis,
        'localizacoes': localizacoes,
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


@login_required
@require_module_permission('reserva_armas')
def confirmacao_retirada(request):
    ids_str = request.GET.get('ids', '')
    # Remove espaços e filtra itens vazios
    ids = [int(i.strip()) for i in ids_str.split(',') if i.strip().isdigit()]
    
    movimentacoes = Movimentacao.objects.filter(id__in=ids).select_related('material', 'policial', 'retirada')
    
    if not movimentacoes:
        messages.warning(request, _('Não foi possível carregar o resumo da retirada. Verifique o histórico.'))
        return redirect('movimentacoes:lista_movimentacoes')
        
    return render(request, 'movimentacoes/confirmacao_retirada.html', {
        'movimentacoes': movimentacoes,
        'ids_str': ids_str,
        'policial': movimentacoes[0].policial,
    })


@login_required
@require_module_permission('reserva_armas')
def gerar_recibo_retirada(request):
    """Gera recibo de retirada em PDF (A5)"""
    ids_str = request.GET.get('ids', '')
    if not ids_str:
        # Tenta pegar um ID unitário
        mov_id = request.GET.get('mov_id')
        if mov_id:
            ids = [mov_id]
        else:
            return HttpResponse("IDs de movimentação não fornecidos.", status=400)
    else:
        ids = [int(i) for i in ids_str.split(',') if i.isdigit()]
        
    movimentacoes = Movimentacao.objects.filter(id__in=ids, tipo='RETIRADA').select_related('material', 'policial', 'retirada', 'registrado_por')
    
    if not movimentacoes:
        return HttpResponse("Nenhuma retirada encontrada para os IDs fornecidos.", status=404)
        
    mov_principal = movimentacoes[0]
    retirada_principal = getattr(mov_principal, 'retirada', None)
    
    buffer = io.BytesIO()
    # A5: 14.8 x 21.0 cm
    doc = SimpleDocTemplate(buffer, pagesize=A5, leftMargin=1*cm, rightMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
    elements = []
    
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=9, leading=11, alignment=1, textColor=colors.white, fontName='Helvetica-Bold')
    section_title = ParagraphStyle('SectionTitle', parent=styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=5)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=8, leading=10)
    
    # Cabeçalho
    header_data = [
        [Paragraph("BATALHÃO DE AÇÕES ESPECIAIS DE POLÍCIA - BAEP<br/>RECIBO DE RETIRADA DE MATERIAL", header_style)]
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
    local_data_hora = timezone.localtime(mov_principal.data_hora)
    info_data = [
        [Paragraph(f"<b>Nº do Recibo:</b> #{mov_principal.pk:06d}", body_style), Paragraph(f"<b>Data:</b> {local_data_hora.strftime('%d/%m/%Y')}", body_style)],
        [Paragraph(f"<b>Hora:</b> {local_data_hora.strftime('%H:%M')}", body_style), Paragraph(f"<b>Registrado por:</b> {mov_principal.registrado_por.username}", body_style)]
    ]
    info_table = Table(info_data, colWidths=[6.4*cm, 6.4*cm])
    info_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(info_table)
    
    # Dados do Policial
    elements.append(Paragraph("DADOS DO POLICIAL", section_title))
    p = mov_principal.policial
    pol_data = [
        [Paragraph(f"<b>Nome:</b> {p.nome}", body_style)],
        [Paragraph(f"<b>RE:</b> {p.re}          <b>Posto/Grad:</b> {p.get_posto_display() if hasattr(p, 'get_posto_display') else ''}", body_style)]
    ]
    pol_table = Table(pol_data, colWidths=[12.8*cm])
    pol_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(pol_table)
    
    # Materiais
    elements.append(Paragraph("MATERIAL RETIRADO", section_title))
    mat_data = [['Identificação / Série', 'Tipo', 'Qtd']]
    for m in movimentacoes:
        mat_data.append([
            Paragraph(f"{m.material.nome} ({m.material.numero})", body_style),
            m.material.get_tipo_display(),
            str(m.quantidade)
        ])
    
    mat_table = Table(mat_data, colWidths=[7.8*cm, 3*cm, 2*cm])
    mat_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.white])
    ]))
    elements.append(mat_table)
    
    # Detalhes da Retirada
    if retirada_principal:
        elements.append(Spacer(1, 0.3*cm))
        det_data = [
            [Paragraph(f"<b>Finalidade:</b> {retirada_principal.finalidade}", body_style)],
            [Paragraph(f"<b>Local de Uso:</b> {retirada_principal.local_uso or '-'}", body_style)],
            [Paragraph(f"<b>Previsão de Devolução:</b> {retirada_principal.data_prevista_devolucao.strftime('%d/%m/%Y %H:%M') if retirada_principal.data_prevista_devolucao else '-'}", body_style)],
            [Paragraph(f"<b>Observações:</b> {mov_principal.observacoes or '-'}", body_style)]
        ]
        det_table = Table(det_data, colWidths=[12.8*cm])
        det_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(det_table)
        
    # Declaração
    elements.append(Spacer(1, 0.5*cm))
    declaracao = "Declaro que recebi o(s) material(is) acima listado(s) em perfeito estado de conservação e comprometo-me a devolvê-lo(s) no prazo estipulado."
    elements.append(Paragraph(declaracao, body_style))
    
    # Assinaturas
    elements.append(Spacer(1, 1.2*cm))
    sig_data = [
        ["________________________________", "________________________________"],
        ["Assinatura do Policial", "Data e Hora"],
        [f"RE: {p.re}", "___/___/_____  ___:___"]
    ]
    sig_table = Table(sig_data, colWidths=[6.4*cm, 6.4*cm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
    ]))
    elements.append(sig_table)
    
    elements.append(Spacer(1, 0.8*cm))
    sig_entrega = [
        ["________________________________"],
        ["Responsável pela Entrega"],
        ["(carimbo/assinatura)"]
    ]
    entrega_table = Table(sig_entrega, colWidths=[6.4*cm])
    entrega_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
    ]))
    elements.append(entrega_table)
    
    # Elementos fixos da página (Apenas Rodapé)
    def draw_page_elements(canvas, doc):
        canvas.saveState()
        
        # 1. Rodapé Textual
        canvas.setFont('Helvetica', 6)
        canvas.drawCentredString(A5[0]/2.0, 0.5*cm, f"Documento gerado automaticamente pelo SIS LOGÍSTICA 2ºBAEP - Página {doc.page}")
        
        canvas.restoreState()

    doc.build(elements, onFirstPage=draw_page_elements, onLaterPages=draw_page_elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="recibo_retirada.pdf"'
    return response
