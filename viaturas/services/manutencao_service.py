"""
viaturas/services/manutencao_service.py
Serviços de gestão do ciclo de vida de manutenções.

Regras de negócio extraídas de views.py e centralizadas aqui.
Toda operação que modifica manutenção deve passar por este service.
"""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from viaturas.models import (
    Manutencao, Viatura, StatusManutencao, StatusViatura,
)
from viaturas.services.manutencao_historico import (
    registrar_abertura,
    registrar_alteracoes_form,
    registrar_cancelamento,
    registrar_conclusao,
)


# ============================================================================
# VALIDAÇÕES
# ============================================================================
_STATUS_CONCLUIVEIS = frozenset({'ABERTA', 'AGUARDANDO_PECA'})
_STATUS_CANCELAVEIS = frozenset({'ABERTA', 'AGUARDANDO_PECA', 'AGENDADA'})


def _pode_concluir(manutencao):
    return manutencao.status in _STATUS_CONCLUIVEIS


def _pode_cancelar(manutencao):
    return manutencao.status in _STATUS_CANCELAVEIS


# ============================================================================
# OPERAÇÕES DE CICLO DE VIDA
# ============================================================================
@transaction.atomic
def criar_manutencao(
    viatura,
    usuario,
    *,
    tipo,
    data_inicio,
    odometro,
    descricao,
    oficina_fk=None,
    oficina=None,
    ordem_servico=None,
    custo_pecas=Decimal('0'),
    custo_mao_obra=Decimal('0'),
    localizacao_fisica=None,
    status=None,
    **campos_extras,
):
    """
    Cria uma nova manutenção (corretiva ou preventiva) e registra no histórico.

    Atualiza automaticamente o status e a localização da viatura via save() do model.

    Args:
        viatura: instância de Viatura.
        usuario: User que está registrando.
        tipo: 'PREVENTIVA' ou 'CORRETIVA'.
        data_inicio: data de entrada na oficina.
        odometro: odômetro no momento da entrada.
        descricao: problema relatado.
        localizacao_fisica: localização escolhida pelo usuário (override).

    Returns:
        Manutencao criada.
    """
    campos = dict(
        viatura=viatura,
        tipo=tipo,
        status=status or StatusManutencao.ABERTA,
        data_inicio=data_inicio,
        odometro=odometro,
        descricao=descricao,
        oficina_fk=oficina_fk,
        oficina=oficina or '',
        ordem_servico=ordem_servico or '',
        custo_pecas=custo_pecas,
        custo_mao_obra=custo_mao_obra,
        registrado_por=usuario,
        **campos_extras,
    )
    manutencao = Manutencao(**campos)
    manutencao.save()  # model.save() atualiza status/localização da viatura

    registrar_abertura(manutencao, usuario)

    # Override de localização escolhido na tela
    if localizacao_fisica and viatura.localizacao != localizacao_fisica:
        viatura.localizacao = localizacao_fisica
        viatura.save(update_fields=['localizacao'])

    return manutencao


@transaction.atomic
def agendar_manutencao(
    viatura,
    usuario,
    *,
    data_inicio,
    descricao,
    tipo='PREVENTIVA',
    oficina_fk=None,
    oficina=None,
    ordem_servico=None,
):
    """
    Cria um agendamento de manutenção futura.

    Usa o odômetro atual da viatura como referência.

    Returns:
        Manutencao com status=AGENDADA.
    """
    return criar_manutencao(
        viatura,
        usuario,
        tipo=tipo,
        data_inicio=data_inicio,
        odometro=viatura.odometro_atual,
        descricao=descricao,
        oficina_fk=oficina_fk,
        oficina=oficina,
        ordem_servico=ordem_servico,
        status=StatusManutencao.AGENDADA,
    )


@transaction.atomic
def converter_agendamento(agendamento, usuario):
    """
    Converte um agendamento (AGENDADA) em manutenção ativa (ABERTA).

    Atualiza data_inicio para hoje.

    Args:
        agendamento: Manutencao com status=AGENDADA.
        usuario: User que está convertendo.

    Raises:
        ValidationError: se o agendamento não estiver em status AGENDADA.

    Returns:
        Manutencao atualizada.
    """
    if agendamento.status != StatusManutencao.AGENDADA:
        raise ValidationError(
            f'Não é possível converter agendamento com status "{agendamento.get_status_display()}".'
        )

    instancia_anterior = Manutencao.objects.get(pk=agendamento.pk)
    agendamento.status = StatusManutencao.ABERTA
    agendamento.data_inicio = timezone.now().date()
    agendamento.save()
    registrar_alteracoes_form(agendamento, usuario, instancia_anterior)
    return agendamento


@transaction.atomic
def atualizar_manutencao(manutencao, usuario, *, campos_alterados, localizacao_fisica=None):
    """
    Atualiza campos de uma manutenção existente e registra mudanças no histórico.

    Args:
        manutencao: instância já persistida com novos valores.
        usuario: User que atualizou.
        campos_alterados: dict {campo: valor_anterior} para diff.
        localizacao_fisica: localização escolhida na tela (override opcional).

    Returns:
        Manutencao atualizada.
    """
    # Construir instância "anterior" virtual a partir dos valores salvos
    class _Snapshot:
        pass

    snapshot = _Snapshot()
    for campo, valor_antigo in campos_alterados.items():
        setattr(snapshot, campo, valor_antigo)
    # Copiar campos não alterados da instância atual para o snapshot funcionar no diff
    for campo in ('viatura', 'tipo', 'status', 'data_inicio', 'data_conclusao',
                  'odometro', 'descricao', 'oficina', 'oficina_fk',
                  'custo_pecas', 'custo_mao_obra', 'ordem_servico',
                  'servicos_executados_corretamente', 'detalhamento_servicos',
                  'detalhamento_pecas_garantia', 'data_validade_garantia',
                  'km_validade_garantia', 'parecer_aprovacao', 'motivo_cancelamento'):
        if not hasattr(snapshot, campo):
            setattr(snapshot, campo, getattr(manutencao, campo, None))

    registrar_alteracoes_form(manutencao, usuario, snapshot)

    if localizacao_fisica and manutencao.viatura.localizacao != localizacao_fisica:
        manutencao.viatura.localizacao = localizacao_fisica
        manutencao.viatura.save(update_fields=['localizacao'])

    return manutencao


@transaction.atomic
def concluir_manutencao(manutencao, usuario, *, dados_conclusao=None):
    """
    Conclui uma manutenção com aprovação formal.

    Args:
        manutencao: Manutencao com status ABERTA ou AGUARDANDO_PECA.
        usuario: User que está aprovando.
        dados_conclusao: dict opcional com campos extras
            (servicos_executados_corretamente, detalhamento_servicos, etc.).

    Raises:
        ValidationError: se o status não permite conclusão.

    Returns:
        Manutencao concluída.
    """
    if not _pode_concluir(manutencao):
        raise ValidationError(
            f'Não é possível concluir manutenção com status "{manutencao.get_status_display()}". '
            f'Use "Em Aberto" ou "Aguardando Peça".'
        )

    instancia_anterior = Manutencao.objects.get(pk=manutencao.pk)

    # Aplicar dados extras (se vierem do form)
    if dados_conclusao:
        for campo, valor in dados_conclusao.items():
            setattr(manutencao, campo, valor)

    agora = timezone.now()
    manutencao.data_conclusao = agora.date()
    manutencao.status = StatusManutencao.CONCLUIDA
    manutencao.aprovado_por = usuario
    manutencao.data_aprovacao = agora
    manutencao.save()

    registrar_alteracoes_form(manutencao, usuario, instancia_anterior)
    registrar_conclusao(manutencao, usuario)
    return manutencao


@transaction.atomic
def cancelar_manutencao(manutencao, usuario, *, motivo=''):
    """
    Cancela uma manutenção (ou agendamento) com justificativa.

    Args:
        manutencao: Manutencao com status cancelável.
        usuario: User que cancelou.
        motivo: justificativa do cancelamento.

    Raises:
        ValidationError: se o status não permite cancelamento.

    Returns:
        Manutencao cancelada.
    """
    if not _pode_cancelar(manutencao):
        raise ValidationError(
            f'Não é possível cancelar manutenção com status "{manutencao.get_status_display()}".'
        )

    agora = timezone.now()
    manutencao.status = StatusManutencao.CANCELADA
    manutencao.cancelado_por = usuario
    manutencao.data_cancelamento = agora
    manutencao.motivo_cancelamento = motivo
    manutencao.save()

    registrar_cancelamento(manutencao, usuario, motivo)
    return manutencao


# ============================================================================
# CONSULTAS
# ============================================================================
def listar_por_status(status='abertas'):
    """
    Retorna queryset de manutenções filtradas por categoria de status.

    Args:
        status: 'abertas' | 'concluidas' | 'agendadas' | 'todas'.
    """
    qs = Manutencao.objects.select_related('viatura', 'oficina_fk').order_by('-data_inicio')
    if status == 'abertas':
        return qs.filter(status__in=['ABERTA', 'AGUARDANDO_PECA'])
    if status == 'concluidas':
        return qs.filter(status__in=['CONCLUIDA', 'CANCELADA'])
    if status == 'agendadas':
        return qs.filter(status='AGENDADA')
    return qs


def pode_reabrir_viatura(viatura):
    """
    Verifica se não há manutenções ativas bloqueando a liberação da viatura.

    Returns:
        True se não há manutenções ABERTA/AGUARDANDO_PECA para essa viatura.
    """
    return not Manutencao.objects.filter(
        viatura=viatura,
        status__in=[StatusManutencao.ABERTA, StatusManutencao.AGUARDANDO_PECA],
    ).exists()
