"""
viaturas/services/previsao_service.py
Motor de previsão de manutenção preventiva.

Calcula previsões de manutenção baseadas em:
- Histórico de km (odômetro dos despachos e manutenções)
- Média diária e mensal de rodagem
- Intervalos entre manutenções anteriores
- Planos de manutenção preventiva cadastrados

Retorna para cada item previsto:
- Data prevista
- Km prevista
- Nível de confiança (ALTO / MÉDIO / BAIXO)

Previsões específicas:
- Troca de óleo
- Pneus
- Revisões gerais
"""
import statistics
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, F, Q
from django.utils import timezone

from viaturas.models import (
    Viatura, DespachoViatura, Manutencao, PlanoManutencaoPreventiva,
    RetiradaPecaItem, ServicoManutencao, StatusManutencao,
)


# ============================================================================
# CONSTANTES DE REFERÊNCIA
# ============================================================================
INTERVALO_DIAS_PADRAO = 180
INTERVALO_KM_PADRAO = 10000

# Palavras-chave para agrupamento de serviços de oficina
GRUPOS_SERVICOS = {
    'Troca de Óleo': ('óleo', 'oleo'),
    'Pastilhas de Freio': ('pastilha', 'freio'),
    'Troca/Alinhamento de Pneus': ('pneu',),
    'Troca de Bateria': ('bateria',),
    'Troca de Filtros': ('filtro',),
    'Manutenção de Suspensão/Bieleta': ('bieleta', 'suspensão', 'suspensao'),
}

# Previsões específicas solicitadas pelo usuário
PREVISOES_ESPECIFICAS = {
    'Troca de Óleo': {
        'palavras_chave': ('óleo', 'oleo', 'lubrificante'),
        'intervalo_dias_padrao': 180,       # 6 meses
        'intervalo_km_padrao': 5000,         # 5.000 km
        'icone': 'fa-oil-can',
        'prioridade': 1,
    },
    'Pneus': {
        'palavras_chave': ('pneu', 'pneus', 'alinhamento', 'balanceamento', 'rodízio'),
        'intervalo_dias_padrao': 730,        # 2 anos
        'intervalo_km_padrao': 40000,        # 40.000 km
        'icone': 'fa-circle',
        'prioridade': 2,
    },
    'Revisão Geral': {
        'palavras_chave': ('revisão', 'revisao', 'revisão geral', 'check-up'),
        'intervalo_dias_padrao': 365,        # 1 ano
        'intervalo_km_padrao': 10000,        # 10.000 km
        'icone': 'fa-clipboard-check',
        'prioridade': 3,
    },
}


def _classificar_servico(descricao):
    """Retorna o nome do grupo de serviço com base na descrição."""
    desc_lower = descricao.lower()
    for grupo, palavras_chave in GRUPOS_SERVICOS.items():
        for palavra in palavras_chave:
            if palavra in desc_lower:
                return grupo
    return descricao.title()


# ============================================================================
# TAXA DE KM — Média diária e mensal de rodagem
# ============================================================================
def calcular_taxa_km(viatura, dias_analise=90):
    """
    Calcula a taxa média de km rodados por dia e por mês com base nos despachos.

    Usa despachos completados (com retorno) nos últimos N dias para calcular
    a média real de uso da viatura.

    Args:
        viatura: instância de Viatura.
        dias_analise: janela de análise em dias (padrão 90).

    Returns:
        dict com:
            km_total_periodo: Decimal — km total rodado no período
            dias_ativos: int — dias com pelo menos 1 despacho
            dias_periodo: int — dias analisados
            media_diaria: float — km/dia (considerando todo o período)
            media_mensal: float — km/mês estimada
            metodo: str — 'despachos' | 'manutencoes' | 'estimativa'
    """
    hoje = timezone.now().date()
    inicio = hoje - timedelta(days=dias_analise)

    # Método 1: Despachos completados no período
    despachos = (
        DespachoViatura.objects
        .filter(
            viatura=viatura,
            data_retorno__isnull=False,
            km_retorno__isnull=False,
            data_saida__date__gte=inicio,
        )
        .annotate(km_rodado=F('km_retorno') - F('km_saida'))
        .filter(km_rodado__gt=0)
        .order_by('data_saida')
    )

    if despachos.exists():
        km_total = sum(float(d.km_rodado) for d in despachos)
        dias_ativos = despachos.values('data_saida__date').distinct().count()
        media_diaria = km_total / dias_analise  # usa todo o período, não só dias ativos
        media_mensal = media_diaria * 30.44  # média de dias por mês
        return {
            'km_total_periodo': Decimal(str(round(km_total, 1))),
            'dias_ativos': dias_ativos,
            'dias_periodo': dias_analise,
            'media_diaria': round(media_diaria, 1),
            'media_mensal': round(media_mensal, 0),
            'metodo': 'despachos',
        }

    # Método 2: Diferença entre manutenções consecutivas (fallback)
    manutencoes = (
        Manutencao.objects
        .filter(viatura=viatura, data_inicio__gte=inicio)
        .order_by('data_inicio')
    )
    if manutencoes.count() >= 2:
        manut_list = list(manutencoes)
        km_diff = float(manut_list[-1].odometro - manut_list[0].odometro)
        dias_diff = (manut_list[-1].data_inicio - manut_list[0].data_inicio).days
        if dias_diff > 0 and km_diff > 0:
            media_diaria = km_diff / dias_diff
            return {
                'km_total_periodo': Decimal(str(round(km_diff, 1))),
                'dias_ativos': dias_diff,
                'dias_periodo': dias_analise,
                'media_diaria': round(media_diaria, 1),
                'media_mensal': round(media_diaria * 30.44, 0),
                'metodo': 'manutencoes',
            }

    # Método 3: Estimativa genérica (viatura operacional padrão)
    return {
        'km_total_periodo': Decimal('0'),
        'dias_ativos': 0,
        'dias_periodo': dias_analise,
        'media_diaria': 50.0,    # estimativa: 50km/dia para viatura policial
        'media_mensal': 1522.0,  # ~1.500 km/mês
        'metodo': 'estimativa',
    }


# ============================================================================
# NÍVEL DE CONFIANÇA
# ============================================================================
def calcular_confianca(ocorrencias, media_dias, media_km, tem_plano):
    """
    Calcula o nível de confiança da previsão (ALTO / MÉDIO / BAIXO).

    Fatores:
    - Quantidade de ocorrências no histórico (peso 40%)
    - Variância dos intervalos (peso 30%) — baixa variância = mais confiança
    - Existência de plano oficial cadastrado (peso 30%)

    Args:
        ocorrencias: lista de dicts com 'data' e 'odometro'.
        media_dias: média de dias entre ocorrências (ou None).
        media_km: média de km entre ocorrências (ou None).
        tem_plano: bool — existe plano preventivo oficial.

    Returns:
        dict com:
            nivel: 'ALTO' | 'MÉDIO' | 'BAIXO'
            score: float 0.0–1.0
            fatores: dict detalhando cada fator
    """
    n = len(ocorrencias)
    score_qtd = 0.0
    score_var = 0.0
    score_plano = 1.0 if tem_plano else 0.0

    # Fator 1: Quantidade de dados (mínimo 2 para calcular média, ideal 4+)
    if n >= 4:
        score_qtd = 1.0
    elif n >= 3:
        score_qtd = 0.75
    elif n >= 2:
        score_qtd = 0.5
    elif n >= 1:
        score_qtd = 0.25
    # n == 0: score_qtd = 0.0

    # Fator 2: Variância dos intervalos (quanto menor, mais consistente)
    if n >= 3 and media_dias:
        intervalos = []
        sorted_occ = sorted(ocorrencias, key=lambda x: x['data'])
        for i in range(len(sorted_occ) - 1):
            d = (sorted_occ[i + 1]['data'] - sorted_occ[i]['data']).days
            if d > 0:
                intervalos.append(d)
        if len(intervalos) >= 2:
            cv = statistics.stdev(intervalos) / statistics.mean(intervalos) if statistics.mean(intervalos) > 0 else 1.0
            # CV baixo = alta confiança. CV > 0.5 = baixa.
            score_var = max(0.0, 1.0 - cv)
        else:
            score_var = 0.5  # apenas 2 intervalos, confiança parcial
    elif n >= 2:
        score_var = 0.3  # poucos dados para avaliar variância

    # Score ponderado
    score = (score_qtd * 0.4) + (score_var * 0.3) + (score_plano * 0.3)

    if score >= 0.7:
        nivel = 'ALTO'
    elif score >= 0.4:
        nivel = 'MÉDIO'
    else:
        nivel = 'BAIXO'

    return {
        'nivel': nivel,
        'score': round(score, 2),
        'fatores': {
            'quantidade_dados': round(score_qtd, 2),
            'consistencia_intervalos': round(score_var, 2),
            'plano_oficial': round(score_plano, 2),
            'total_ocorrencias': n,
        },
    }


# ============================================================================
# OCORRÊNCIAS DE MANUTENÇÃO
# ============================================================================
def _coletar_ocorrencias_pecas(viatura):
    """Coleta ocorrências de peças trocadas (via almoxarifado) agrupadas por nome."""
    pecas_qs = (
        RetiradaPecaItem.objects
        .filter(retirada__viatura=viatura)
        .select_related('peca', 'retirada')
        .order_by('-retirada__data_retirada')
    )
    ocorrencias = {}
    for p_item in pecas_qs:
        nome = p_item.peca.nome
        if nome not in ocorrencias:
            ocorrencias[nome] = []
        manut_vinculada = p_item.retirada.manutencao_vinculada.first()
        km = manut_vinculada.odometro if manut_vinculada else Decimal('0')
        ocorrencias[nome].append({
            'data': p_item.retirada.data_retirada.date(),
            'odometro': km or Decimal('0'),
            'origem': 'Peça (Almoxarifado)',
        })
    return ocorrencias


def _coletar_ocorrencias_servicos(viatura):
    """Coleta ocorrências de serviços de oficina agrupadas por tipo/grupo."""
    servicos_qs = (
        ServicoManutencao.objects
        .filter(manutencao__viatura=viatura, manutencao__status='CONCLUIDA')
        .select_related('manutencao')
        .order_by('manutencao__data_conclusao')
    )
    ocorrencias = {}
    for s in servicos_qs:
        grupo = _classificar_servico(s.descricao)
        if grupo not in ocorrencias:
            ocorrencias[grupo] = []
        ocorrencias[grupo].append({
            'data': s.manutencao.data_conclusao or s.manutencao.data_inicio,
            'odometro': s.odometro or s.manutencao.odometro or Decimal('0'),
            'origem': 'Serviço (Oficina)',
        })
    return ocorrencias


def _mesclar_ocorrencias(viatura):
    """Mescla ocorrências de peças e serviços. Garante planos preventivos."""
    ocorrencias = _coletar_ocorrencias_pecas(viatura)
    for grupo, lista in _coletar_ocorrencias_servicos(viatura).items():
        if grupo in ocorrencias:
            ocorrencias[grupo].extend(lista)
        else:
            ocorrencias[grupo] = lista
    planos = PlanoManutencaoPreventiva.objects.filter(modelo=viatura.modelo, ativo=True)
    for plano in planos:
        if plano.descricao not in ocorrencias:
            ocorrencias[plano.descricao] = []
    return ocorrencias


# ============================================================================
# CÁLCULO DE MÉDIAS
# ============================================================================
def _calcular_medias(ocorrencias_ordenadas):
    """Calcula média de dias e km entre ocorrências consecutivas."""
    if len(ocorrencias_ordenadas) < 2:
        return None, None
    diferencas_dias = []
    diferencas_km = []
    for i in range(len(ocorrencias_ordenadas) - 1):
        diferencas_dias.append(
            (ocorrencias_ordenadas[i + 1]['data'] - ocorrencias_ordenadas[i]['data']).days
        )
        km_diff = ocorrencias_ordenadas[i + 1]['odometro'] - ocorrencias_ordenadas[i]['odometro']
        if km_diff > 0:
            diferencas_km.append(km_diff)
    media_dias = int(sum(diferencas_dias) / len(diferencas_dias)) if diferencas_dias else None
    media_km = int(sum(diferencas_km) / len(diferencas_km)) if diferencas_km else None
    return media_dias, media_km


# ============================================================================
# ANÁLISE PREDITIVA DE ITEM ÚNICO (com confiança e taxa km)
# ============================================================================
def _analisar_item(item_nome, ocorrencias, plano, viatura, taxa_km):
    """
    Analisa um único item e gera previsão com nível de confiança.

    Returns:
        dict com dados completos de previsão.
    """
    hoje = timezone.now().date()
    ocorrencias = sorted(ocorrencias, key=lambda x: x['data'])
    media_dias, media_km = _calcular_medias(ocorrencias)

    ultima_data = ocorrencias[-1]['data'] if ocorrencias else viatura.data_cadastro.date()
    ultimo_km = ocorrencias[-1]['odometro'] if ocorrencias else Decimal('0')

    # Definir intervalo de referência (plano > histórico > padrão)
    intervalo_dias_ref = INTERVALO_DIAS_PADRAO
    intervalo_km_ref = INTERVALO_KM_PADRAO

    if plano:
        intervalo_dias_ref = plano.intervalo_dias or (media_dias or intervalo_dias_ref)
        intervalo_km_ref = plano.intervalo_km or (media_km or intervalo_km_ref)
    else:
        if media_dias:
            intervalo_dias_ref = media_dias
        if media_km:
            intervalo_km_ref = media_km

    # Calcular previsão por data e por km
    proxima_data = ultima_data + timedelta(days=intervalo_dias_ref)
    proximo_km = ultimo_km + Decimal(str(intervalo_km_ref))

    # Previsão por taxa de km (quando chegar ao km previsto)
    km_restantes = float(proximo_km - viatura.odometro_atual)
    if taxa_km['media_diaria'] > 0 and km_restantes > 0:
        dias_ate_km = int(km_restantes / taxa_km['media_diaria'])
        data_por_km = hoje + timedelta(days=dias_ate_km)
    else:
        dias_ate_km = None
        data_por_km = None

    # Usar a previsão mais conservadora (a que chegar primeiro)
    if data_por_km and proxima_data:
        data_prevista_final = min(proxima_data, data_por_km)
    else:
        data_prevista_final = proxima_data

    restante_dias = (data_prevista_final - hoje).days if data_prevista_final else 0
    restante_km = km_restantes

    if restante_dias < 0 or restante_km < 0:
        status_prev = 'ATRASADO'
    elif restante_dias <= 15 or restante_km <= 500:
        status_prev = 'ALERTA'
    elif restante_dias <= 30:
        status_prev = 'ATENCAO'
    else:
        status_prev = 'OK'

    # Confiança
    confianca = calcular_confianca(ocorrencias, media_dias, media_km, plano is not None)

    return {
        'nome': item_nome,
        'plano_vinculado': plano,
        'historico_count': len(ocorrencias),
        'ultima_data': ocorrencias[-1]['data'] if ocorrencias else None,
        'ultimo_km': float(ocorrencias[-1]['odometro']) if ocorrencias else None,
        'media_dias_duracao': media_dias,
        'media_km_duracao': media_km,
        'intervalo_dias_ref': intervalo_dias_ref,
        'intervalo_km_ref': intervalo_km_ref,
        'proxima_data': proxima_data,
        'proximo_km': float(proximo_km),
        'data_por_km': data_por_km,
        'data_prevista': data_prevista_final,
        'km_previsto': float(proximo_km),
        'restante_dias': restante_dias,
        'restante_km': round(restante_km, 1),
        'status_prev': status_prev,
        'confianca': confianca,
        'recorrente': len(ocorrencias) >= 2 or plano is not None,
    }


# ============================================================================
# PREVISÕES ESPECÍFICAS (óleo, pneus, revisões)
# ============================================================================
def _buscar_ocorrencias_especificas(viatura, palavras_chave):
    """
    Busca ocorrências de manutenção que correspondam às palavras-chave.

    Procura em:
    - Serviços de oficina (descrição)
    - Manutenções concluídas (descrição)
    - Peças trocadas (nome da peça)

    Returns:
        list[dict] — ocorrências encontradas.
    """
    ocorrencias = []
    occ_set = set()  # evitar duplicatas por (data, km)

    # 1. Serviços de oficina
    servicos = (
        ServicoManutencao.objects
        .filter(manutencao__viatura=viatura, manutencao__status='CONCLUIDA')
        .select_related('manutencao')
        .order_by('manutencao__data_conclusao')
    )
    for s in servicos:
        desc_lower = (s.descricao or '').lower()
        if any(p in desc_lower for p in palavras_chave):
            key = (s.manutencao.data_conclusao or s.manutencao.data_inicio, float(s.odometro or 0))
            if key not in occ_set:
                occ_set.add(key)
                ocorrencias.append({
                    'data': s.manutencao.data_conclusao or s.manutencao.data_inicio,
                    'odometro': s.odometro or s.manutencao.odometro or Decimal('0'),
                    'origem': f'Serviço: {s.descricao[:50]}',
                })

    # 2. Manutenções concluídas (descrição geral)
    manutencoes = (
        Manutencao.objects
        .filter(viatura=viatura, status='CONCLUIDA')
        .order_by('data_conclusao')
    )
    for m in manutencoes:
        desc_lower = (m.descricao or '').lower()
        if any(p in desc_lower for p in palavras_chave):
            data = m.data_conclusao or m.data_inicio
            key = (data, float(m.odometro))
            if key not in occ_set:
                occ_set.add(key)
                ocorrencias.append({
                    'data': data,
                    'odometro': m.odometro or Decimal('0'),
                    'origem': f'Manutenção: {m.descricao[:50]}',
                })

    # 3. Peças trocadas
    pecas = (
        RetiradaPecaItem.objects
        .filter(retirada__viatura=viatura)
        .select_related('peca', 'retirada')
        .order_by('-retirada__data_retirada')
    )
    for p_item in pecas:
        nome_lower = (p_item.peca.nome or '').lower()
        if any(p in nome_lower for p in palavras_chave):
            data = p_item.retirada.data_retirada.date()
            manut = p_item.retirada.manutencao_vinculada.first()
            km = manut.odometro if manut else Decimal('0')
            key = (data, float(km or 0))
            if key not in occ_set:
                occ_set.add(key)
                ocorrencias.append({
                    'data': data,
                    'odometro': km or Decimal('0'),
                    'origem': f'Peça: {p_item.peca.nome}',
                })

    return ocorrencias


def prever_manutencoes_especificas(viatura, taxa_km=None):
    """
    Gera previsões para itens específicos: troca de óleo, pneus, revisões.

    Para cada item, busca o histórico correspondente e calcula a próxima
    data/km prevista com nível de confiança.

    Args:
        viatura: instância de Viatura com modelo pré-carregado.
        taxa_km: dict de calcular_taxa_km() (calculado se None).

    Returns:
        list[dict] — previsões ordenadas por prioridade e urgência.
    """
    if taxa_km is None:
        taxa_km = calcular_taxa_km(viatura)

    hoje = timezone.now().date()
    previsoes = []

    for nome_item, config in PREVISOES_ESPECIFICAS.items():
        ocorrencias = _buscar_ocorrencias_especificas(viatura, config['palavras_chave'])

        # Buscar plano oficial para este item
        plano = PlanoManutencaoPreventiva.objects.filter(
            modelo=viatura.modelo,
            ativo=True,
            descricao__icontains=nome_item.split()[0],  # "Troca" ou "Pneus" ou "Revisão"
        ).first()

        # Intervalos específicos (config > plano > histórico)
        intervalo_dias = config['intervalo_dias_padrao']
        intervalo_km = config['intervalo_km_padrao']
        if plano:
            intervalo_dias = plano.intervalo_dias or intervalo_dias
            intervalo_km = plano.intervalo_km or intervalo_km

        # Construir objeto plano simulado para _analisar_item
        class _PlanoRef:
            intervalo_dias = intervalo_dias
            intervalo_km = intervalo_km
            descricao = nome_item
        plano_ref = _PlanoRef() if not plano else plano

        resultado = _analisar_item(nome_item, ocorrencias, plano_ref, viatura, taxa_km)
        resultado['icone'] = config['icone']
        resultado['prioridade'] = config['prioridade']
        resultado['tipo_previsao'] = 'especifica'
        previsoes.append(resultado)

    # Ordenar: ATRASADO > ALERTA > ATENCAO > OK, depois por dias restantes
    ordem = {'ATRASADO': 0, 'ALERTA': 1, 'ATENCAO': 2, 'OK': 3}
    previsoes.sort(key=lambda x: (ordem.get(x['status_prev'], 9), x['restante_dias']))
    return previsoes


# ============================================================================
# PREVISÃO COMPLETA POR VIATURA (todas as peças/serviços + específicos)
# ============================================================================
def analisar_previsao_viatura(viatura):
    """
    Análise preventiva completa: peças, serviços e previsões específicas.

    Cruza histórico de peças (almoxarifado) + serviços (oficina) com planos
    de manutenção preventiva e gera previsões com confiança.

    Args:
        viatura: instância de Viatura com modelo pré-carregado.

    Returns:
        list[dict] — itens recorrentes ou vinculados a plano oficial.
    """
    taxa_km = calcular_taxa_km(viatura)
    ocorrencias = _mesclar_ocorrencias(viatura)

    planos = {
        p.descricao: p
        for p in PlanoManutencaoPreventiva.objects.filter(modelo=viatura.modelo, ativo=True)
    }

    analise = []
    nomes_especificos = set(PREVISOES_ESPECIFICAS.keys())

    for item_nome, ocorr in ocorrencias.items():
        # Pular se já está nas previsões específicas
        if item_nome in nomes_especificos:
            continue
        plano = planos.get(item_nome)
        resultado = _analisar_item(item_nome, ocorr, plano, viatura, taxa_km)
        resultado['tipo_previsao'] = 'historico'
        if resultado['recorrente']:
            analise.append(resultado)

    # Adicionar previsões específicas
    analise.extend(prever_manutencoes_especificas(viatura, taxa_km))

    # Ordenar: ATRASADO > ALERTA > ATENCAO > OK, depois por dias
    ordem = {'ATRASADO': 0, 'ALERTA': 1, 'ATENCAO': 2, 'OK': 3}
    analise.sort(key=lambda x: (ordem.get(x['status_prev'], 9), x['restante_dias']))
    return analise


# ============================================================================
# PREVISÃO DE FROTA (resumo para todas as viaturas ativas)
# ============================================================================
def prever_frota(status_filtro=None):
    """
    Gera resumo de previsões para toda a frota ativa.

    Para cada viatura, calcula as 3 previsões específicas (óleo, pneus, revisão)
    e retorna um resumo consolidado com alertas.

    Args:
        status_filtro: lista de status para filtrar (padrão: disponíveis + em uso).

    Returns:
        dict com:
            viaturas: list[dict] — resumo por viatura
            alertas_atrasados: int — total de itens atrasados na frota
            alertas_urgentes: int — total de itens em ALERTA (<=15 dias)
            total_previsoes: int — total de previsões geradas
    """
    if status_filtro is None:
        status_filtro = ['DISPONIVEL', 'EM_USO']

    viaturas = (
        Viatura.objects
        .filter(status__in=status_filtro)
        .select_related('modelo', 'modelo__marca')
        .order_by('prefixo')
    )

    resultado_frota = []
    total_atrasados = 0
    total_urgentes = 0
    total_previsoes = 0

    for viatura in viaturas:
        taxa_km = calcular_taxa_km(viatura)
        previsoes = prever_manutencoes_especificas(viatura, taxa_km)

        atrasados = sum(1 for p in previsoes if p['status_prev'] == 'ATRASADO')
        urgentes = sum(1 for p in previsoes if p['status_prev'] == 'ALERTA')
        total_atrasados += atrasados
        total_urgentes += urgentes
        total_previsoes += len(previsoes)

        # Próxima manutenção mais urgente
        proxima = previsoes[0] if previsoes else None

        resultado_frota.append({
            'viatura': viatura,
            'prefixo': viatura.prefixo,
            'modelo': f'{viatura.modelo.marca.nome} {viatura.modelo.nome}',
            'odometro_atual': float(viatura.odometro_atual),
            'taxa_km': taxa_km,
            'previsoes': previsoes,
            'atrasados': atrasados,
            'urgentes': urgentes,
            'proxima_manutencao': {
                'nome': proxima['nome'],
                'data_prevista': proxima['data_prevista'],
                'km_previsto': proxima['km_previsto'],
                'restante_dias': proxima['restante_dias'],
                'status': proxima['status_prev'],
                'confianca': proxima['confianca']['nivel'],
            } if proxima else None,
        })

    # Ordenar: mais urgentes primeiro
    resultado_frota.sort(key=lambda x: (
        -(x['atrasados'] * 10 + x['urgentes']),
        x['proxima_manutencao']['restante_dias'] if x['proxima_manutencao'] else 9999,
    ))

    return {
        'viaturas': resultado_frota,
        'alertas_atrasados': total_atrasados,
        'alertas_urgentes': total_urgentes,
        'total_previsoes': total_previsoes,
        'total_viaturas': len(resultado_frota),
    }


# ============================================================================
# API LEGADA (compatibilidade)
# ============================================================================
def obter_pecas_viatura(viatura):
    """Retorna queryset de peças trocadas na viatura com detalhes."""
    return (
        RetiradaPecaItem.objects
        .filter(retirada__viatura=viatura)
        .select_related('peca', 'retirada', 'retirada__policial')
        .order_by('-retirada__data_retirada')
    )


def total_pecas_trocadas(viatura):
    """Retorna a contagem total de peças trocadas na viatura."""
    return (
        RetiradaPecaItem.objects
        .filter(retirada__viatura=viatura)
        .aggregate(total=Sum('quantidade'))['total']
    ) or 0
