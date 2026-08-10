import io
from django.http import HttpResponse
from django.db.models import Sum, Count
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from relatorios.utils import PDFReportGenerator
from .models import CicloInventario, ItemInventario, ContaContabil


def gerar_termo_inventario_pdf(request, ciclo_id):
    ciclo = CicloInventario.objects.prefetch_related('itens', 'itens__conta_contabil').get(pk=ciclo_id)
    
    buffer = io.BytesIO()
    generator = PDFReportGenerator(
        buffer=buffer,
        title=f"Termo de Inventário - {ciclo.termo_numero}",
        user=request.user
    )
    styles = generator.styles
    elements = []

    # 1. Cabeçalho Oficial PMESP
    elements.append(Paragraph("POLÍCIA MILITAR DO ESTADO DE SÃO PAULO", styles['Heading1']))
    elements.append(Paragraph("COMANDO DE POLICIAMENTO DO INTERIOR SEIS", styles['Heading2']))
    elements.append(Paragraph("SEGUNDO BATALHÃO DE AÇÕES ESPECIAIS DE POLÍCIA", styles['Heading2']))
    elements.append(Spacer(1, 0.4 * cm))

    # 2. Título do Termo
    elements.append(Paragraph(f"TERMO DE INVENTÁRIO FÍSICO E CONTÁBIL — Nº {ciclo.termo_numero}", styles['SectionHeader']))
    elements.append(Spacer(1, 0.2 * cm))

    # 3. Texto Regulamentar Oficial
    data_formatada = ciclo.data_referencia.strftime('%d de %B de %Y')
    detentor = ciclo.detentor_executivo or "Cap PM Detentor Executivo"
    
    texto_intro = (
        f"Aos {ciclo.data_referencia.day} dias do mês de {ciclo.data_referencia.strftime('%B')} de {ciclo.data_referencia.year}, "
        f"na sede do 2º BAEP, o Sr. <b>{detentor}</b>, Detentor Executivo da OPM: <b>{ciclo.opm_codigos}</b>, "
        f"em conformidade com o disposto nos artigos 54 e 90 da <b>I-23 PM</b>, procedeu à realização do "
        f"Inventário Físico e Contábil de Material Permanente da Unidade, nos termos do artigo 96 da Lei Federal nº 4.320/64 "
        f"e artigos 18 e 20 da Lei Estadual nº 10.320/68, servindo como base a Listagem de Controle de Material (LCM) e o SIPL."
    )
    elements.append(Paragraph(texto_intro, styles['BodyText']))
    elements.append(Spacer(1, 0.5 * cm))

    # 4. Tabela Resumo por Conta Contábil
    elements.append(Paragraph("RESUMO GERAL DAS CONTAS CONTÁBEIS", styles['SectionHeader']))
    
    contas_resumo = ItemInventario.objects.filter(ciclo=ciclo).values(
        'conta_contabil__codigo',
        'conta_contabil__nome'
    ).annotate(
        qtd=Count('id'),
        valor_total=Sum('valor')
    ).order_by('conta_contabil__codigo')

    linhas_contas = [['Conta', 'Descrição da Conta Contábil', 'Qtd Bens', 'Valor Total (R$)']]
    valor_geral = 0.0
    qtd_geral = 0

    for c in contas_resumo:
        codigo = c['conta_contabil__codigo'] or 'N/A'
        nome = c['conta_contabil__nome'] or 'Outros Bens'
        qtd = c['qtd']
        val = c['valor_total'] or 0.0
        valor_geral += float(val)
        qtd_geral += qtd
        
        linhas_contas.append([
            codigo,
            nome,
            str(qtd),
            f"R$ {val:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
        ])

    linhas_contas.append([
        'TOTAL GERAL',
        'PATRIMÔNIO TOTAL DA UNIDADE',
        str(qtd_geral),
        f"R$ {valor_geral:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
    ])

    tabela_contas = generator.create_table(
        linhas_contas,
        col_widths=[3.0 * cm, 8.5 * cm, 2.5 * cm, 3.5 * cm]
    )
    elements.append(tabela_contas)
    elements.append(Spacer(1, 0.5 * cm))

    # 5. Bens em Processo de Exclusão / Descarte
    itens_exclusao = ItemInventario.objects.filter(ciclo=ciclo, situacao_material__icontains='EXCLUSÃO')
    if itens_exclusao.exists():
        elements.append(Paragraph(f"BENS EM PROCESSO DE EXCLUSÃO/BAIXA ({itens_exclusao.count()} ITENS)", styles['SectionHeader']))
        linhas_exclusao = [['Seção', 'Patrimônio', 'Nº Série', 'Descrição', 'Situação']]
        for item in itens_exclusao[:30]:  # Exibe os 30 primeiros na folha
            linhas_exclusao.append([
                item.secao_subunidade,
                item.patrimonio,
                item.numero_serie or '-',
                item.tipo_material,
                item.situacao_material
            ])
        tabela_exclusao = generator.create_table(
            linhas_exclusao,
            col_widths=[3.5 * cm, 2.5 * cm, 2.5 * cm, 4.5 * cm, 4.5 * cm]
        )
        elements.append(tabela_exclusao)
        elements.append(Spacer(1, 0.5 * cm))

    # 6. Termo de Encerramento e Assinaturas
    elements.append(Paragraph("TERMO DE ENCERRAMENTO E CERTIFICAÇÃO", styles['SectionHeader']))
    texto_encerramento = (
        "E, por estar conforme e representar a exata expressão da verdade sobre a existência física "
        "e a situação contábil dos bens patrimoniais do 2º BAEP, lavrou-se o presente Termo de Inventário "
        "que vai devidamente assinado pelo Detentor Executivo e pela Comissão de Inventário."
    )
    elements.append(Paragraph(texto_encerramento, styles['BodyText']))
    elements.append(Spacer(1, 1.2 * cm))

    # Tabela de Assinaturas
    assinaturas = [
        ['_______________________________________________', '_______________________________________________'],
        [f'{detentor}', 'Comissão de Inventário Físico/Contábil'],
        ['Detentor Executivo — 2º BAEP', 'Oficial Membro / Auditor']
    ]
    t_ass = Table(assinaturas, colWidths=[8.5 * cm, 8.5 * cm])
    t_ass.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(t_ass)

    generator.generate(elements)
    pdf_content = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="termo_inventario_{ciclo.id}.pdf"'
    return response
