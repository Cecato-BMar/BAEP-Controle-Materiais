"""
viaturas/services/indicadores_service.py
Serviços de indicadores, KPIs e alertas operacionais da frota.

Centraliza toda a lógica de dashboard e métricas que antes vivia em views.py.
As views passam a chamar estes services e apenas formatam o resultado.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Avg, F, Subquery, OuterRef
from django.utils import timezone

from viaturas.models import (
    Viatura, DespachoViatura, Abastecimento, Manutencao,
    PlanoManutencaoPreventiva, DocumentoViatura, PecaViatura,
    RetiradaPeca, StatusViatura, StatusManutencao,
)


# ============================================================================
# STATUS DA FROTA
# ============================================================================
def obter_status_counts():
    """
    Retorna contagem consolidada de viaturas por status.

    Returns:
        dict com chaves: total, disponiveis, em_uso, manutencao, baixadas, vistoria, pregao.
    """
    rows = Viatura.objects.values('status').annotate(total=Count('id'))
    status_map = {row['status']: row['total'] for row in rows}
    total = sum(status_map.values())
    return {
        'total': total,
        'disponiveis': status_map.get('DISPONIVEL', 0),
        'em_uso': status_map.get('EM_USO', 0),
        'manutencao': status_map.get('MANUTENCAO', 0),
        'baixadas': status_map.get('BAIXADA', 0),
        'vistoria': status_map.get('VISTORIA', 0),
        'pregao': status_map.get('PREGAO', 0),
    }


def obter_distribuicao_por_tipo():
    """
    Retorna contagem de viaturas agrupada por tipo de veículo.

    Returns:
        QuerySet com values('modelo__tipo').annotate(total=Count('id')).
    """
    return (
        Viatura.objects
        .values('modelo__tipo')
        .annotate(total=Count('id'))
        .order_by('modelo__tipo')
    )


# ============================================================================
# DESPACHOS E OPERAÇÃO
# ============================================================================
def obter_despachos_ativos():
    """Retorna despachos sem retorno ordenados por saída."""
    return (
        DespachoViatura.objects
        .filter(data_retorno__isnull=True)
        .select_related('viatura', 'motorista', 'encarregado')
        .order_by('-data_saida')
    )


def obter_ultimos_abastecimentos(limite=5):
    """Retorna os últimos abastecimentos registrados."""
    return (
        Abastecimento.objects
        .select_related('viatura', 'motorista')
        .order_by('-data_abastecimento')[:limite]
    )


def obter_ultimas_retiradas(limite=5):
    """Retorna as últimas retiradas de peças com contagem de itens."""
    return (
        RetiradaPeca.objects
        .select_related('viatura')
        .annotate(total_itens=Count('itens'))
        .order_by('-data_retirada')[:limite]
    )


# ============================================================================
# MANUTENÇÕES
# ============================================================================
def obter_manutencoes_abertas():
    """Retorna manutenções em aberto (ABERTA ou AGUARDANDO_PECA)."""
    return (
        Manutencao.objects
        .filter(status__in=['ABERTA', 'AGUARDANDO_PECA'])
        .select_related('viatura')
        .order_by('data_inicio')
    )


def obter_agendamentos():
    """
    Retorna agendamentos futuros e contagem de atrasados.

    Returns:
        tuple (queryset_agendamentos, int_agendamentos_atrasados).
    """
    hoje = timezone.now().date()
    agendamentos = (
        Manutencao.objects
        .filter(status='AGENDADA')
        .select_related('viatura', 'oficina_fk')
        .order_by('data_inicio')
    )
    atrasados = agendamentos.filter(data_inicio__lt=hoje).count()
    return agendamentos, atrasados


# ============================================================================
# ALERTAS INTELIGENTES
# ============================================================================
def obter_garantias_vencendo(dias=30):
    """Retorna manutenções com garantia vencendo nos próximos N dias."""
    hoje = timezone.now().date()
    limite = hoje + timedelta(days=dias)
    return (
        Manutencao.objects
        .filter(
            status='CONCLUIDA',
            data_validade_garantia__isnull=False,
            data_validade_garantia__lte=limite,
            data_validade_garantia__gte=hoje,
        )
        .select_related('viatura')
        .order_by('data_validade_garantia')[:10]
    )


def obter_garantias_vencidas(dias_retroativos=60):
    """Retorna contagem de garantias vencidas nos últimos N dias."""
    hoje = timezone.now().date()
    return (
        Manutencao.objects
        .filter(
            status='CONCLUIDA',
            data_validade_garantia__isnull=False,
            data_validade_garantia__lt=hoje,
            data_validade_garantia__gte=hoje - timedelta(days=dias_retroativos),
        )
        .select_related('viatura')
        .count()
    )


def obter_manutencoes_longas(dias=30):
    """Retorna manutenções abertas há mais de N dias sem conclusão."""
    limite = timezone.now().date() - timedelta(days=dias)
    return (
        Manutencao.objects
        .filter(status__in=['ABERTA', 'AGUARDANDO_PECA'], data_inicio__lte=limite)
        .select_related('viatura')
        .order_by('data_inicio')[:10]
    )


def obter_documentos_vencendo(dias=30):
    """Retorna documentos vencendo nos próximos N dias e contagem de vencidos."""
    hoje = timezone.now().date()
    limite = hoje + timedelta(days=dias)
    vencendo = (
        DocumentoViatura.objects
        .filter(
            ativo=True,
            data_vencimento__isnull=False,
            data_vencimento__lte=limite,
            data_vencimento__gte=hoje,
        )
        .select_related('viatura')
        .order_by('data_vencimento')[:10]
    )
    vencidos = (
        DocumentoViatura.objects
        .filter(ativo=True, data_vencimento__isnull=False, data_vencimento__lt=hoje)
        .count()
    )
    return vencendo, vencidos


def obter_pecas_estoque_baixo():
    """Retorna contagem de peças com estoque abaixo do mínimo."""
    return (
        PecaViatura.objects
        .filter(quantidade_estoque__lte=F('limite_minimo'), ativo=True)
        .count()
    )


# ============================================================================
# ALERTAS PREVENTIVOS (Subquery em vez de N+1 loop)
# ============================================================================
def obter_alertas_preventivas(limite=10):
    """
    Gera lista de alertas de manutenção preventiva vencida/atrasada.

    Usa Subquery para obter a data/km da última preventiva de cada viatura
    e compara com os planos cadastrados — sem loop N+1.

    Returns:
        list[dict] com chaves: viatura, plano, motivo.
    """
    hoje = timezone.now().date()
    planos_ativos = (
        PlanoManutencaoPreventiva.objects
        .filter(ativo=True)
        .select_related('modelo')
    )
    if not planos_ativos:
        return []

    planos_por_modelo = {}
    for plano in planos_ativos:
        planos_por_modelo.setdefault(plano.modelo_id, []).append(plano)

    modelos_ids = list(planos_por_modelo.keys())

    ultima_prev_sub = (
        Manutencao.objects
        .filter(viatura=OuterRef('pk'), tipo='PREVENTIVA', status='CONCLUIDA')
        .order_by('-data_conclusao')
    )

    viaturas_ativas = (
        Viatura.objects
        .filter(modelo_id__in=modelos_ids, status__in=['DISPONIVEL', 'EM_USO'])
        .select_related('modelo')
        .annotate(
            ultima_prev_data=Subquery(ultima_prev_sub.values('data_conclusao')[:1]),
            ultima_prev_km=Subquery(ultima_prev_sub.values('odometro')[:1]),
        )
    )

    alertas = []
    for vtr in viaturas_ativas:
        planos = planos_por_modelo.get(vtr.modelo_id, [])
        for plano in planos:
            alerta = False
            motivo = ''
            if plano.intervalo_km and vtr.ultima_prev_km is not None:
                km_desde = vtr.odometro_atual - vtr.ultima_prev_km
                if km_desde >= Decimal(str(plano.intervalo_km)):
                    alerta = True
                    motivo = f'{km_desde:,.0f} km desde a última ({plano.descricao})'
            if plano.intervalo_dias and vtr.ultima_prev_data is not None:
                dias_desde = (hoje - vtr.ultima_prev_data).days
                if dias_desde >= plano.intervalo_dias:
                    alerta = True
                    motivo = f'{dias_desde} dias desde a última ({plano.descricao})'
            if vtr.ultima_prev_data is None and (plano.intervalo_km or plano.intervalo_dias):
                alerta = True
                motivo = f'Nunca realizou: {plano.descricao}'

            if alerta:
                alertas.append({'viatura': vtr, 'plano': plano, 'motivo': motivo})

    return alertas[:limite]


# ============================================================================
# KPIs AGREGADOS DE FROTA
# ============================================================================
def obter_kpis_frota():
    """
    Retorna indicadores consolidados de custo e tempo de manutenção.

    Returns:
        dict com chaves:
            custo_total_frota, custo_medio, tempo_medio_oficina,
            total_manutencoes_concluidas.
    """
    concluidas = Manutencao.objects.filter(status='CONCLUIDA')
    agg = concluidas.aggregate(
        total_pecas=Sum('custo_pecas'),
        total_mao_obra=Sum('custo_mao_obra'),
        total_registros=Count('id'),
    )
    custo_total = (agg['total_pecas'] or Decimal('0')) + (agg['total_mao_obra'] or Decimal('0'))
    qtd = agg['total_registros'] or 0
    custo_medio = custo_total / qtd if qtd else Decimal('0')

    # Tempo médio em oficina (apenas com datas válidas)
    tempos = []
    for m in concluidas.filter(data_conclusao__isnull=False):
        if m.data_conclusao and m.data_inicio:
            tempos.append((m.data_conclusao - m.data_inicio).days)
    tempo_medio = sum(tempos) / len(tempos) if tempos else 0

    return {
        'custo_total_frota': custo_total,
        'custo_medio': custo_medio,
        'tempo_medio_oficina': tempo_medio,
        'total_manutencoes_concluidas': qtd,
    }


def obter_top_viaturas_custo(limite=5):
    """Retorna as N viaturas com maior custo acumulado de manutenção."""
    return (
        Viatura.objects
        .annotate(custo_manut=Sum('manutencoes__custo_pecas') + Sum('manutencoes__custo_mao_obra'))
        .filter(custo_manut__gt=0)
        .order_by('-custo_manut')[:limite]
    )


# ============================================================================
# INDICADORES POR VIATURA (detalhe_viatura)
# ============================================================================
def obter_indicadores_viatura(viatura):
    """
    Retorna indicadores específicos de uma viatura para a tela de detalhe.

    Args:
        viatura: instância de Viatura (com modelo e marca pré-carregados).

    Returns:
        dict com:
            total_km_rodado, total_combustivel, custo_total_manutencao,
            total_manutencoes, concluidas_count, preventivas_count, corretivas_count,
            manutencoes_com_duracao.
    """
    # Km rodado
    total_km_rodado = (
        viatura.despachos
        .filter(km_retorno__isnull=False)
        .aggregate(total=Sum('km_retorno') - Sum('km_saida'))['total']
    ) or Decimal('0')

    # Total combustível
    total_combustivel = (
        viatura.abastecimentos.aggregate(total=Sum('quantidade_litros'))['total']
    ) or Decimal('0')

    # Manutenções
    manutencoes = viatura.manutencoes.order_by('-data_inicio')
    custo_total_manutencao = sum(m.custo_total for m in manutencoes)

    total_manutencoes = manutencoes.count()
    concluidas_count = manutencoes.filter(status='CONCLUIDA').count()
    preventivas_count = manutencoes.filter(tipo='PREVENTIVA').count()
    corretivas_count = manutencoes.filter(tipo='CORRETIVA').count()

    # Com duração
    manutencoes_com_duracao = []
    for m in manutencoes:
        duracao_dias = None
        if m.status == 'CONCLUIDA' and m.data_conclusao:
            duracao_dias = (m.data_conclusao - m.data_inicio).days
        manutencoes_com_duracao.append({
            'obj': m,
            'duracao_dias': duracao_dias,
            'custo_total': m.custo_total,
        })

    return {
        'total_km_rodado': total_km_rodado,
        'total_combustivel': total_combustivel,
        'custo_total_manutencao': custo_total_manutencao,
        'total_manutencoes': total_manutencoes,
        'concluidas_count': concluidas_count,
        'preventivas_count': preventivas_count,
        'corretivas_count': corretivas_count,
        'manutencoes_com_duracao': manutencoes_com_duracao,
    }


# ============================================================================
# CONTEXTO COMPLETO DO DASHBOARD
# ============================================================================
def obter_contexto_dashboard():
    """
    Monta o dicionário completo de contexto do dashboard da frota.

    Substitui toda a lógica que antes estava dentro de dashboard_frota().

    Returns:
        dict pronto para ser passado como context ao render().
    """
    status = obter_status_counts()
    kpis = obter_kpis_frota()
    agendamentos, agendamentos_atrasados = obter_agendamentos()
    documentos_vencendo, documentos_vencidos = obter_documentos_vencendo()

    return {
        # Status
        **status,
        'por_tipo': obter_distribuicao_por_tipo(),
        # Operação
        'despachos_ativos': obter_despachos_ativos(),
        'manutencoes_abertas': obter_manutencoes_abertas(),
        'ultimos_abastecimentos': obter_ultimos_abastecimentos(),
        'agendamentos': agendamentos,
        'agendamentos_atrasados': agendamentos_atrasados,
        'hoje': timezone.now().date(),
        # Peças
        'pecas_estoque_baixo': obter_pecas_estoque_baixo(),
        'ultimas_retiradas': obter_ultimas_retiradas(),
        # Alertas inteligentes
        'garantias_vencendo': obter_garantias_vencendo(),
        'garantias_vencidas': obter_garantias_vencidas(),
        'manutencoes_longas': obter_manutencoes_longas(),
        'alertas_preventivas': obter_alertas_preventivas(),
        # Documentos
        'documentos_vencendo': documentos_vencendo,
        'documentos_vencidos': documentos_vencidos,
        # KPIs
        **kpis,
        'top_viaturas_custo': obter_top_viaturas_custo(),
    }
