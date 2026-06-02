import io
from datetime import datetime, time

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Q
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer
from .forms import (
    LoteMunicaoForm,
    RetiradaMunicaoForm,
    DevolucaoMunicaoForm,
    DevolucaoCPIForm,
    RelatorioMunicoesForm,
)
from .models import LoteMunicao, RetiradaMunicao, DevolucaoMunicao, RegistroDisparoMunicao, DevolucaoCPI
from materiais.models import Material
from relatorios.utils import PDFReportGenerator


@login_required
def lista_lotes(request):
    lotes = LoteMunicao.objects.filter(ativo=True).select_related('material').order_by('-data_validade', 'material__nome')
    retiradas_recentes = (
        RetiradaMunicao.objects
        .select_related('material', 'lote', 'policial')
        .order_by('-data_hora')[:15]
    )
    return render(request, 'municoes/lista_lotes.html', {'lotes': lotes, 'retiradas_recentes': retiradas_recentes})


@login_required
def dashboard(request):
    lotes = LoteMunicao.objects.filter(ativo=True).select_related('material')
    devolucoes_cpi_qs = DevolucaoCPI.objects.select_related('lote', 'lote__material')

    totais_lotes = lotes.aggregate(
        cartuchos=Sum('quantidade_atual'),
        estojos=Sum('quantidade_estojos'),
        total_lotes=Count('id'),
    )

    totais_retiradas = RetiradaMunicao.objects.aggregate(total=Sum('quantidade'))
    totais_devolucoes = DevolucaoMunicao.objects.aggregate(total=Sum('quantidade'))
    totais_disparos = RegistroDisparoMunicao.objects.aggregate(
        disparado=Sum('quantidade_disparada'),
        extraviado=Sum('quantidade_extraviada'),
        estojos=Sum('quantidade_estojos'),
    )
    totais_cpi = devolucoes_cpi_qs.aggregate(total=Sum('quantidade'))

    totais_mov = {
        'retirado': totais_retiradas.get('total') or 0,
        'devolvido': totais_devolucoes.get('total') or 0,
        'disparado': totais_disparos.get('disparado') or 0,
        'extraviado': totais_disparos.get('extraviado') or 0,
        'estojos_devolvidos': totais_disparos.get('estojos') or 0,
        'devolvido_cpi': totais_cpi.get('total') or 0,
    }

    # Evita N+1 e iteração pesada: traz poucas retiradas recentes e calcula pendente em Python (lista pequena)
    retiradas_recentes = (
        RetiradaMunicao.objects
        .select_related('material', 'lote', 'policial')
        .order_by('-data_hora')[:40]
    )
    retiradas_pendentes = [r for r in retiradas_recentes if r.quantidade_pendente > 0][:10]

    devolucoes_cpi_recentes = devolucoes_cpi_qs.order_by('-data_hora')[:10]
    lotes_criticos = lotes.order_by('quantidade_atual')[:10]

    return render(request, 'municoes/dashboard.html', {
        'totais_lotes': totais_lotes,
        'totais_mov': totais_mov,
        'retiradas_pendentes': retiradas_pendentes,
        'devolucoes_cpi_recentes': devolucoes_cpi_recentes,
        'lotes_criticos': lotes_criticos,
    })


def _aplicar_filtros_relatorio(form):
    retiradas = RetiradaMunicao.objects.select_related('material', 'lote', 'policial').order_by('-data_hora')
    devolucoes = DevolucaoMunicao.objects.select_related('retirada', 'retirada__material', 'retirada__lote', 'retirada__policial').order_by('-data_hora')
    devolucoes_cpi = DevolucaoCPI.objects.select_related('lote', 'lote__material').order_by('-data_hora')
    registros = RegistroDisparoMunicao.objects.select_related('devolucao', 'devolucao__retirada', 'devolucao__retirada__material')

    if not form.is_valid():
        return retiradas.none(), devolucoes.none(), devolucoes_cpi.none(), registros.none()

    cd = form.cleaned_data
    data_inicio = cd.get('data_inicio')
    data_fim = cd.get('data_fim')
    material = cd.get('material')
    lote = cd.get('lote')
    policial = cd.get('policial')
    tipo_item_cpi = cd.get('tipo_item_cpi')
    somente_extravio = cd.get('somente_com_extravio')
    somente_pendentes = cd.get('somente_pendentes')

    if data_inicio:
        dt_inicio = datetime.combine(data_inicio, time.min)
        retiradas = retiradas.filter(data_hora__gte=dt_inicio)
        devolucoes = devolucoes.filter(data_hora__gte=dt_inicio)
        devolucoes_cpi = devolucoes_cpi.filter(data_hora__gte=dt_inicio)
        registros = registros.filter(data_registro__gte=dt_inicio)
    if data_fim:
        dt_fim = datetime.combine(data_fim, time.max)
        retiradas = retiradas.filter(data_hora__lte=dt_fim)
        devolucoes = devolucoes.filter(data_hora__lte=dt_fim)
        devolucoes_cpi = devolucoes_cpi.filter(data_hora__lte=dt_fim)
        registros = registros.filter(data_registro__lte=dt_fim)

    if material:
        retiradas = retiradas.filter(material=material)
        devolucoes = devolucoes.filter(retirada__material=material)
        devolucoes_cpi = devolucoes_cpi.filter(lote__material=material)
        registros = registros.filter(devolucao__retirada__material=material)
    if lote:
        retiradas = retiradas.filter(lote=lote)
        devolucoes = devolucoes.filter(retirada__lote=lote)
        devolucoes_cpi = devolucoes_cpi.filter(lote=lote)
        registros = registros.filter(devolucao__retirada__lote=lote)
    if policial:
        retiradas = retiradas.filter(policial=policial)
        devolucoes = devolucoes.filter(retirada__policial=policial)
        registros = registros.filter(devolucao__retirada__policial=policial)
    if tipo_item_cpi:
        devolucoes_cpi = devolucoes_cpi.filter(tipo_item=tipo_item_cpi)
    if somente_extravio:
        registros = registros.filter(quantidade_extraviada__gt=0)
        devolucoes = devolucoes.filter(registro_disparo__quantidade_extraviada__gt=0)
    if somente_pendentes:
        retiradas = [r for r in retiradas if r.quantidade_pendente > 0]

    return retiradas, devolucoes, devolucoes_cpi, registros


def _pdf_relatorio_municoes(request, retiradas, devolucoes, devolucoes_cpi, registros):
    buffer = io.BytesIO()
    generator = PDFReportGenerator(buffer=buffer, title='Relatório de Munições', user=request.user)
    styles = generator.styles
    elements = []

    resumo = [
        ['Retiradas', str(len(retiradas))],
        ['Devoluções', str(len(devolucoes))],
        ['Devoluções ao CPI', str(len(devolucoes_cpi))],
        ['Registros com extravio', str(sum(1 for r in registros if r.quantidade_extraviada > 0))],
        ['Total disparado', str(sum(r.quantidade_disparada for r in registros))],
        ['Total estojos', str(sum(r.quantidade_estojos for r in registros))],
        ['Total extraviado', str(sum(r.quantidade_extraviada for r in registros))],
    ]
    elements.append(Paragraph('RESUMO EXECUTIVO', styles['SectionHeader']))
    elements.append(generator.create_table(resumo, col_widths=[8 * cm, 8 * cm]))
    elements.append(Spacer(1, 0.4 * cm))

    linhas_retiradas = [['Data', 'Policial', 'Material', 'Lote', 'Qtd', 'Pendente']]
    for r in list(retiradas)[:50]:
        linhas_retiradas.append([
            r.data_hora.strftime('%d/%m/%Y %H:%M'),
            r.policial.nome,
            r.material.nome,
            r.lote.numero_lote,
            str(r.quantidade),
            str(r.quantidade_pendente),
        ])
    if len(linhas_retiradas) == 1:
        linhas_retiradas.append(['-', '-', '-', '-', '0', '0'])
    elements.append(Paragraph('RETIRADAS (ATÉ 50 REGISTROS)', styles['SectionHeader']))
    elements.append(generator.create_table(linhas_retiradas, col_widths=[2.8 * cm, 4.0 * cm, 4.3 * cm, 2.0 * cm, 1.2 * cm, 1.7 * cm]))
    elements.append(Spacer(1, 0.4 * cm))

    linhas_cpi = [['Data', 'Lote', 'Tipo', 'Qtd', 'Documento']]
    for r in list(devolucoes_cpi)[:50]:
        linhas_cpi.append([
            r.data_hora.strftime('%d/%m/%Y %H:%M'),
            r.lote.numero_lote,
            r.get_tipo_item_display(),
            str(r.quantidade),
            r.documento_referencia or '-',
        ])
    if len(linhas_cpi) == 1:
        linhas_cpi.append(['-', '-', '-', '0', '-'])
    elements.append(Paragraph('DEVOLUÇÕES AO CPI (ATÉ 50 REGISTROS)', styles['SectionHeader']))
    elements.append(generator.create_table(linhas_cpi, col_widths=[2.8 * cm, 2.5 * cm, 3.5 * cm, 1.2 * cm, 6.0 * cm]))

    generator.generate(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="relatorio_municoes.pdf"'
    return response


@login_required
def relatorios(request):
    form = RelatorioMunicoesForm(request.GET or None)
    retiradas, devolucoes, devolucoes_cpi, registros = _aplicar_filtros_relatorio(form)

    if request.GET.get('export') == 'pdf' and form.is_valid():
        return _pdf_relatorio_municoes(request, retiradas, devolucoes, devolucoes_cpi, registros)

    totais_reg = registros.aggregate(
        disparado=Sum('quantidade_disparada'),
        estojos=Sum('quantidade_estojos'),
        extraviado=Sum('quantidade_extraviada'),
    )
    totais_ret = retiradas.aggregate(total=Sum('quantidade')) if hasattr(retiradas, 'aggregate') else {'total': sum(r.quantidade for r in retiradas)}
    totais_dev = devolucoes.aggregate(total=Sum('quantidade'))
    totais_cpi = devolucoes_cpi.aggregate(total=Sum('quantidade'))

    context = {
        'form': form,
        'retiradas': list(retiradas)[:100],
        'devolucoes': list(devolucoes)[:100],
        'devolucoes_cpi': list(devolucoes_cpi)[:100],
        'totais': {
            'retirado': totais_ret.get('total') or 0,
            'devolvido': totais_dev.get('total') or 0,
            'disparado': totais_reg.get('disparado') or 0,
            'estojos': totais_reg.get('estojos') or 0,
            'extraviado': totais_reg.get('extraviado') or 0,
            'devolvido_cpi': totais_cpi.get('total') or 0,
        },
    }
    return render(request, 'municoes/relatorios.html', context)


@login_required
def novo_lote(request):
    if request.method == 'POST':
        form = LoteMunicaoForm(request.POST)
        if form.is_valid():
            lote = form.save()
            messages.success(request, 'Lote de munição criado com sucesso.')
            return redirect('municoes:lista_lotes')
    else:
        form = LoteMunicaoForm()
    return render(request, 'municoes/form_lote.html', {'form': form})


@login_required
@transaction.atomic
def nova_retirada(request):
    if request.method == 'POST':
        form = RetiradaMunicaoForm(request.POST)
        if form.is_valid():
            retirada = form.save(commit=False)
            lote = retirada.lote
            material = retirada.material

            if lote.material != material:
                form.add_error('lote', 'O lote selecionado não pertence ao material informado.')
            elif lote.quantidade_atual < retirada.quantidade:
                form.add_error('quantidade', 'Quantidade maior do que saldo disponível no lote.')
            elif material.tipo != 'MUNICAO':
                form.add_error('material', 'O material precisa ser do tipo Munição.')
            else:
                lote.quantidade_atual -= retirada.quantidade
                lote.save()

                material.quantidade_disponivel -= retirada.quantidade
                material.quantidade_em_uso += retirada.quantidade
                material.save()

                retirada.registrado_por = request.user
                retirada.save()

                messages.success(request, 'Retirada de munição registrada com sucesso.')
                return redirect('municoes:lista_lotes')
    else:
        form = RetiradaMunicaoForm()
    return render(request, 'municoes/form_retirada.html', {'form': form})


@login_required
@transaction.atomic
def nova_devolucao(request):
    if request.method == 'POST':
        form = DevolucaoMunicaoForm(request.POST)
        if form.is_valid():
            devolucao = form.save(commit=False)
            retirada = devolucao.retirada
            material = retirada.material
            lote = retirada.lote
            disparos = form.cleaned_data.get('disparos') or 0
            extravios = form.cleaned_data.get('extravios') or 0
            estojos = form.cleaned_data.get('estojos') or 0
            justificativa = form.cleaned_data.get('justificativa', '').strip()
            sindicancia = form.cleaned_data.get('sindicancia', '').strip()
            boletim = form.cleaned_data.get('boletim_ocorrencia', '').strip()

            if devolucao.quantidade > retirada.quantidade_pendente:
                form.add_error('quantidade', 'A quantidade não pode exceder o pendente da retirada selecionada.')
            elif disparos + extravios > devolucao.quantidade:
                form.add_error('quantidade', 'A soma de disparos e extravios não pode passar da quantidade devolvida.')
            elif estojos > disparos:
                form.add_error('estojos', 'Estojos devolvidos não podem ser maiores que a quantidade disparada.')
            elif (disparos > 0 or extravios > 0) and not justificativa:
                form.add_error('justificativa', 'Informe justificativa quando houver disparos ou extravios.')
            elif extravios > 0 and not sindicancia:
                form.add_error('sindicancia', 'Informe a sindicância/apuração para justificar perda ou extravio.')
            elif disparos > 0 and not boletim:
                form.add_error('boletim_ocorrencia', 'Informe o número do B.O. quando houver disparos.')
            else:
                devolucao.save()
                if disparos > 0 or extravios > 0:
                    RegistroDisparoMunicao.objects.create(
                        devolucao=devolucao,
                        quantidade_disparada=disparos,
                        quantidade_estojos=estojos,
                        quantidade_extraviada=extravios,
                        justificativa=justificativa,
                        sindicancia=sindicancia,
                        boletim_ocorrencia=boletim,
                    )

                lote.quantidade_atual += devolucao.quantidade - (disparos + extravios)
                lote.quantidade_estojos += estojos
                lote.save()

                material.quantidade_disponivel += devolucao.quantidade - (disparos + extravios)
                material.quantidade_em_uso = max(material.quantidade_em_uso - devolucao.quantidade, 0)
                material.save()

                messages.success(request, 'Devolução de munição registrada com sucesso.')
                return redirect('municoes:lista_lotes')
    else:
        form = DevolucaoMunicaoForm()
    return render(request, 'municoes/form_devolucao.html', {'form': form})


@login_required
@transaction.atomic
def devolucao_cpi(request):
    if request.method == 'POST':
        form = DevolucaoCPIForm(request.POST)
        if form.is_valid():
            registro = form.save(commit=False)
            lote = registro.lote
            material = lote.material

            if registro.tipo_item == 'CARTUCHO':
                if registro.quantidade > lote.quantidade_atual:
                    form.add_error('quantidade', 'Quantidade maior que o saldo de cartuchos do lote.')
                else:
                    lote.quantidade_atual -= registro.quantidade
                    material.quantidade_disponivel = max(material.quantidade_disponivel - registro.quantidade, 0)
            else:
                if registro.quantidade > lote.quantidade_estojos:
                    form.add_error('quantidade', 'Quantidade maior que o saldo de estojos em cautela.')
                else:
                    lote.quantidade_estojos -= registro.quantidade

            if form.errors:
                return render(request, 'municoes/form_devolucao_cpi.html', {'form': form})

            registro.registrado_por = request.user
            registro.save()
            lote.save()
            material.save()
            messages.success(request, 'Devolução ao CPI registrada com sucesso.')
            return redirect('municoes:lista_lotes')
    else:
        form = DevolucaoCPIForm()
    return render(request, 'municoes/form_devolucao_cpi.html', {'form': form})


@login_required
def fechamento_retirada_pdf(request, retirada_id):
    retirada = get_object_or_404(
        RetiradaMunicao.objects.select_related('material', 'lote', 'policial', 'registrado_por'),
        pk=retirada_id,
    )
    devolucoes = list(retirada.devolucoes.select_related('registro_disparo').order_by('data_hora'))

    total_devolvido = 0
    total_disparado = 0
    total_estojos = 0
    total_extraviado = 0
    total_intacto = 0

    linhas_devolucao = [['Data/Hora', 'Qtd Devolvida', 'Intactas', 'Disparadas', 'Estojos', 'Extravio']]
    for devolucao in devolucoes:
        registro = getattr(devolucao, 'registro_disparo', None)
        disparado = registro.quantidade_disparada if registro else 0
        estojos = registro.quantidade_estojos if registro else 0
        extraviado = registro.quantidade_extraviada if registro else 0
        intacto = max(devolucao.quantidade - (disparado + extraviado), 0)

        total_devolvido += devolucao.quantidade
        total_disparado += disparado
        total_estojos += estojos
        total_extraviado += extraviado
        total_intacto += intacto

        linhas_devolucao.append([
            devolucao.data_hora.strftime('%d/%m/%Y %H:%M'),
            str(devolucao.quantidade),
            str(intacto),
            str(disparado),
            str(estojos),
            str(extraviado),
        ])

    if len(linhas_devolucao) == 1:
        linhas_devolucao.append(['-', '0', '0', '0', '0', '0'])

    devolucoes_cpi_lote = DevolucaoCPI.objects.filter(lote=retirada.lote).order_by('-data_hora')[:20]
    linhas_cpi = [['Data/Hora', 'Tipo', 'Quantidade', 'Documento']]
    for registro in devolucoes_cpi_lote:
        linhas_cpi.append([
            registro.data_hora.strftime('%d/%m/%Y %H:%M'),
            registro.get_tipo_item_display(),
            str(registro.quantidade),
            registro.documento_referencia or '-',
        ])
    if len(linhas_cpi) == 1:
        linhas_cpi.append(['-', '-', '0', '-'])

    buffer = io.BytesIO()
    generator = PDFReportGenerator(
        buffer=buffer,
        title=f"Fechamento de Munição - Retirada #{retirada.pk}",
        user=request.user,
    )
    styles = generator.styles
    elements = []

    elements.append(Paragraph("DADOS DA RETIRADA", styles['SectionHeader']))
    tabela_retirada = generator.create_table(
        [
            ['Policial', retirada.policial.nome],
            ['Material', retirada.material.nome],
            ['Lote', retirada.lote.numero_lote],
            ['Quantidade Retirada', str(retirada.quantidade)],
            ['Finalidade', retirada.finalidade],
            ['Local de Uso', retirada.local_uso or '-'],
            ['Data da Retirada', retirada.data_hora.strftime('%d/%m/%Y %H:%M')],
        ],
        col_widths=[5 * cm, 11 * cm],
    )
    elements.append(tabela_retirada)
    elements.append(Spacer(1, 0.4 * cm))

    elements.append(Paragraph("CONSOLIDADO DA RETIRADA", styles['SectionHeader']))
    tabela_resumo = generator.create_table(
        [
            ['Total Retirado', str(retirada.quantidade)],
            ['Total Devolvido', str(total_devolvido)],
            ['Saldo Pendente', str(retirada.quantidade_pendente)],
            ['Intactas Devolvidas', str(total_intacto)],
            ['Disparadas', str(total_disparado)],
            ['Estojos Devolvidos', str(total_estojos)],
            ['Extraviadas', str(total_extraviado)],
        ],
        col_widths=[7 * cm, 9 * cm],
    )
    elements.append(tabela_resumo)
    elements.append(Spacer(1, 0.4 * cm))

    elements.append(Paragraph("DETALHAMENTO DAS DEVOLUÇÕES", styles['SectionHeader']))
    elements.append(generator.create_table(
        linhas_devolucao,
        col_widths=[3.2 * cm, 2.2 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm],
    ))
    elements.append(Spacer(1, 0.4 * cm))

    elements.append(Paragraph("DEVOLUÇÕES AO CPI (LOTE RELACIONADO)", styles['SectionHeader']))
    elements.append(generator.create_table(
        linhas_cpi,
        col_widths=[3.6 * cm, 4.0 * cm, 2.2 * cm, 6.2 * cm],
    ))

    generator.generate(elements)
    pdf_content = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="fechamento_retirada_municao_{retirada.pk}.pdf"'
    return response
