from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg, F
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from decimal import Decimal
from datetime import timedelta

from .models import (
    MarcaViatura, ModeloViatura, Viatura, DespachoViatura, Abastecimento,
    Manutencao, Oficina, ChecklistViatura, SolicitacaoBaixaViatura,
    PecaViatura, RetiradaPeca, EvidenciaManutencao, PlanoManutencaoPreventiva,
    RetiradaPecaItem, ServicoManutencao
)
from .forms import (
    ViaturaForm, DespachoSaidaForm, DespachoRetornoForm,
    AbastecimentoForm, ManutencaoForm, AgendamentoManutencaoForm, MarcaViaturaForm,
    ModeloViaturaForm, OficinaForm, ImportarFrotaForm, ChecklistViaturaForm,
    SolicitacaoBaixaViaturaForm, AnaliseBaixaViaturaForm,
    PecaViaturaForm, RetiradaPecaForm, RetiradaPecaItemFormSet, AnexarReciboRetiradaForm,
    ConcluirManutencaoForm, CancelarManutencaoForm, EvidenciaManutencaoForm,
    PlanoManutencaoPreventivaForm, ServicoManutencaoForm,
)
from reserva_baep.decorators import require_module_permission
from .services.manutencao_historico import (
    registrar_abertura,
    registrar_alteracoes_form,
    registrar_cancelamento,
    registrar_conclusao,
    registrar_evidencia,
    registrar_servico,
    garantir_historico_estruturado,
)

import xml.etree.ElementTree as ET
import pandas as pd
from django.db import transaction
import io

FROTA_GROUPS = ['frota', 'reserva_armas']  # grupos com acesso ao módulo


def _has_frota_permission(user):
    """Verifica se o usuário tem acesso ao módulo de frota."""
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=FROTA_GROUPS).exists()


# =============================================================================
# DASHBOARD FROTA
# =============================================================================

@login_required
@require_module_permission('frota')
def dashboard_frota(request):
    total = Viatura.objects.count()
    disponiveis = Viatura.objects.filter(status='DISPONIVEL').count()
    em_uso = Viatura.objects.filter(status='EM_USO').count()
    manutencao = Viatura.objects.filter(status='MANUTENCAO').count()
    baixadas = Viatura.objects.filter(status='BAIXADA').count()

    # Por tipo
    por_tipo = (
        Viatura.objects
        .values('modelo__tipo', 'modelo__tipo')
        .annotate(total=Count('id'))
        .order_by('modelo__tipo')
    )

    # Despachos ativos (sem retorno)
    despachos_ativos = DespachoViatura.objects.filter(data_retorno__isnull=True).select_related(
        'viatura', 'motorista', 'encarregado'
    ).order_by('-data_saida')

    # Manutenções em aberto
    manutencoes_abertas = Manutencao.objects.filter(status__in=['ABERTA', 'AGUARDANDO_PECA']).select_related('viatura')

    # Agendamentos futuros
    hoje = timezone.now().date()
    agendamentos = Manutencao.objects.filter(status='AGENDADA').select_related('viatura', 'oficina_fk').order_by('data_inicio')
    agendamentos_atrasados = agendamentos.filter(data_inicio__lt=hoje).count()

    # Últimos abastecimentos
    ultimos_abastecimentos = Abastecimento.objects.select_related('viatura', 'motorista').order_by('-data_abastecimento')[:5]

    # Dados de Peças
    pecas_estoque_baixo = PecaViatura.objects.filter(quantidade_estoque__lte=F('limite_minimo'), ativo=True).count()
    ultimas_retiradas = RetiradaPeca.objects.select_related('viatura').order_by('-data_retirada')[:5]

    # =========================================================================
    # ALERTAS INTELIGENTES (Fase 3)
    # =========================================================================
    limite_garantia = hoje + timedelta(days=30)
    
    # Garantias vencendo nos próximos 30 dias
    garantias_vencendo = Manutencao.objects.filter(
        status='CONCLUIDA',
        data_validade_garantia__isnull=False,
        data_validade_garantia__lte=limite_garantia,
        data_validade_garantia__gte=hoje
    ).select_related('viatura').order_by('data_validade_garantia')[:10]
    
    # Garantias já vencidas (últimos 60 dias) sem nova manutenção
    garantias_vencidas = Manutencao.objects.filter(
        status='CONCLUIDA',
        data_validade_garantia__isnull=False,
        data_validade_garantia__lt=hoje,
        data_validade_garantia__gte=hoje - timedelta(days=60)
    ).select_related('viatura').count()
    
    # Manutenções abertas há mais de 30 dias sem conclusão
    limite_longa = hoje - timedelta(days=30)
    manutencoes_longas = Manutencao.objects.filter(
        status__in=['ABERTA', 'AGUARDANDO_PECA'],
        data_inicio__lte=limite_longa
    ).select_related('viatura').order_by('data_inicio')[:10]
    
    # Alertas de manutenção preventiva (baseado em PlanoManutencaoPreventiva)
    alertas_preventivas = []
    planos_ativos = PlanoManutencaoPreventiva.objects.filter(ativo=True).select_related('modelo')
    for plano in planos_ativos:
        viaturas_plano = Viatura.objects.filter(
            modelo=plano.modelo,
            status__in=['DISPONIVEL', 'EM_USO']
        )
        for vtr in viaturas_plano:
            ultima_prev = Manutencao.objects.filter(
                viatura=vtr, tipo='PREVENTIVA', status='CONCLUIDA',
                descricao__icontains=plano.descricao[:30]
            ).order_by('-data_conclusao').first()
            
            alerta = False
            motivo = ''
            if plano.intervalo_km and ultima_prev:
                km_desde = vtr.odometro_atual - ultima_prev.odometro
                if km_desde >= Decimal(str(plano.intervalo_km)):
                    alerta = True
                    motivo = f'{km_desde:,.0f} km desde a última ({plano.descricao})'
            if plano.intervalo_dias and ultima_prev and ultima_prev.data_conclusao:
                dias_desde = (hoje - ultima_prev.data_conclusao).days
                if dias_desde >= plano.intervalo_dias:
                    alerta = True
                    motivo = f'{dias_desde} dias desde a última ({plano.descricao})'
            if not ultima_prev and (plano.intervalo_km or plano.intervalo_dias):
                alerta = True
                motivo = f'Nunca realizou: {plano.descricao}'
            
            if alerta:
                alertas_preventivas.append({
                    'viatura': vtr,
                    'plano': plano,
                    'motivo': motivo
                })
    
    # =========================================================================
    # KPIs DE FROTA (Fase 4)
    # =========================================================================
    manutencoes_concluidas = Manutencao.objects.filter(status='CONCLUIDA')
    
    # Custo total e médio de manutenções
    total_custos = manutencoes_concluidas.aggregate(
        total_pecas=Sum('custo_pecas'),
        total_mao_obra=Sum('custo_mao_obra'),
        total_registros=Count('id')
    )
    custo_total_frota = (total_custos['total_pecas'] or Decimal('0')) + (total_custos['total_mao_obra'] or Decimal('0'))
    custo_medio = custo_total_frota / total_custos['total_registros'] if total_custos['total_registros'] else Decimal('0')
    
    # Tempo médio em oficina (dias)
    manut_com_datas = manutencoes_concluidas.filter(data_conclusao__isnull=False)
    tempos = []
    for m in manut_com_datas:
        if m.data_conclusao and m.data_inicio:
            dias = (m.data_conclusao - m.data_inicio).days
            tempos.append(dias)
    tempo_medio_oficina = sum(tempos) / len(tempos) if tempos else 0
    
    # Top 5 viaturas mais custosas
    top_viaturas_custo = (
        Viatura.objects
        .annotate(
            custo_manut=Sum('manutencoes__custo_pecas') + Sum('manutencoes__custo_mao_obra')
        )
        .filter(custo_manut__gt=0)
        .order_by('-custo_manut')[:5]
    )

    context = {
        'total': total,
        'disponiveis': disponiveis,
        'em_uso': em_uso,
        'manutencao': manutencao,
        'baixadas': baixadas,
        'por_tipo': por_tipo,
        'despachos_ativos': despachos_ativos,
        'manutencoes_abertas': manutencoes_abertas,
        'ultimos_abastecimentos': ultimos_abastecimentos,
        'agendamentos': agendamentos,
        'agendamentos_atrasados': agendamentos_atrasados,
        'hoje': hoje,
        'pecas_estoque_baixo': pecas_estoque_baixo,
        'ultimas_retiradas': ultimas_retiradas,
        # Alertas (Fase 3)
        'garantias_vencendo': garantias_vencendo,
        'garantias_vencidas': garantias_vencidas,
        'manutencoes_longas': manutencoes_longas,
        'alertas_preventivas': alertas_preventivas[:10],
        # KPIs (Fase 4)
        'custo_total_frota': custo_total_frota,
        'custo_medio': custo_medio,
        'tempo_medio_oficina': tempo_medio_oficina,
        'total_manutencoes_concluidas': total_custos['total_registros'] or 0,
        'top_viaturas_custo': top_viaturas_custo,
    }
    return render(request, 'viaturas/dashboard.html', context)


# =============================================================================
# VIATURAS (CRUD)
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_viaturas(request):
    qs = Viatura.objects.select_related('modelo', 'modelo__marca').all()
    tipo = request.GET.get('tipo')
    status = request.GET.get('status')
    q = request.GET.get('q')

    if tipo:
        qs = qs.filter(modelo__tipo=tipo)
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(prefixo__icontains=q) |
            Q(placa__icontains=q) |
            Q(chassi__icontains=q) |
            Q(modelo__nome__icontains=q) |
            Q(modelo__marca__nome__icontains=q)
        )

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    modelos_tipo = ModeloViatura.TIPO_CHOICES

    return render(request, 'viaturas/lista_viaturas.html', {
        'page_obj': page,
        'tipo_filtro': tipo,
        'status_filtro': status,
        'q': q,
        'tipos_choices': modelos_tipo,
        'status_choices': Viatura.STATUS_CHOICES,
    })


@login_required
@require_module_permission('frota')
def criar_viatura(request):
    if request.method == 'POST':
        form = ViaturaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Viatura cadastrada com sucesso!')
            return redirect('viaturas:lista_viaturas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ViaturaForm()
    return render(request, 'viaturas/form_viatura.html', {'form': form, 'titulo': 'Nova Viatura'})


@login_required
@require_module_permission('frota')
def editar_viatura(request, pk):
    viatura = get_object_or_404(Viatura, pk=pk)
    if request.method == 'POST':
        form = ViaturaForm(request.POST, instance=viatura)
        if form.is_valid():
            form.save()
            messages.success(request, f'Viatura {viatura.prefixo} atualizada!')
            return redirect('viaturas:detalhe_viatura', pk=pk)
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ViaturaForm(instance=viatura)
    return render(request, 'viaturas/form_viatura.html', {'form': form, 'titulo': f'Editar {viatura.prefixo}', 'viatura': viatura})


@login_required
@require_module_permission('frota')
def detalhe_viatura(request, pk):
    viatura = get_object_or_404(Viatura.objects.select_related('modelo', 'modelo__marca'), pk=pk)
    despachos = viatura.despachos.select_related('motorista', 'encarregado', 'registrado_por').order_by('-data_saida')[:10]
    abastecimentos = viatura.abastecimentos.select_related('motorista').order_by('-data_abastecimento')[:10]
    manutencoes = viatura.manutencoes.order_by('-data_inicio')
    despacho_ativo = viatura.despachos.filter(data_retorno__isnull=True).first()

    # Totais
    total_km_rodado = (
        viatura.despachos.filter(km_retorno__isnull=False)
        .aggregate(total=Sum('km_retorno') - Sum('km_saida'))['total'] or Decimal('0')
    )
    total_combustivel = viatura.abastecimentos.aggregate(total=Sum('quantidade_litros'))['total'] or Decimal('0')
    custo_total_manutencao = sum(m.custo_total for m in viatura.manutencoes.all())

    # 1. Total Manutenções
    total_manutencoes = manutencoes.count()
    concluidas_count = manutencoes.filter(status='CONCLUIDA').count()
    preventivas_count = manutencoes.filter(tipo='PREVENTIVA').count()
    corretivas_count = manutencoes.filter(tipo='CORRETIVA').count()

    # 2. Total Peças Trocadas (Almoxarifado)
    pecas_qs = RetiradaPecaItem.objects.filter(retirada__viatura=viatura).select_related('peca', 'retirada', 'retirada__policial').order_by('-retirada__data_retirada')
    total_pecas_trocadas = pecas_qs.aggregate(total=Sum('quantidade'))['total'] or 0

    # 3. Listar Manutenções com tempo de duração do serviço
    manutencoes_calculadas = []
    for m in manutencoes:
        duracao_dias = None
        if m.status == 'CONCLUIDA' and m.data_conclusao:
            duracao_dias = (m.data_conclusao - m.data_inicio).days
        manutencoes_calculadas.append({
            'obj': m,
            'duracao_dias': duracao_dias,
            'custo_total': m.custo_total
        })

    # 4. Encontrar ocorrências por serviço ou peça recorrente
    ocorrencias_por_item = {}

    # Ocorrências de peças estruturadas
    for p_item in pecas_qs:
        nome_peca = p_item.peca.nome
        if nome_peca not in ocorrencias_por_item:
            ocorrencias_por_item[nome_peca] = []
        
        km = None
        manut_vinculada = p_item.retirada.manutencao_vinculada.first()
        if manut_vinculada:
            km = manut_vinculada.odometro
        
        ocorrencias_por_item[nome_peca].append({
            'data': p_item.retirada.data_retirada.date(),
            'odometro': km or Decimal('0'),
            'origem': 'Peça (Almoxarifado)'
        })

    # Ocorrências de serviços de oficina
    servicos_qs = ServicoManutencao.objects.filter(
        manutencao__viatura=viatura, 
        manutencao__status='CONCLUIDA'
    ).select_related('manutencao').order_by('manutencao__data_conclusao')
    
    for s in servicos_qs:
        desc = s.descricao
        match_grupo = None
        desc_lower = desc.lower()
        if 'óleo' in desc_lower or 'oleo' in desc_lower:
            match_grupo = 'Troca de Óleo'
        elif 'pastilha' in desc_lower or 'freio' in desc_lower:
            match_grupo = 'Pastilhas de Freio'
        elif 'pneu' in desc_lower:
            match_grupo = 'Troca/Alinhamento de Pneus'
        elif 'bateria' in desc_lower:
            match_grupo = 'Troca de Bateria'
        elif 'filtro' in desc_lower:
            match_grupo = 'Troca de Filtros'
        elif 'bieleta' in desc_lower or 'suspensão' in desc_lower or 'suspensao' in desc_lower:
            match_grupo = 'Manutenção de Suspensão/Bieleta'
        else:
            match_grupo = desc.title()

        if match_grupo not in ocorrencias_por_item:
            ocorrencias_por_item[match_grupo] = []
            
        ocorrencias_por_item[match_grupo].append({
            'data': s.manutencao.data_conclusao or s.manutencao.data_inicio,
            'odometro': s.odometro or s.manutencao.odometro or Decimal('0'),
            'origem': 'Serviço (Oficina)'
        })

    # Planos preventivos oficiais
    planos_preventivos = PlanoManutencaoPreventiva.objects.filter(modelo=viatura.modelo, ativo=True)
    planos_mapeados = {}
    for p in planos_preventivos:
        planos_mapeados[p.descricao] = p

    # Garantir que todos os planos preventivos apareçam mesmo que nunca tenham sido feitos
    for desc_plano, plano in planos_mapeados.items():
        if desc_plano not in ocorrencias_por_item:
            ocorrencias_por_item[desc_plano] = []

    # Processamos cada item
    analise_preventiva = []
    
    for item_nome, ocorrencias in ocorrencias_por_item.items():
        ocorrencias = sorted(ocorrencias, key=lambda x: x['data'])
        plano = planos_mapeados.get(item_nome)
        
        media_dias = None
        media_km = None
        
        if len(ocorrencias) >= 2:
            diferencas_dias = []
            diferencas_km = []
            for i in range(len(ocorrencias) - 1):
                dias = (ocorrencias[i+1]['data'] - ocorrencias[i]['data']).days
                diferencas_dias.append(dias)
                
                km_diff = ocorrencias[i+1]['odometro'] - ocorrencias[i]['odometro']
                if km_diff > 0:
                    diferencas_km.append(km_diff)
            
            if diferencas_dias:
                media_dias = int(sum(diferencas_dias) / len(diferencas_dias))
            if diferencas_km:
                media_km = int(sum(diferencas_km) / len(diferencas_km))

        ultima_data = None
        ultimo_km = None
        if ocorrencias:
            ultima_data = ocorrencias[-1]['data']
            ultimo_km = ocorrencias[-1]['odometro']
        else:
            ultima_data = viatura.data_cadastro.date()
            ultimo_km = Decimal('0')

        intervalo_dias_ref = 180
        intervalo_km_ref = 10000

        if plano:
            if plano.intervalo_dias:
                intervalo_dias_ref = plano.intervalo_dias
            elif media_dias:
                intervalo_dias_ref = media_dias
                
            if plano.intervalo_km:
                intervalo_km_ref = plano.intervalo_km
            elif media_km:
                intervalo_km_ref = media_km
        else:
            if media_dias:
                intervalo_dias_ref = media_dias
            if media_km:
                intervalo_km_ref = media_km

        proxima_data = ultima_data + timedelta(days=intervalo_dias_ref)
        proximo_km = ultimo_km + Decimal(str(intervalo_km_ref))

        hoje = timezone.now().date()
        restante_dias = (proxima_data - hoje).days
        restante_km = float(proximo_km - viatura.odometro_atual)

        if restante_dias < 0 or restante_km < 0:
            status_prev = 'ATRASADO'
        elif restante_dias <= 15 or restante_km <= 500:
            status_prev = 'ALERTA'
        else:
            status_prev = 'OK'

        analise_preventiva.append({
            'nome': item_nome,
            'plano_vinculado': plano,
            'historico_count': len(ocorrencias),
            'ultima_data': ocorrencias[-1]['data'] if ocorrencias else None,
            'ultimo_km': ocorrencias[-1]['odometro'] if ocorrencias else None,
            'media_dias_duracao': media_dias,
            'media_km_duracao': media_km,
            'proxima_data': proxima_data,
            'proximo_km': proximo_km,
            'restante_dias': restante_dias,
            'restante_km': restante_km,
            'status_prev': status_prev,
            'recorrente': len(ocorrencias) >= 2 or plano is not None
        })

    # Filtrar para exibir itens recorrentes ou com plano vinculado
    analise_preventiva = [item for item in analise_preventiva if item['recorrente']]

    return render(request, 'viaturas/detalhe_viatura.html', {
        'viatura': viatura,
        'despachos': despachos,
        'abastecimentos': abastecimentos,
        'manutencoes': manutencoes[:10],
        'manutencoes_calculadas': manutencoes_calculadas,
        'despacho_ativo': despacho_ativo,
        'total_km_rodado': total_km_rodado,
        'total_combustivel': total_combustivel,
        'custo_total_manutencao': custo_total_manutencao,
        
        # Novos indicadores inteligentes
        'total_manutencoes': total_manutencoes,
        'concluidas_count': concluidas_count,
        'preventivas_count': preventivas_count,
        'corretivas_count': corretivas_count,
        'total_pecas_trocadas': total_pecas_trocadas,
        'pecas_detalhadas': pecas_qs,
        'analise_preventiva': analise_preventiva,
    })


# =============================================================================
# DESPACHO (SAÍDA / RETORNO)
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_despachos(request):
    qs = DespachoViatura.objects.select_related('viatura', 'motorista', 'encarregado', 'registrado_por').order_by('-data_saida')
    status = request.GET.get('status', 'ativos')

    if status == 'ativos':
        qs = qs.filter(data_retorno__isnull=True)
    elif status == 'concluidos':
        qs = qs.filter(data_retorno__isnull=False)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_despachos.html', {'page_obj': page, 'status_filtro': status})


@login_required
@require_module_permission('frota')
def criar_despacho(request):
    if request.method == 'POST':
        form = DespachoSaidaForm(request.POST)
        if form.is_valid():
            despacho = form.save(commit=False)
            despacho.registrado_por = request.user
            despacho.save()
            # Atualiza status da viatura
            despacho.viatura.status = 'EM_USO'
            despacho.viatura.save()
            messages.success(request, f'Saída da viatura {despacho.viatura.prefixo} registrada!')
            return redirect('viaturas:lista_despachos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = DespachoSaidaForm()
    return render(request, 'viaturas/form_despacho.html', {'form': form, 'titulo': 'Registrar Saída (Serviço Adm.)'})


@login_required
@require_module_permission('frota')
def retorno_despacho(request, pk):
    despacho = get_object_or_404(DespachoViatura, pk=pk, data_retorno__isnull=True)
    if request.method == 'POST':
        form = DespachoRetornoForm(request.POST, instance=despacho)
        if form.is_valid():
            d = form.save(commit=False)
            d.data_retorno = timezone.now()
            d.save()
            # Atualiza odômetro e status da viatura
            viatura = despacho.viatura
            if d.km_retorno:
                viatura.odometro_atual = d.km_retorno
            viatura.status = 'DISPONIVEL'
            viatura.save()
            messages.success(request, f'Retorno da viatura {viatura.prefixo} registrado!')
            return redirect('viaturas:lista_despachos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = DespachoRetornoForm()
    return render(request, 'viaturas/form_retorno.html', {'form': form, 'despacho': despacho})


# =============================================================================
# ABASTECIMENTOS
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_abastecimentos(request):
    qs = Abastecimento.objects.select_related('viatura', 'motorista').order_by('-data_abastecimento')
    viatura_id = request.GET.get('viatura')
    if viatura_id:
        qs = qs.filter(viatura_id=viatura_id)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    viaturas = Viatura.objects.all()
    return render(request, 'viaturas/lista_abastecimentos.html', {
        'page_obj': page, 'viaturas': viaturas, 'viatura_filtro': viatura_id
    })


@login_required
@require_module_permission('frota')
def criar_abastecimento(request):
    if request.method == 'POST':
        form = AbastecimentoForm(request.POST)
        if form.is_valid():
            ab = form.save(commit=False)
            ab.registrado_por = request.user
            ab.save()
            # Atualiza odometro
            if ab.odometro > ab.viatura.odometro_atual:
                ab.viatura.odometro_atual = ab.odometro
                ab.viatura.save()
            messages.success(request, 'Abastecimento registrado com sucesso!')
            return redirect('viaturas:lista_abastecimentos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = AbastecimentoForm()
    return render(request, 'viaturas/form_abastecimento.html', {'form': form, 'titulo': 'Registrar Abastecimento'})


# =============================================================================
# MANUTENÇÕES
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_manutencoes(request):
    qs = Manutencao.objects.select_related('viatura', 'oficina_fk').order_by('-data_inicio')
    status = request.GET.get('status', 'abertas')
    if status == 'abertas':
        qs = qs.filter(status__in=['ABERTA', 'AGUARDANDO_PECA'])
    elif status == 'concluidas':
        qs = qs.filter(status__in=['CONCLUIDA', 'CANCELADA'])
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_manutencoes.html', {'page_obj': page, 'status_filtro': status})


@login_required
@require_module_permission('frota')
def detalhe_manutencao(request, pk):
    man = get_object_or_404(
        Manutencao.objects.select_related('viatura', 'oficina_fk', 'registrado_por')
        .prefetch_related('servicos__registrado_por'),
        pk=pk,
    )
    garantir_historico_estruturado(man)
    man = (
        Manutencao.objects
        .select_related('viatura', 'oficina_fk', 'registrado_por')
        .prefetch_related('servicos__registrado_por')
        .get(pk=pk)
    )
    return render(request, 'viaturas/detalhe_manutencao.html', {
        'manutencao': man,
        'servicos': man.servicos.all(),
    })


@login_required
@require_module_permission('frota')
def concluir_manutencao(request, pk):
    """Conclui uma manutenção com formulário de aprovação (POST obrigatório)."""
    man = get_object_or_404(Manutencao, pk=pk)
    
    if man.status not in ['ABERTA', 'AGUARDANDO_PECA']:
        messages.warning(request, 'Esta manutenção não pode ser concluída no status atual.')
        return redirect('viaturas:detalhe_manutencao', pk=pk)
    
    if request.method == 'POST':
        instancia_anterior = Manutencao.objects.get(pk=man.pk)
        form = ConcluirManutencaoForm(request.POST, request.FILES, instance=man)
        if form.is_valid():
            man = form.save(commit=False)
            man.data_conclusao = timezone.now().date()
            man.status = 'CONCLUIDA'
            man.aprovado_por = request.user
            man.data_aprovacao = timezone.now()
            man.save()
            registrar_alteracoes_form(man, request.user, instancia_anterior)
            registrar_conclusao(man, request.user)
            
            messages.success(request, f'Manutenção da viatura {man.viatura.prefixo} concluída e aprovada!')
            return redirect('viaturas:detalhe_manutencao', pk=pk)
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ConcluirManutencaoForm(instance=man)
    
    return render(request, 'viaturas/form_concluir_manutencao.html', {
        'form': form, 'manutencao': man
    })


@login_required
@require_module_permission('frota')
def criar_manutencao(request):
    if request.method == 'POST':
        form = ManutencaoForm(request.POST, request.FILES)
        if form.is_valid():
            man = form.save(commit=False)
            man.registrado_por = request.user
            man.save() # O método save do modelo Manutencao atualiza o status e a localização da viatura automaticamente
            registrar_abertura(man, request.user)
            
            # Atualiza localização escolhida na tela
            local = form.cleaned_data.get('localizacao_fisica')
            if local and man.viatura.localizacao != local:
                man.viatura.localizacao = local
                man.viatura.save(update_fields=['localizacao'])
            
            messages.success(request, 'Manutenção registrada com sucesso!')
            return redirect('viaturas:lista_manutencoes')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ManutencaoForm()
    return render(request, 'viaturas/form_manutencao.html', {'form': form, 'titulo': 'Registrar Manutenção'})


@login_required
@require_module_permission('frota')
def editar_manutencao(request, pk):
    man = get_object_or_404(Manutencao, pk=pk)
    if request.method == 'POST':
        instancia_anterior = Manutencao.objects.get(pk=pk)
        form = ManutencaoForm(request.POST, request.FILES, instance=man)
        if form.is_valid():
            m = form.save() # O método save do modelo Manutencao atualiza o status e a localização da viatura automaticamente
            registrar_alteracoes_form(m, request.user, instancia_anterior)
            
            # Atualiza localização escolhida na tela
            local = form.cleaned_data.get('localizacao_fisica')
            if local and m.viatura.localizacao != local:
                m.viatura.localizacao = local
                m.viatura.save(update_fields=['localizacao'])
            
            messages.success(request, 'Manutenção atualizada!')
            return redirect('viaturas:lista_manutencoes')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ManutencaoForm(instance=man)
    return render(request, 'viaturas/form_manutencao.html', {'form': form, 'titulo': 'Editar Manutenção', 'manutencao': man})

# =============================================================================
# AGENDAMENTOS DE MANUTENÇÃO
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_agendamentos(request):
    from django.utils import timezone as tz
    hoje = tz.now().date()
    qs = Manutencao.objects.select_related('viatura', 'oficina_fk').filter(status='AGENDADA').order_by('data_inicio')
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_agendamentos.html', {'page_obj': page, 'hoje': hoje})


@login_required
@require_module_permission('frota')
def criar_agendamento(request):
    if request.method == 'POST':
        form = AgendamentoManutencaoForm(request.POST)
        if form.is_valid():
            agend = form.save(commit=False)
            agend.status = 'AGENDADA'
            agend.odometro = agend.viatura.odometro_atual  # usa odometro atual como referência
            agend.registrado_por = request.user
            agend.save()
            registrar_abertura(agend, request.user)
            messages.success(request, f'Agendamento registrado para {agend.viatura.prefixo} em {agend.data_inicio.strftime("%d/%m/%Y")}!')
            return redirect('viaturas:lista_agendamentos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = AgendamentoManutencaoForm()
    return render(request, 'viaturas/form_agendamento.html', {'form': form, 'titulo': 'Novo Agendamento'})


@login_required
@require_module_permission('frota')
def converter_agendamento(request, pk):
    """Converte um agendamento em manutenção ativa (Em Aberto)."""
    agend = get_object_or_404(Manutencao, pk=pk, status='AGENDADA')
    instancia_anterior = Manutencao.objects.get(pk=agend.pk)
    agend.status = 'ABERTA'
    agend.data_inicio = timezone.now().date()
    agend.save()
    registrar_alteracoes_form(agend, request.user, instancia_anterior)
    messages.success(request, f'Agendamento da viatura {agend.viatura.prefixo} iniciado como manutenção Em Aberto!')
    return redirect('viaturas:lista_manutencoes')


@login_required
@require_module_permission('frota')
def cancelar_agendamento(request, pk):
    """Cancela um agendamento com justificativa obrigatória (POST)."""
    agend = get_object_or_404(Manutencao, pk=pk, status='AGENDADA')
    
    if request.method == 'POST':
        form = CancelarManutencaoForm(request.POST, instance=agend)
        if form.is_valid():
            man = form.save(commit=False)
            man.status = 'CANCELADA'
            man.cancelado_por = request.user
            man.data_cancelamento = timezone.now()
            man.save()
            registrar_cancelamento(man, request.user, man.motivo_cancelamento or '')
            messages.warning(request, f'Agendamento da viatura {agend.viatura.prefixo} cancelado.')
            return redirect('viaturas:lista_agendamentos')
        messages.error(request, 'Informe o motivo do cancelamento.')
    else:
        form = CancelarManutencaoForm(instance=agend)
    
    return render(request, 'viaturas/form_cancelar_manutencao.html', {
        'form': form, 'manutencao': agend, 'titulo': 'Cancelar Agendamento'
    })


# =============================================================================
# MARCAS E MODELOS (AUXILIARES)
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_marcas(request):
    qs = MarcaViatura.objects.annotate(count_modelos=Count('modelos')).all()
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_marcas.html', {'page_obj': page})


@login_required
@require_module_permission('frota')
def criar_marca(request):
    if request.method == 'POST':
        form = MarcaViaturaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Marca cadastrada com sucesso!')
            return redirect('viaturas:lista_marcas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = MarcaViaturaForm()
    return render(request, 'viaturas/form_marca.html', {'form': form, 'titulo': 'Nova Marca'})


@login_required
@require_module_permission('frota')
def editar_marca(request, pk):
    marca = get_object_or_404(MarcaViatura, pk=pk)
    if request.method == 'POST':
        form = MarcaViaturaForm(request.POST, instance=marca)
        if form.is_valid():
            form.save()
            messages.success(request, f'Marca {marca.nome} atualizada!')
            return redirect('viaturas:lista_marcas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = MarcaViaturaForm(instance=marca)
    return render(request, 'viaturas/form_marca.html', {'form': form, 'titulo': f'Editar {marca.nome}'})


@login_required
@require_module_permission('frota')
def lista_modelos(request):
    qs = ModeloViatura.objects.select_related('marca').annotate(count_viaturas=Count('viaturas')).all()
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_modelos.html', {'page_obj': page})


@login_required
@require_module_permission('frota')
def criar_modelo(request):
    if request.method == 'POST':
        form = ModeloViaturaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Modelo cadastrado com sucesso!')
            return redirect('viaturas:lista_modelos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ModeloViaturaForm()
    return render(request, 'viaturas/form_modelo.html', {'form': form, 'titulo': 'Novo Modelo'})


@login_required
@require_module_permission('frota')
def editar_modelo(request, pk):
    modelo = get_object_or_404(ModeloViatura, pk=pk)
    if request.method == 'POST':
        form = ModeloViaturaForm(request.POST, instance=modelo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Modelo {modelo.nome} atualizado!')
            return redirect('viaturas:lista_modelos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ModeloViaturaForm(instance=modelo)
    return render(request, 'viaturas/form_modelo.html', {'form': form, 'titulo': f'Editar {modelo.nome}'})


# =============================================================================
# OFICINAS
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_oficinas(request):
    qs = Oficina.objects.annotate(total_manutencoes=Count('manutencoes')).all()
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_oficinas.html', {'page_obj': page})


@login_required
@require_module_permission('frota')
def criar_oficina(request):
    if request.method == 'POST':
        form = OficinaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Oficina cadastrada com sucesso!')
            return redirect('viaturas:lista_oficinas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = OficinaForm()
    return render(request, 'viaturas/form_oficina.html', {'form': form, 'titulo': 'Nova Oficina'})


@login_required
@require_module_permission('frota')
def editar_oficina(request, pk):
    oficina = get_object_or_404(Oficina, pk=pk)
    if request.method == 'POST':
        form = OficinaForm(request.POST, instance=oficina)
        if form.is_valid():
            form.save()
            messages.success(request, f'Oficina {oficina.nome} atualizada!')
            return redirect('viaturas:lista_oficinas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = OficinaForm(instance=oficina)
    return render(request, 'viaturas/form_oficina.html', {'form': form, 'titulo': f'Editar {oficina.nome}'})

@login_required
@require_module_permission('frota')
def importar_viaturas(request):
    if request.method == 'POST':
        form = ImportarFrotaForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = request.FILES['arquivo']
            extensao = arquivo.name.split('.')[-1].lower()
            
            criados = 0
            atualizados = 0
            erros = []
            
            try:
                with transaction.atomic():
                    if extensao == 'xml':
                        tree = ET.parse(arquivo)
                        root = tree.getroot()
                        for v_elem in root.findall('.//Viatura'):
                            data = {
                                'marca_modelo': v_elem.findtext('MarcaModelo'),
                                'placa': v_elem.findtext('Placa'),
                                'chassi': v_elem.findtext('Chassi'),
                                'renavam': v_elem.findtext('Renavam'),
                                'ano_fabricacao': v_elem.findtext('AnoFabricacao'),
                                'numero_patrimonio': v_elem.findtext('NumeroPatrimonio'),
                                'prefixo': v_elem.findtext('Prefixo'),
                                'situacao': v_elem.findtext('Situacao'),
                            }
                            
                            res = _processar_viatura_import(data)
                            if res == 'criado': criados += 1
                            elif res == 'atualizado': atualizados += 1
                    
                    elif extensao in ['xlsx', 'xls']:
                        df = pd.read_excel(arquivo)
                        for _, row in df.iterrows():
                            # Mapeamento básico para planilhas
                            data = {
                                'marca_modelo': row.get('MarcaModelo') or row.get('Modelo'),
                                'placa': row.get('Placa'),
                                'chassi': row.get('Chassi'),
                                'renavam': row.get('Renavam'),
                                'ano_fabricacao': row.get('AnoFabricacao'),
                                'numero_patrimonio': row.get('NumeroPatrimonio') or row.get('Patrimonio'),
                                'prefixo': row.get('Prefixo'),
                                'situacao': row.get('Situacao') or row.get('Status'),
                            }
                            if not data['prefixo'] and not data['placa']:
                                continue
                                
                            res = _processar_viatura_import(data)
                            if res == 'criado': criados += 1
                            elif res == 'atualizado': atualizados += 1
                    
                messages.success(request, f'Importação concluída! {criados} novas viaturas, {atualizados} atualizadas.')
                return redirect('viaturas:lista_viaturas')
                
            except Exception as e:
                messages.error(request, f'Erro ao processar arquivo: {str(e)}')
    else:
        form = ImportarFrotaForm()
        
    return render(request, 'viaturas/importar_viaturas.html', {'form': form})

def _processar_viatura_import(data):
    """Função auxiliar para processar uma linha de importação."""
    prefixo = data.get('prefixo') or f"S/P-{data.get('placa')}"
    if not prefixo: return 'erro'
    
    # Tratar Marca e Modelo
    mm = data.get('marca_modelo', 'IGNORADO/DESCONHECIDO')
    if '/' in mm:
        marca_nome, modelo_nome = mm.split('/', 1)
    else:
        marca_nome, modelo_nome = 'OUTROS', mm
        
    marca, _ = MarcaViatura.objects.get_or_create(nome=marca_nome.strip().upper())
    
    # Tenta inferir tipo
    tipo = '4_RODAS'
    if any(x in modelo_nome.upper() for x in ['MOTO', 'NXR', 'XT', 'LANDER', 'TRIUMPH', 'BMW G']):
        tipo = 'MOTO'
    elif any(x in modelo_nome.upper() for x in ['CARGO', 'BUS', 'ONIBUS', 'CAMINHAO']):
        tipo = 'CAMINHAO'
        
    modelo, _ = ModeloViatura.objects.get_or_create(
        marca=marca, 
        nome=modelo_nome.strip().upper(),
        defaults={'tipo': tipo}
    )
    
    # Mapear Situação
    status = 'DISPONIVEL'
    situacao = str(data.get('situacao', '')).upper()
    if 'DESCARGA' in situacao or 'BAIXA' in situacao:
        status = 'BAIXADA'
    elif 'MANUT' in situacao or 'OFICINA' in situacao:
        status = 'MANUTENCAO'
        
    obj, created = Viatura.objects.update_or_create(
        prefixo=prefixo,
        defaults={
            'placa': data.get('placa'),
            'chassi': data.get('chassi'),
            'renavam': data.get('renavam'),
            'numero_patrimonio': data.get('numero_patrimonio'),
            'modelo': modelo,
            'ano_fabricacao': int(data.get('ano_fabricacao')) if data.get('ano_fabricacao') and str(data.get('ano_fabricacao')).isdigit() else None,
            'status': status
        }
    )
    return 'criado' if created else 'atualizado'


@login_required
@require_module_permission('frota')
def lista_checklists(request):
    q = request.GET.get('q', '')
    checklists = ChecklistViatura.objects.all()
    
    if q:
        checklists = checklists.filter(
            Q(viatura__prefixo__icontains=q) | 
            Q(policial__nome_completo__icontains=q) |
            Q(policial__nome_guerra__icontains=q)
        )
    
    paginator = Paginator(checklists, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'viaturas/lista_checklists.html', {
        'page_obj': page_obj,
        'q': q
    })

@login_required
@require_module_permission('frota')
def criar_checklist(request):
    viatura_id = request.GET.get('viatura')
    initial_data = {}
    if viatura_id:
        viatura = get_object_or_404(Viatura, pk=viatura_id)
        initial_data['viatura'] = viatura
        initial_data['odometro'] = viatura.odometro_atual

    if request.method == 'POST':
        form = ChecklistViaturaForm(request.POST)
        if form.is_valid():
            checklist = form.save(commit=False)
            checklist.registrado_por = request.user
            checklist.save()
            
            # Opcional: Atualizar odômetro da viatura se o do checklist for maior
            if checklist.odometro > checklist.viatura.odometro_atual:
                checklist.viatura.odometro_atual = checklist.odometro
                checklist.viatura.save()
                
            messages.success(request, 'Checklist registrado com sucesso!')
            return redirect('viaturas:lista_checklists')
    else:
        form = ChecklistViaturaForm(initial=initial_data)

    return render(request, 'viaturas/form_checklist.html', {'form': form})

@login_required
@require_module_permission('frota')
def detalhe_checklist(request, pk):
    checklist = get_object_or_404(ChecklistViatura, pk=pk)
    return render(request, 'viaturas/detalhe_checklist.html', {'checklist': checklist})

# =============================================================================
# BAIXA DE VIATURAS
# =============================================================================

@login_required
def solicitar_baixa(request):
    """View para qualquer usuário solicitar a baixa de uma viatura."""
    if request.method == 'POST':
        form = SolicitacaoBaixaViaturaForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.solicitante = request.user
            solicitacao.save()
            messages.success(request, 'Solicitação de baixa registrada e enviada para análise.')
            return redirect('home') # Ou algum lugar apropriado para o usuário
    else:
        form = SolicitacaoBaixaViaturaForm()

    return render(request, 'viaturas/form_solicitar_baixa.html', {'form': form})

@login_required
@require_module_permission('frota')
def lista_baixas(request):
    """Lista as solicitações de baixa para a administração da frota."""
    qs = SolicitacaoBaixaViatura.objects.select_related('viatura', 'solicitante', 'analisado_por').order_by('-data_solicitacao')
    
    status_filtro = request.GET.get('status', 'PENDENTE')
    if status_filtro:
        qs = qs.filter(status=status_filtro)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'viaturas/lista_baixas.html', {
        'page_obj': page_obj,
        'status_filtro': status_filtro
    })

@login_required
@require_module_permission('frota')
def analisar_baixa(request, pk):
    """View para o gestor de frota analisar e destinar uma solicitação de baixa."""
    solicitacao = get_object_or_404(SolicitacaoBaixaViatura, pk=pk)
    viatura = solicitacao.viatura
    
    if request.method == 'POST':
        form = AnaliseBaixaViaturaForm(request.POST, instance=solicitacao)
        if form.is_valid():
            analise = form.save(commit=False)
            analise.analisado_por = request.user
            analise.data_analise = timezone.now()
            
            # Lógica de atualização da Viatura conforme a destinação escolhida pelo gestor
            if analise.status == 'MANUTENCAO':
                viatura.status = 'MANUTENCAO'
                # Abrir automaticamente uma manutenção corretiva
                nova_man = Manutencao.objects.create(
                    viatura=viatura,
                    tipo='CORRETIVA',
                    status='ABERTA',
                    data_inicio=timezone.now().date(),
                    odometro=viatura.odometro_atual,
                    descricao=f"Manutenção aberta automaticamente via Solicitação de Baixa #{analise.id}. Justificativa: {analise.motivo}",
                    registrado_por=request.user
                )
                registrar_abertura(nova_man, request.user)
            elif analise.status == 'OFICINA':
                viatura.status = 'MANUTENCAO'
                viatura.localizacao = 'OFICINA'
            elif analise.status == 'AGUARDAR_VISTORIA':
                viatura.status = 'VISTORIA'
            elif analise.status == 'MOTOMEC':
                viatura.localizacao = 'MOTOMEC'
                viatura.status = 'DISPONIVEL'
            elif analise.status == 'PREGAO':
                viatura.status = 'PREGAO'
            elif analise.status == 'DESCARGA':
                viatura.status = 'BAIXADA'
            
            # Salvar alterações na viatura se não for negada
            if analise.status != 'NEGADA':
                viatura.save()
                
            analise.save()
            
            # Mensagem de feedback para o gestor
            destinacao = analise.get_status_display()
            messages.success(request, f'Solicitação #{analise.id} processada. Viatura {viatura.prefixo} destinada para: {destinacao}.')
            return redirect('viaturas:lista_baixas')
    else:
        form = AnaliseBaixaViaturaForm(instance=solicitacao)

    return render(request, 'viaturas/analisar_baixa.html', {'form': form, 'solicitacao': solicitacao})

# =============================================================================
# CONTROLE DE PEÇAS DE VIATURAS
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_pecas(request):
    qs = PecaViatura.objects.all().order_by('nome')
    q = request.GET.get('q')
    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(codigo__icontains=q))
    
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_pecas.html', {'page_obj': page, 'q': q})

@login_required
@require_module_permission('frota')
def criar_peca(request):
    if request.method == 'POST':
        form = PecaViaturaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Peça cadastrada com sucesso!')
            return redirect('viaturas:lista_pecas')
    else:
        form = PecaViaturaForm()
    return render(request, 'viaturas/form_peca.html', {'form': form, 'titulo': 'Nova Peça'})

@login_required
@require_module_permission('frota')
def editar_peca(request, pk):
    peca = get_object_or_404(PecaViatura, pk=pk)
    if request.method == 'POST':
        form = PecaViaturaForm(request.POST, instance=peca)
        if form.is_valid():
            form.save()
            messages.success(request, 'Peça atualizada com sucesso!')
            return redirect('viaturas:lista_pecas')
    else:
        form = PecaViaturaForm(instance=peca)
    return render(request, 'viaturas/form_peca.html', {'form': form, 'titulo': 'Editar Peça'})

@login_required
@require_module_permission('frota')
def lista_retiradas(request):
    qs = RetiradaPeca.objects.select_related('viatura', 'policial').order_by('-data_retirada')
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_retiradas.html', {'page_obj': page})

@login_required
@require_module_permission('frota')
def criar_retirada(request):
    if request.method == 'POST':
        form = RetiradaPecaForm(request.POST)
        formset = RetiradaPecaItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            retirada = form.save(commit=False)
            retirada.registrado_por = request.user
            retirada.save()
            
            formset.instance = retirada
            try:
                with transaction.atomic():
                    formset.save()
                messages.success(request, 'Retirada registrada com sucesso!')
                return redirect('viaturas:recibo_retirada_peca', pk=retirada.pk)
            except ValueError as e:
                messages.error(request, str(e))
                retirada.delete() # Reverte se houver erro no estoque
    else:
        form = RetiradaPecaForm()
        formset = RetiradaPecaItemFormSet()
        
    return render(request, 'viaturas/form_retirada.html', {'form': form, 'formset': formset, 'titulo': 'Nova Retirada de Peças'})

@login_required
@require_module_permission('frota')
def recibo_retirada_peca(request, pk):
    retirada = get_object_or_404(RetiradaPeca.objects.select_related('viatura', 'policial', 'registrado_por'), pk=pk)
    return render(request, 'viaturas/recibo_retirada_peca.html', {'retirada': retirada})

@login_required
@require_module_permission('frota')
def anexar_recibo_retirada(request, pk):
    retirada = get_object_or_404(RetiradaPeca, pk=pk)
    if request.method == 'POST':
        form = AnexarReciboRetiradaForm(request.POST, request.FILES, instance=retirada)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recibo anexado com sucesso!')
            return redirect('viaturas:lista_retiradas')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = AnexarReciboRetiradaForm(instance=retirada)
    return render(request, 'viaturas/form_anexar_recibo.html', {'form': form, 'retirada': retirada})


# =============================================================================
# EVIDÊNCIAS DE MANUTENÇÃO (Fase 3)
# =============================================================================

@login_required
@require_module_permission('frota')
def adicionar_evidencia(request, manutencao_pk):
    """Upload de evidência (foto, laudo, orçamento) para uma manutenção."""
    man = get_object_or_404(Manutencao, pk=manutencao_pk)
    if request.method == 'POST':
        form = EvidenciaManutencaoForm(request.POST, request.FILES)
        if form.is_valid():
            ev = form.save(commit=False)
            ev.manutencao = man
            ev.registrado_por = request.user
            ev.save()
            registrar_evidencia(man, request.user, ev)
            messages.success(request, 'Evidência anexada com sucesso!')
            return redirect('viaturas:detalhe_manutencao', pk=manutencao_pk)
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = EvidenciaManutencaoForm()
    return render(request, 'viaturas/form_evidencia.html', {
        'form': form, 'manutencao': man, 'titulo': 'Anexar Evidência'
    })


@login_required
@require_module_permission('frota')
@require_POST
def excluir_evidencia(request, pk):
    """Exclui uma evidência de manutenção."""
    ev = get_object_or_404(EvidenciaManutencao, pk=pk)
    manutencao_pk = ev.manutencao.pk
    ev.arquivo.delete(save=False)
    ev.delete()
    messages.success(request, 'Evidência removida.')
    return redirect('viaturas:detalhe_manutencao', pk=manutencao_pk)


# =============================================================================
# PLANOS DE MANUTENÇÃO PREVENTIVA (Fase 3)
# =============================================================================

@login_required
@require_module_permission('frota')
def lista_planos_preventivos(request):
    qs = PlanoManutencaoPreventiva.objects.select_related('modelo', 'modelo__marca').all()
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'viaturas/lista_planos_preventivos.html', {'page_obj': page})


@login_required
@require_module_permission('frota')
def criar_plano_preventivo(request):
    if request.method == 'POST':
        form = PlanoManutencaoPreventivaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Plano de manutenção preventiva cadastrado!')
            return redirect('viaturas:lista_planos_preventivos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = PlanoManutencaoPreventivaForm()
    return render(request, 'viaturas/form_plano_preventivo.html', {
        'form': form, 'titulo': 'Novo Plano Preventivo'
    })


@login_required
@require_module_permission('frota')
def editar_plano_preventivo(request, pk):
    plano = get_object_or_404(PlanoManutencaoPreventiva, pk=pk)
    if request.method == 'POST':
        form = PlanoManutencaoPreventivaForm(request.POST, instance=plano)
        if form.is_valid():
            form.save()
            messages.success(request, 'Plano preventivo atualizado!')
            return redirect('viaturas:lista_planos_preventivos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = PlanoManutencaoPreventivaForm(instance=plano)
    return render(request, 'viaturas/form_plano_preventivo.html', {
        'form': form, 'titulo': f'Editar: {plano.descricao}'
    })


# =============================================================================
# HISTÓRICO DE AUDITORIA (Fase 1)
# =============================================================================

@login_required
@require_module_permission('frota')
def adicionar_servico_manutencao(request, manutencao_pk):
    """Registra um novo serviço como entrada imutável no histórico."""
    man = get_object_or_404(Manutencao, pk=manutencao_pk)
    if man.status in ('CONCLUIDA', 'CANCELADA'):
        messages.warning(request, 'Não é possível registrar serviço em manutenção encerrada.')
        return redirect('viaturas:historico_manutencao', pk=manutencao_pk)

    if request.method == 'POST':
        form = ServicoManutencaoForm(request.POST, manutencao=man)
        if form.is_valid():
            dados = form.cleaned_data
            registrar_servico(
                man,
                request.user,
                dados['descricao'],
                detalhamento=dados.get('detalhamento'),
                pecas_garantia=dados.get('pecas_garantia'),
                custo_pecas=dados.get('custo_pecas'),
                custo_mao_obra=dados.get('custo_mao_obra'),
                odometro=dados.get('odometro'),
            )
            messages.success(request, 'Serviço registrado no histórico com sucesso!')
            return redirect('viaturas:historico_manutencao', pk=manutencao_pk)
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ServicoManutencaoForm(manutencao=man)

    return render(request, 'viaturas/form_servico_manutencao.html', {
        'form': form,
        'manutencao': man,
        'titulo': 'Registrar Novo Serviço',
    })


@login_required
@require_module_permission('frota')
def historico_manutencao(request, pk):
    """
    Exibe a linha do tempo de eventos e serviços da manutenção (modelo append-only).
    Sempre garante pelo menos um registro de abertura para manutenções antigas.
    """
    man = get_object_or_404(
        Manutencao.objects.select_related('viatura', 'registrado_por'),
        pk=pk,
    )
    # Garante que manutenções antigas (antes da nova estrutura) tenham pelo menos um evento de abertura
    garantir_historico_estruturado(man)

    # Recarrega com prefetch para não gerar N+1 no template
    man = (
        Manutencao.objects
        .select_related('viatura', 'registrado_por')
        .prefetch_related(
            'registros_historico__servico',
            'registros_historico__registrado_por',
            'servicos__registrado_por',
        )
        .get(pk=pk)
    )

    eventos = man.registros_historico.select_related('servico', 'registrado_por').order_by('data_registro')
    servicos = man.servicos.select_related('registrado_por').order_by('data_registro')

    return render(request, 'viaturas/historico_manutencao.html', {
        'manutencao': man,
        'eventos': eventos,
        'servicos': servicos,
        'pode_registrar_servico': man.status not in ('CONCLUIDA', 'CANCELADA'),
    })

