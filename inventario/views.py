import openpyxl
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.utils import timezone

from .models import CicloInventario, ItemInventario, ContaContabil
from .forms import ImportarInventarioForm, CicloInventarioForm, ConferenciaItemForm, FiltroInventarioForm
from .services import InventarioExcelImporter
from .reports import gerar_termo_inventario_pdf


@login_required
def dashboard(request):
    ciclos = CicloInventario.objects.all().order_by('-ano', '-semestre', '-criado_em')
    ciclo_atual = ciclos.first()

    totais_gerais = ItemInventario.objects.aggregate(
        total_bens=Count('id'),
        total_valor=Sum('valor'),
        total_conferidos=Count('id', filter=Q(conferido=True)),
        total_exclusao=Count('id', filter=Q(situacao_material__icontains='EXCLUSÃO'))
    )

    contas_resumo = []
    if ciclo_atual:
        contas_resumo = ItemInventario.objects.filter(ciclo=ciclo_atual).values(
            'conta_contabil__codigo',
            'conta_contabil__nome'
        ).annotate(
            qtd=Count('id'),
            valor_total=Sum('valor'),
            conferidos=Count('id', filter=Q(conferido=True))
        ).order_by('conta_contabil__codigo')

    context = {
        'ciclos': ciclos[:5],
        'ciclo_atual': ciclo_atual,
        'totais_gerais': totais_gerais,
        'contas_resumo': contas_resumo,
        'total_contas': ContaContabil.objects.count()
    }
    return render(request, 'inventario/dashboard.html', context)


@login_required
def lista_ciclos(request):
    ciclos = CicloInventario.objects.all().order_by('-ano', '-semestre', '-criado_em')
    return render(request, 'inventario/lista_ciclos.html', {'ciclos': ciclos})


@login_required
def detalhe_ciclo(request, ciclo_id):
    ciclo = get_object_or_404(CicloInventario, pk=ciclo_id)
    form_filtro = FiltroInventarioForm(request.GET or None)

    itens_qs = ItemInventario.objects.filter(ciclo=ciclo).select_related('conta_contabil', 'conferido_por')

    if form_filtro.is_valid():
        busca = form_filtro.cleaned_data.get('busca')
        conta = form_filtro.cleaned_data.get('conta')
        secao = form_filtro.cleaned_data.get('secao')
        conferido = form_filtro.cleaned_data.get('conferido')
        situacao = form_filtro.cleaned_data.get('situacao')

        if busca:
            itens_qs = itens_qs.filter(
                Q(patrimonio__icontains=busca) |
                Q(numero_serie__icontains=busca) |
                Q(tipo_material__icontains=busca)
            )
        if conta:
            itens_qs = itens_qs.filter(conta_contabil=conta)
        if secao:
            itens_qs = itens_qs.filter(secao_subunidade__icontains=secao)
        if conferido == 'SIM':
            itens_qs = itens_qs.filter(conferido=True)
        elif conferido == 'NAO':
            itens_qs = itens_qs.filter(conferido=False)
        if situacao:
            itens_qs = itens_qs.filter(situacao_material__icontains=situacao)

    # Paginação (50 itens por página)
    paginator = Paginator(itens_qs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Estatísticas do ciclo
    estatisticas = {
        'total_itens': ciclo.itens.count(),
        'total_valor': ciclo.itens.aggregate(v=Sum('valor'))['v'] or 0.0,
        'conferidos': ciclo.itens.filter(conferido=True).count(),
        'exclusao': ciclo.itens.filter(situacao_material__icontains='EXCLUSÃO').count(),
    }
    estatisticas['pendentes'] = estatisticas['total_itens'] - estatisticas['conferidos']

    contas_list = ContaContabil.objects.filter(itens__ciclo=ciclo).distinct().order_by('codigo')

    context = {
        'ciclo': ciclo,
        'page_obj': page_obj,
        'form_filtro': form_filtro,
        'estatisticas': estatisticas,
        'contas_list': contas_list,
    }
    return render(request, 'inventario/detalhe_ciclo.html', context)


@login_required
def importar_inventario(request):
    if request.method == 'POST':
        form = ImportarInventarioForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                arquivo = form.cleaned_data['arquivo']
                importer = InventarioExcelImporter(
                    file_path_or_stream=arquivo,
                    titulo=form.cleaned_data['titulo'],
                    ano=form.cleaned_data['ano'],
                    semestre=form.cleaned_data['semestre'],
                    detentor=form.cleaned_data['detentor_executivo'],
                    termo_numero=form.cleaned_data['termo_numero'],
                    user=request.user
                )
                resultado = importer.process()
                ciclo = resultado['ciclo']
                ciclo.arquivo_origem = arquivo
                ciclo.save()

                messages.success(
                    request,
                    f"Inventário importado com sucesso! {resultado['total_itens']} itens de patrimônio "
                    f"carregados (Total R$ {resultado['valor_total']:,.2f})."
                )
                return redirect('inventario:detalhe_ciclo', ciclo_id=ciclo.id)
            except Exception as e:
                messages.error(request, f"Erro ao processar o arquivo Excel: {str(e)}")
    else:
        form = ImportarInventarioForm()

    return render(request, 'inventario/importar.html', {'form': form})


@login_required
def novo_ciclo(request):
    if request.method == 'POST':
        form = CicloInventarioForm(request.POST)
        if form.is_valid():
            ciclo = form.save(commit=False)
            ciclo.criado_por = request.user
            ciclo.save()
            messages.success(request, 'Ciclo de Inventário criado com sucesso.')
            return redirect('inventario:detalhe_ciclo', ciclo_id=ciclo.id)
    else:
        form = CicloInventarioForm()
    return render(request, 'inventario/form_ciclo.html', {'form': form, 'titulo_pagina': 'Novo Inventário Semestral'})


@login_required
def conferir_item(request, item_id):
    item = get_object_or_404(ItemInventario, pk=item_id)
    
    if request.method == 'POST':
        conferido = request.POST.get('conferido') == 'true' or request.POST.get('conferido') == '1' or 'conferido' in request.POST
        situacao_fisica = request.POST.get('situacao_fisica_conferida', 'CONFORME')
        obs = request.POST.get('observacoes_conferencia', '').strip()

        item.conferido = conferido
        item.situacao_fisica_conferida = situacao_fisica
        item.observacoes_conferencia = obs
        item.data_conferencia = timezone.now() if conferido else None
        item.conferido_por = request.user if conferido else None
        item.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'item_id': item.id,
                'conferido': item.conferido,
                'progresso': item.ciclo.progresso_conferencia,
                'total_conferidos': item.ciclo.total_conferidos
            })

        messages.success(request, f"Status de conferência do patrimônio {item.patrimonio} atualizado.")
        return redirect('inventario:detalhe_ciclo', ciclo_id=item.ciclo.id)

    return JsonResponse({'error': 'Método inválido'}, status=400)


@login_required
def conferir_lote(request, ciclo_id):
    ciclo = get_object_or_404(CicloInventario, pk=ciclo_id)
    if request.method == 'POST':
        acao = request.POST.get('acao')
        if acao == 'MARCAR_TODOS':
            ciclo.itens.update(
                conferido=True,
                data_conferencia=timezone.now(),
                conferido_por=request.user
            )
            messages.success(request, 'Todos os itens deste inventário foram marcados como conferidos.')
        elif acao == 'DESMARCAR_TODOS':
            ciclo.itens.update(
                conferido=False,
                data_conferencia=None,
                conferido_por=None
            )
            messages.info(request, 'Status de conferência reiniciado.')
            
    return redirect('inventario:detalhe_ciclo', ciclo_id=ciclo.id)


@login_required
def termo_pdf(request, ciclo_id):
    return gerar_termo_inventario_pdf(request, ciclo_id)


@login_required
def exportar_excel(request, ciclo_id):
    ciclo = get_object_or_404(CicloInventario, pk=ciclo_id)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventário"

    headers = [
        "Conta Contábil", "Descrição da Conta", "Seção / Subunidade",
        "Patrimônio", "Nº de Série", "Descrição do Material",
        "Situação do Material", "Valor (R$)", "Conferido Físico", "Situação Conferida"
    ]
    ws.append(headers)

    for item in ciclo.itens.select_related('conta_contabil').all():
        ws.append([
            item.conta_contabil.codigo if item.conta_contabil else '',
            item.conta_contabil.nome if item.conta_contabil else '',
            item.secao_subunidade,
            item.patrimonio,
            item.numero_serie or '',
            item.tipo_material,
            item.situacao_material,
            float(item.valor),
            'SIM' if item.conferido else 'NÃO',
            item.get_situacao_fisica_conferida_display()
        ])

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    response = HttpResponse(
        stream.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="inventario_{ciclo.termo_numero}.xlsx"'
    return response
