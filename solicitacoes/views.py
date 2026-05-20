from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponseForbidden
from .models import Solicitacao, ItemSolicitacao, ConfiguracaoSolicitacao
from estoque.models import Produto

def get_config_solicitacao():
    config, created = ConfiguracaoSolicitacao.objects.get_or_create(id=1)
    return config

class MinhasSolicitacoesView(LoginRequiredMixin, ListView):
    model = Solicitacao
    template_name = 'solicitacoes/minhas_solicitacoes.html'
    context_object_name = 'solicitacoes'

    def get_queryset(self):
        return Solicitacao.objects.filter(solicitante=self.request.user)

class CatalogoMateriaisView(LoginRequiredMixin, ListView):
    model = Produto
    template_name = 'solicitacoes/catalogo.html'
    context_object_name = 'produtos'
    paginate_by = 12

    def get_queryset(self):
        queryset = Produto.objects.filter(status='ATIVO', disponivel_solicitacao=True).order_by('nome')
        q = self.request.GET.get('q')
        categoria = self.request.GET.get('categoria')
        
        if q:
            queryset = queryset.filter(nome__icontains=q) | queryset.filter(codigo__icontains=q)
        if categoria:
            queryset = queryset.filter(categoria_id=categoria)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from estoque.models import Categoria
        context['categorias'] = Categoria.objects.filter(ativo=True)
        context['config'] = get_config_solicitacao()
        return context

class VerCarrinhoView(LoginRequiredMixin, TemplateView):
    template_name = 'solicitacoes/carrinho.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        carrinho = self.request.session.get('carrinho', {})
        itens_carrinho = []
        
        for produto_id, quantidade in carrinho.items():
            produto = get_object_or_404(Produto, id=int(produto_id))
            itens_carrinho.append({
                'produto': produto,
                'quantidade': quantidade
            })
        
        context['itens_carrinho'] = itens_carrinho
        
        from estoque.models import OrgaoRequisitante
        context['orgaos'] = OrgaoRequisitante.objects.filter(ativo=True).order_by('nome')
        
        return context

@login_required
def adicionar_ao_carrinho(request, produto_id):
    carrinho = request.session.get('carrinho', {})
    quantidade = int(request.POST.get('quantidade', 1))
    
    produto_id_str = str(produto_id)
    if produto_id_str in carrinho:
        carrinho[produto_id_str] += quantidade
    else:
        carrinho[produto_id_str] = quantidade
    
    request.session['carrinho'] = carrinho
    messages.success(request, 'Item adicionado à sua solicitação.')
    return redirect('solicitacoes:novo_pedido')

@login_required
def remover_do_carrinho(request, produto_id):
    carrinho = request.session.get('carrinho', {})
    produto_id_str = str(produto_id)
    
    if produto_id_str in carrinho:
        del carrinho[produto_id_str]
        request.session['carrinho'] = carrinho
        messages.success(request, 'Item removido.')
    
    return redirect('solicitacoes:ver_carrinho')

@login_required
@transaction.atomic
def finalizar_solicitacao(request):
    carrinho = request.session.get('carrinho', {})
    
    if not carrinho:
        messages.error(request, 'Sua lista de solicitação está vazia.')
        return redirect('solicitacoes:novo_pedido')
    
    # Criar a solicitação principal
    solicitacao = Solicitacao.objects.create(
        solicitante=request.user,
        orgao_requisitante_id=request.POST.get('orgao_requisitante'),
        descricao_outra_unidade=request.POST.get('descricao_outra_unidade'),
        policial_requisitante_id=request.POST.get('policial_requisitante') or None,
        observacoes=request.POST.get('observacoes', '')
    )
    
    # Criar os itens da solicitação
    for produto_id, quantidade in carrinho.items():
        produto = get_object_or_404(Produto, id=int(produto_id))
        ItemSolicitacao.objects.create(
            solicitacao=solicitacao,
            produto=produto,
            quantidade_solicitada=quantidade
        )
    
    # Limpar carrinho
    request.session['carrinho'] = {}
    
    messages.success(request, f'Solicitação #{solicitacao.id} enviada com sucesso! Ela está sendo processada pelo Almoxarifado.')
    return redirect('solicitacoes:minhas_solicitacoes')

class DetalheSolicitacaoView(LoginRequiredMixin, DetailView):
    model = Solicitacao
    template_name = 'solicitacoes/detalhe_solicitacao.html'
    context_object_name = 'solicitacao'

    def get_queryset(self):
        # Usuários comuns veem só as delas, Logística vê todas
        if self.request.user.is_superuser or self.request.user.groups.filter(name='materiais').exists():
            return Solicitacao.objects.all()
        return Solicitacao.objects.filter(solicitante=self.request.user)

# --- VIEWS DE GESTÃO (LOGÍSTICA) ---

class GerenciarSolicitacoesView(LoginRequiredMixin, ListView):
    model = Solicitacao
    template_name = 'solicitacoes/gestao_lista.html'
    context_object_name = 'solicitacoes'

    def get_queryset(self):
        return Solicitacao.objects.all().order_by('-data_solicitacao')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['config'] = get_config_solicitacao()
        return context

@login_required
def toggle_visibilidade_estoque(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='materiais').exists()):
        return HttpResponseForbidden("Acesso negado.")
    
    config = get_config_solicitacao()
    config.exibir_quantidade_disponivel = not config.exibir_quantidade_disponivel
    config.save()
    
    status = "ativada" if config.exibir_quantidade_disponivel else "desativada"
    messages.success(request, f"Visualização de estoque {status} com sucesso.")
    return redirect('solicitacoes:gestao_lista')

@login_required
@transaction.atomic
def mudar_status_solicitacao(request, pk, novo_status):
    solicitacao = get_object_or_404(Solicitacao, pk=pk)
    solicitacao.status = novo_status
    
    if request.method == 'POST':
        solicitacao.notas_admin = request.POST.get('notas_admin', '')
        
        # Se estiver finalizando, registra as quantidades atendidas e cria movimentação
        if novo_status == 'ENTREGUE':
            solicitacao.entregue_por = request.user
            from estoque.models import MovimentacaoEstoque
            from decimal import Decimal
            
            for item in solicitacao.itens.all():
                qtd_atendida = request.POST.get(f'qtd_atendida_{item.id}')
                if qtd_atendida and Decimal(qtd_atendida) > 0:
                    item.quantidade_atendida = qtd_atendida
                    item.save()
                    
                    # Priorizar o policial_requisitante da própria solicitação
                    # Se não houver, tenta buscar o vinculado ao usuário (legado/fallback)
                    policial = solicitacao.policial_requisitante
                    if not policial:
                        try:
                            policial = solicitacao.solicitante.perfil.policial
                        except:
                            pass

                    # Criar registro formal de movimentação de saída
                    MovimentacaoEstoque.objects.create(
                        produto=item.produto,
                        tipo_movimentacao='SAIDA',
                        subtipo='REQUISICAO',
                        quantidade=Decimal(qtd_atendida),
                        orgao_requisitante=solicitacao.orgao_requisitante, # Adicionado campo destino
                        descricao_outra_unidade=solicitacao.descricao_outra_unidade,
                        militar_requisitante=policial,
                        usuario=request.user,  # Auditoria: Quem entregou
                        documento_referencia=f"SOLIC-# {solicitacao.id}",
                        data_movimentacao=solicitacao.data_atualizacao.date(),
                        observacoes=f"Retirada Ref. Solicitação #{solicitacao.id}. {solicitacao.notas_admin}"
                    )
                    
                    # Atualizar cache do produto (se houver essa lógica no save do MovimentacaoEstoque ele já faz, 
                    # mas garantimos aqui se necessário)
                    produto = item.produto
                    produto.estoque_atual -= Decimal(qtd_atendida)
                    produto.save()
    
    solicitacao.save()
    messages.success(request, f'Status da solicitação #{pk} atualizado para {solicitacao.get_status_display()}.')
    return redirect('solicitacoes:gestao_lista')

@login_required
def visualizar_recibo(request, pk):
    solicitacao = get_object_or_404(Solicitacao, pk=pk)
    eh_gestor = request.user.is_staff or request.user.is_superuser or \
                request.user.groups.filter(name='materiais').exists()
    if not eh_gestor and solicitacao.solicitante != request.user:
        return HttpResponseForbidden("Acesso negado.")
    
    return render(request, 'solicitacoes/recibo_entrega.html', {
        'solicitacao': solicitacao,
        'data_atual': timezone.now()
    })

@login_required
def gerar_recibo_pdf(request, pk):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
    from django.http import HttpResponse
    from io import BytesIO
    from django.utils.timezone import localtime
    from django.conf import settings
    import os

    solicitacao = get_object_or_404(Solicitacao, pk=pk)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
        # Cabeçalho Padrão Imagem 2
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo_baep.png')
    
    # Obter sigla do órgão requisitante
    orgao_sigla = solicitacao.orgao_requisitante.sigla if solicitacao.orgao_requisitante else 'Logística'
    if orgao_sigla == 'OUTRA' and solicitacao.descricao_outra_unidade:
        orgao_sigla = solicitacao.descricao_outra_unidade
        
    header_text_content = (
        "<font size=9>SECRETARIA DA SEGURANÇA PÚBLICA</font><br/>"
        "<font size=11><b>POLÍCIA MILITAR DO ESTADO DE SÃO PAULO</b></font><br/>"
        "<font size=10>2º BATALHÃO DE AÇÕES ESPECIAIS DE POLÍCIA</font>"
    )
    
    # Criar Tabela para o Cabeçalho (Logo e Textos)
    header_data = []
    if os.path.exists(logo_path):
        img = Image(logo_path, width=50, height=50)
        
        header_text = Paragraph(header_text_content, styles['Normal'])
        header_text.alignment = 1 
        
        header_data = [[img, header_text]]
        header_table = Table(header_data, colWidths=[60, 475])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ]))
        elements.append(header_table)
    else:
        header_text = Paragraph(header_text_content, styles['Normal'])
        header_text.alignment = 1
        
        header_table = Table([[header_text]], colWidths=[535])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ]))
        elements.append(header_table)

    elements.append(Spacer(1, 5))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    elements.append(Spacer(1, 20))

    # Título do Documento com a numeração solicitada
    dt_pedido = localtime(solicitacao.data_solicitacao).strftime('%d/%m/%Y %H:%M')
    dt_entrega = localtime(solicitacao.data_atualizacao).strftime('%d/%m/%Y %H:%M')
    year_num = localtime(solicitacao.data_atualizacao).year
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=1, spaceAfter=20)
    elements.append(Paragraph(f"RECIBO Nº 2BAEP-{solicitacao.id:03d}/40/{year_num}", title_style))
    
    # Determinar Requisitante para o Recibo
    if solicitacao.policial_requisitante:
        requisitante_nome = f"{solicitacao.policial_requisitante.get_posto_display()} {solicitacao.policial_requisitante.re} {solicitacao.policial_requisitante.nome}"
    else:
        requisitante_nome = solicitacao.solicitante.get_full_name() or solicitacao.solicitante.username

    elements.append(Paragraph(f"<b>Requisitante/Destino:</b> {requisitante_nome}", styles['Normal']))
    secao_unidade = solicitacao.orgao_requisitante.nome if solicitacao.orgao_requisitante else 'Não informada'
    if solicitacao.orgao_requisitante and solicitacao.orgao_requisitante.sigla == 'OUTRA' and solicitacao.descricao_outra_unidade:
        secao_unidade = f"{secao_unidade} - {solicitacao.descricao_outra_unidade}"
    elements.append(Paragraph(f"<b>Seção/Unidade:</b> {secao_unidade}", styles['Normal']))
    elements.append(Paragraph(f"<b>Data do Pedido:</b> {dt_pedido}", styles['Normal']))
    elements.append(Paragraph(f"<b>Data da Entrega:</b> {dt_entrega}", styles['Normal']))
    if solicitacao.entregue_por:
        elements.append(Paragraph(f"<b>Entregue por (Logística):</b> {solicitacao.entregue_por.get_full_name() or solicitacao.entregue_por.username}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Mensagem de recebimento
    elements.append(Paragraph("Recebi do P/4 do 2º BAEP os materiais abaixo relacionados:", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # Tabela de Itens (Mesma lógica)
    data = [['Material', 'Código', 'Qtd. Pedida', 'Qtd. Entregue']]
    for item in solicitacao.itens.all():
        data.append([
            item.produto.nome,
            item.produto.codigo,
            str(item.quantidade_solicitada),
            str(item.quantidade_atendida)
        ])
    
    t = Table(data, colWidths=[250, 100, 80, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    elements.append(t)
    
    # Datas formatadas por extenso em Português
    meses = {
        1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
        5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
        9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
    }
    dt_atualizacao_local = localtime(solicitacao.data_atualizacao)
    data_formatada = f"SANTOS, {dt_atualizacao_local.day} de {meses[dt_atualizacao_local.month].upper()} de {dt_atualizacao_local.year}"
    
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"<b>{data_formatada}</b>", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    if solicitacao.notas_admin:
        elements.append(Paragraph(f"<b>Observações do Almoxarifado:</b> {solicitacao.notas_admin}", styles['Normal']))
        elements.append(Spacer(1, 30))

    # Assinaturas inspiradas no recibo do docx (apenas o recebedor)
    sig_data = [
        [
            Paragraph(
                "GRAD/NOME COMPLETO: ____________________________________________________________________<br/><br/>"
                "RE: ____________________________________________________________________________________<br/><br/>"
                "ASS: ___________________________________________________________________________________", 
                styles['Normal']
            )
        ]
    ]
    sig_table = Table(sig_data, colWidths=[535])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(sig_table)
    
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="recibo_solicitacao_{solicitacao.id}.pdf"'
    response.write(pdf)
    return response
