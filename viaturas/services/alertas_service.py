"""
viaturas/services/alertas_service.py
Sistema de alertas operacionais da frota.

Gera alertas automáticos para:
- Manutenção vencida (preventiva atrasada por plano ou agendamento)
- Garantia vencendo (validade da garantia nos próximos N dias)
- Pneu próximo do limite (previsão baseada em km/tempo desde a última troca)
- Veículo parado (sem despachos nos últimos N dias)
- Documento vencido ou vencendo (CRLV, Seguro, IPVA, DPVAT)

Cada função retorna uma lista de dicts padronizados:
    {
        'tipo': str — categoria do alerta,
        'nivel': 'CRITICO' | 'ALERTA' | 'ATENCAO',
        'viatura': Viatura | None,
        'prefixo': str,
        'titulo': str — resumo curto,
        'mensagem': str — detalhe do alerta,
        'data_ref': date | None,
        'dias_restantes': int | None,
    }
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import F, Subquery, OuterRef, Max
from django.utils import timezone

from viaturas.models import (
    Viatura, Manutencao, DespachoViatura, DocumentoViatura,
    PlanoManutencaoPreventiva, StatusViatura, StatusManutencao,
)
from viaturas.services.previsao_service import (
    prever_manutencoes_especificas,
    calcular_taxa_km,
)


# ============================================================================
# ESTRUTURA PADRÃO DE ALERTA
# ============================================================================
def _alerta(tipo, nivel, viatura, titulo, mensagem, data_ref=None, dias_restantes=None):
    """Constrói um dict de alerta padronizado."""
    return {
        'tipo': tipo,
        'nivel': nivel,
        'viatura': viatura,
        'prefixo': viatura.prefixo if viatura else '',
        'titulo': titulo,
        'mensagem': mensagem,
        'data_ref': data_ref,
        'dias_restantes': dias_restantes,
    }


# ============================================================================
# 1. MANUTENÇÃO VENCIDA
# ============================================================================
def alertas_manutencao_vencida():
    """
    Detecta manutenções vencidas em 2 categorias:

    a) Agendamentos atrasados — manutenções AGENDADA com data_inicio < hoje.
    b) Preventiva por plano — viaturas ativas cuja última preventiva concluída
       ultrapassou o intervalo de dias ou km do plano cadastrado.

    Returns:
        list[dict] — alertas gerados.
    """
    hoje = timezone.now().date()
    alertas = []

    # --- (a) Agendamentos atrasados ---
    agendamentos_atrasados = (
        Manutencao.objects
        .filter(
            status=StatusManutencao.AGENDADA,
            data_inicio__lt=hoje,
        )
        .select_related('viatura', 'viatura__modelo', 'viatura__modelo__marca')
        .order_by('data_inicio')
    )
    for m in agendamentos_atrasados:
        dias_atraso = (hoje - m.data_inicio).days
        nivel = 'CRITICO' if dias_atraso > 15 else 'ALERTA'
        alertas.append(_alerta(
            tipo='MANUTENCAO_VENCIDA',
            nivel=nivel,
            viatura=m.viatura,
            titulo=f'Agendamento atrasado há {dias_atraso} dias',
            mensagem=(
                f'{m.viatura.prefixo} — {m.descricao[:80]}. '
                f'Agendada para {m.data_inicio.strftime("%d/%m/%Y")}. '
                f'OS: {m.ordem_servico or "N/A"}.'
            ),
            data_ref=m.data_inicio,
            dias_restantes=-dias_atraso,
        ))

    # --- (b) Preventiva por plano (intervalo excedido) ---
    planos_ativos = (
        PlanoManutencaoPreventiva.objects
        .filter(ativo=True)
        .select_related('modelo')
    )
    if planos_ativos.exists():
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
            .select_related('modelo', 'modelo__marca')
            .annotate(
                ultima_prev_data=Subquery(ultima_prev_sub.values('data_conclusao')[:1]),
                ultima_prev_km=Subquery(ultima_prev_sub.values('odometro')[:1]),
            )
        )

        for vtr in viaturas_ativas:
            planos = planos_por_modelo.get(vtr.modelo_id, [])
            for plano in planos:
                motivo = None

                # Verificar por km
                if plano.intervalo_km and vtr.ultima_prev_km is not None:
                    km_desde = vtr.odometro_atual - vtr.ultima_prev_km
                    if km_desde >= Decimal(str(plano.intervalo_km)):
                        motivo = (
                            f'{km_desde:,.0f} km desde a última {plano.descricao} '
                            f'(limite: {plano.intervalo_km:,.0f} km)'
                        )

                # Verificar por dias
                if plano.intervalo_dias and vtr.ultima_prev_data is not None:
                    dias_desde = (hoje - vtr.ultima_prev_data).days
                    if dias_desde >= plano.intervalo_dias:
                        excesso = dias_desde - plano.intervalo_dias
                        nivel = 'CRITICO' if excesso > 30 else 'ALERTA'
                        motivo = (
                            f'{dias_desde} dias desde a última {plano.descricao} '
                            f'(intervalo: {plano.intervalo_dias} dias, '
                            f'{excesso} dias em atraso)'
                        )
                        alertas.append(_alerta(
                            tipo='MANUTENCAO_VENCIDA',
                            nivel=nivel,
                            viatura=vtr,
                            titulo=f'{plano.descricao} atrasada',
                            mensagem=f'{vtr.prefixo} — {motivo}',
                            data_ref=vtr.ultima_prev_data,
                            dias_restantes=-excesso,
                        ))

                # Nunca realizou
                if vtr.ultima_prev_data is None and (plano.intervalo_km or plano.intervalo_dias):
                    alertas.append(_alerta(
                        tipo='MANUTENCAO_VENCIDA',
                        nivel='ATENCAO',
                        viatura=vtr,
                        titulo=f'{plano.descricao} nunca realizada',
                        mensagem=(
                            f'{vtr.prefixo} — Nenhuma preventiva registrada '
                            f'para {plano.descricao}.'
                        ),
                        data_ref=None,
                        dias_restantes=None,
                    ))

    return alertas


# ============================================================================
# 2. GARANTIA VENCENDO
# ============================================================================
def alertas_garantia_vencendo(dias_alerta=30, dias_atencao=60):
    """
    Detecta manutenções concluídas com garantia prestes a vencer.

    Gera alerta CRÍTICO para garantias já vencidas (nos últimos 30 dias),
    ALERTA para as que vencem em até N dias, ATENCAO para até M dias.

    Args:
        dias_alerta: janela de alerta (padrão 30 dias).
        dias_atencao: janela de atenção (padrão 60 dias).

    Returns:
        list[dict] — alertas gerados.
    """
    hoje = timezone.now().date()
    limite_alerta = hoje + timedelta(days=dias_alerta)
    limite_atencao = hoje + timedelta(days=dias_atencao)

    manutencoes = (
        Manutencao.objects
        .filter(
            status='CONCLUIDA',
            data_validade_garantia__isnull=False,
            data_validade_garantia__lte=limite_atencao,
        )
        .select_related('viatura', 'viatura__modelo', 'viatura__modelo__marca')
        .order_by('data_validade_garantia')
    )

    alertas = []
    for m in manutencoes:
        dias_restantes = (m.data_validade_garantia - hoje).days

        if dias_restantes < 0:
            # Garantia já venceu
            nivel = 'CRITICO'
            titulo = f'Garantia vencida há {abs(dias_restantes)} dias'
        elif dias_restantes <= dias_alerta:
            nivel = 'ALERTA'
            titulo = f'Garantia vence em {dias_restantes} dias'
        else:
            nivel = 'ATENCAO'
            titulo = f'Garantia vence em {dias_restantes} dias'

        # Detalhe da garantia
        detalhe_km = ''
        if m.km_validade_garantia:
            km_restantes = m.km_validade_garantia - m.viatura.odometro_atual
            detalhe_km = f' | Km restante: {float(km_restantes):,.0f} km'

        alertas.append(_alerta(
            tipo='GARANTIA_VENCENDO',
            nivel=nivel,
            viatura=m.viatura,
            titulo=titulo,
            mensagem=(
                f'{m.viatura.prefixo} — {m.descricao[:80]}. '
                f'Validade: {m.data_validade_garantia.strftime("%d/%m/%Y")}.'
                f'{detalhe_km}'
            ),
            data_ref=m.data_validade_garantia,
            dias_restantes=dias_restantes,
        ))

    return alertas


# ============================================================================
# 3. PNEU PRÓXIMO DO LIMITE
# ============================================================================
def alertas_pneu_proximo_limite(dias_alerta=30, km_alerta=2000):
    """
    Usa o motor de previsão para detectar pneus próximos do limite.

    Para cada viatura ativa, consulta a previsão de "Pneus" e gera alerta
    se estiver ATRASADO, em ALERTA (<=15 dias) ou ATENCAO (<=30 dias).

    Args:
        dias_alerta: dias restantes para considerar alerta (padrão 30).
        km_alerta: km restantes para considerar alerta (padrão 2000).

    Returns:
        list[dict] — alertas gerados.
    """
    viaturas = (
        Viatura.objects
        .filter(status__in=['DISPONIVEL', 'EM_USO'])
        .select_related('modelo', 'modelo__marca')
        .order_by('prefixo')
    )

    alertas = []
    for viatura in viaturas:
        taxa_km = calcular_taxa_km(viatura)
        previsoes = prever_manutencoes_especificas(viatura, taxa_km)

        # Encontrar previsão de pneus
        for prev in previsoes:
            if prev['nome'] != 'Pneus':
                continue

            status_prev = prev['status_prev']
            dias = prev['restante_dias']
            km = prev['restante_km']

            if status_prev == 'ATRASADO':
                nivel = 'CRITICO'
                titulo = 'Pneus com troca atrasada'
                mensagem = (
                    f'{viatura.prefixo} — Troca de pneus atrasada. '
                    f'Última troca: {prev["ultima_data"].strftime("%d/%m/%Y") if prev["ultima_data"] else "sem registro"}. '
                    f'Confiança: {prev["confianca"]["nivel"]}.'
                )
            elif status_prev == 'ALERTA' or (dias is not None and dias <= dias_alerta) or (km is not None and km <= km_alerta):
                nivel = 'ALERTA'
                titulo = f'Pneus: troca em {dias} dias ou {km:,.0f} km'
                mensagem = (
                    f'{viatura.prefixo} — Pneus próximos do limite. '
                    f'Previsto: {prev["data_prevista"].strftime("%d/%m/%Y") if prev["data_prevista"] else "N/A"}. '
                    f'Km restante: {km:,.0f}. Confiança: {prev["confianca"]["nivel"]}.'
                )
            elif status_prev == 'ATENCAO':
                nivel = 'ATENCAO'
                titulo = f'Pneus: atenção — troca em {dias} dias'
                mensagem = (
                    f'{viatura.prefixo} — Programar troca de pneus. '
                    f'Previsto: {prev["data_prevista"].strftime("%d/%m/%Y") if prev["data_prevista"] else "N/A"}. '
                    f'Km restante: {km:,.0f}.'
                )
            else:
                continue  # OK, sem alerta

            alertas.append(_alerta(
                tipo='PNEU_PROXIMO_LIMITE',
                nivel=nivel,
                viatura=viatura,
                titulo=titulo,
                mensagem=mensagem,
                data_ref=prev.get('data_prevista'),
                dias_restantes=dias,
            ))
            break  # apenas 1 alerta de pneu por viatura

    return alertas


# ============================================================================
# 4. VEÍCULO PARADO
# ============================================================================
def alertas_veiculo_parado(dias_parado=7, status_considerados=None):
    """
    Detecta viaturas sem despachos nos últimos N dias.

    Considera apenas viaturas que deveriam estar ativas (DISPONIVEL).
    Viaturas em manutenção ou baixadas são ignoradas.

    Args:
        dias_parado: dias sem despacho para considerar parado (padrão 7).
        status_considerados: lista de status para checar (padrão: DISPONIVEL).

    Returns:
        list[dict] — alertas gerados.
    """
    if status_considerados is None:
        status_considerados = [StatusViatura.DISPONIVEL]

    hoje = timezone.now().date()
    limite = hoje - timedelta(days=dias_parado)

    # Subquery: último despacho de cada viatura
    ultimo_despacho_sub = (
        DespachoViatura.objects
        .filter(viatura=OuterRef('pk'))
        .order_by('-data_saida')
    )

    viaturas = (
        Viatura.objects
        .filter(status__in=status_considerados)
        .select_related('modelo', 'modelo__marca')
        .annotate(
            ultimo_despacho=Subquery(ultimo_despacho_sub.values('data_saida')[:1]),
        )
        .order_by('prefixo')
    )

    alertas = []
    for vtr in viaturas:
        if vtr.ultimo_despacho is None:
            # Nunca foi despachada
            dias_sem = (hoje - vtr.data_cadastro.date()).days if vtr.data_cadastro else 0
            nivel = 'ATENCAO'
            titulo = f'Viatura sem despachos desde o cadastro'
            mensagem = (
                f'{vtr.prefixo} — {vtr.modelo.marca.nome} {vtr.modelo.nome}. '
                f'Cadastrada em {vtr.data_cadastro.strftime("%d/%m/%Y") if vtr.data_cadastro else "N/A"} '
                f'({dias_sem} dias). Nenhum despacho registrado.'
            )
        elif vtr.ultimo_despacho.date() < limite:
            dias_sem = (hoje - vtr.ultimo_despacho.date()).days
            nivel = 'ALERTA' if dias_sem >= 14 else 'ATENCAO'
            titulo = f'Viatura parada há {dias_sem} dias'
            mensagem = (
                f'{vtr.prefixo} — {vtr.modelo.marca.nome} {vtr.modelo.nome}. '
                f'Último despacho: {vtr.ultimo_despacho.strftime("%d/%m/%Y")}.'
            )
        else:
            continue  # dentro do limite

        alertas.append(_alerta(
            tipo='VEICULO_PARADO',
            nivel=nivel,
            viatura=vtr,
            titulo=titulo,
            mensagem=mensagem,
            data_ref=vtr.ultimo_despacho.date() if vtr.ultimo_despacho else None,
            dias_restantes=None,
        ))

    return alertas


# ============================================================================
# 5. DOCUMENTOS VENCIDOS OU VENCENDO (bônus)
# ============================================================================
def alertas_documentos(dias_alerta=30):
    """
    Detecta documentos vencidos e vencendo nos próximos N dias.

    Returns:
        list[dict] — alertas gerados.
    """
    hoje = timezone.now().date()
    limite = hoje + timedelta(days=dias_alerta)

    documentos = (
        DocumentoViatura.objects
        .filter(
            ativo=True,
            data_vencimento__isnull=False,
            data_vencimento__lte=limite,
        )
        .select_related('viatura', 'viatura__modelo', 'viatura__modelo__marca')
        .order_by('data_vencimento')
    )

    alertas = []
    for doc in documentos:
        dias_restantes = (doc.data_vencimento - hoje).days
        tipo_display = doc.get_tipo_display()

        if dias_restantes < 0:
            nivel = 'CRITICO'
            titulo = f'{tipo_display} vencido há {abs(dias_restantes)} dias'
        elif dias_restantes <= 15:
            nivel = 'ALERTA'
            titulo = f'{tipo_display} vence em {dias_restantes} dias'
        else:
            nivel = 'ATENCAO'
            titulo = f'{tipo_display} vence em {dias_restantes} dias'

        alertas.append(_alerta(
            tipo='DOCUMENTO_VENCENDO',
            nivel=nivel,
            viatura=doc.viatura,
            titulo=titulo,
            mensagem=(
                f'{doc.viatura.prefixo} — {tipo_display} '
                f'(Nº {doc.numero_documento or "N/A"}). '
                f'Vencimento: {doc.data_vencimento.strftime("%d/%m/%Y")}.'
            ),
            data_ref=doc.data_vencimento,
            dias_restantes=dias_restantes,
        ))

    return alertas


# ============================================================================
# CONSOLIDADOR — TODOS OS ALERTAS
# ============================================================================
def gerar_todos_alertas():
    """
    Executa todas as verificações e retorna um resumo consolidado.

    Returns:
        dict com:
            alertas: list[dict] — todos os alertas ordenados por nível.
            resumo: dict — contagem por tipo e nível.
            total: int — total de alertas.
    """
    todos = []
    todos.extend(alertas_manutencao_vencida())
    todos.extend(alertas_garantia_vencendo())
    todos.extend(alertas_pneu_proximo_limite())
    todos.extend(alertas_veiculo_parado())
    todos.extend(alertas_documentos())

    # Ordenar: CRITICO > ALERTA > ATENCAO
    ordem_nivel = {'CRITICO': 0, 'ALERTA': 1, 'ATENCAO': 2}
    todos.sort(key=lambda a: (ordem_nivel.get(a['nivel'], 9), a.get('dias_restantes') or 0))

    # Resumo
    resumo = {}
    for a in todos:
        key = f"{a['tipo']}_{a['nivel']}"
        resumo[key] = resumo.get(key, 0) + 1

    # Contagem por tipo
    por_tipo = {}
    for a in todos:
        por_tipo[a['tipo']] = por_tipo.get(a['tipo'], 0) + 1

    # Contagem por nível
    por_nivel = {'CRITICO': 0, 'ALERTA': 0, 'ATENCAO': 0}
    for a in todos:
        por_nivel[a['nivel']] = por_nivel.get(a['nivel'], 0) + 1

    return {
        'alertas': todos,
        'resumo': resumo,
        'por_tipo': por_tipo,
        'por_nivel': por_nivel,
        'total': len(todos),
    }
