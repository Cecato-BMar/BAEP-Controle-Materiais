from django.db import transaction
from django.utils import timezone

from .models import ConferenciaInventario, DivergenciaInventario, MembroComissaoInventario


RESULTADO_PARA_DIVERGENCIA = {
    'NAO_LOCALIZADO': 'NAO_LOCALIZADO',
    'OUTRA_SECAO': 'OUTRA_SECAO',
    'EXCEDENTE': 'EXCEDENTE',
    'AVARIADO': 'AVARIADO',
    'EM_BAIXA': 'EM_BAIXA',
    'SERIE_DIVERGENTE': 'SERIE_DIVERGENTE',
}

RESULTADOS_CONFORMES = {'CONFIRMADO', 'COM_RESSALVA'}


def usuario_pode_conferir(usuario, ciclo):
    if usuario.is_superuser:
        return True
    return MembroComissaoInventario.objects.filter(
        ciclo=ciclo,
        usuario=usuario,
        ativo=True,
        papel__in=['PRESIDENTE', 'MEMBRO', 'CONFERENTE', 'SUPERVISOR'],
    ).exists()


def usuario_pode_gerir_ciclo(usuario, ciclo):
    if usuario.is_superuser:
        return True
    return MembroComissaoInventario.objects.filter(
        ciclo=ciclo,
        usuario=usuario,
        ativo=True,
        papel__in=['PRESIDENTE', 'SUPERVISOR', 'HOMOLOGADOR'],
    ).exists()


@transaction.atomic
def registrar_conferencia(*, item, usuario, resultado, situacao_fisica='CONFORME',
                          observacoes='', localizacao_encontrada='', numero_serie_encontrado='', evidencia=None):
    """Registra um evento imutável de conferência e atualiza o resumo do item."""
    ciclo = item.ciclo
    if ciclo.bloqueado_para_edicao:
        raise ValueError('O ciclo está homologado ou arquivado e não permite novas conferências.')
    if ciclo.status != 'EM_ANDAMENTO':
        raise ValueError('O ciclo precisa estar em conferência para registrar itens.')
    if not usuario_pode_conferir(usuario, ciclo):
        raise PermissionError('Usuário não está designado para conferir este ciclo.')

    conferencia = ConferenciaInventario.objects.create(
        item=item,
        resultado=resultado,
        situacao_fisica=situacao_fisica,
        observacoes=observacoes,
        localizacao_encontrada=localizacao_encontrada,
        numero_serie_encontrado=numero_serie_encontrado,
        evidencia=evidencia,
        conferido_por=usuario,
    )

    item.conferido = resultado in RESULTADOS_CONFORMES
    item.situacao_fisica_conferida = situacao_fisica
    item.observacoes_conferencia = observacoes
    item.data_conferencia = conferencia.conferido_em
    item.conferido_por = usuario
    item.save(update_fields=[
        'conferido', 'situacao_fisica_conferida', 'observacoes_conferencia',
        'data_conferencia', 'conferido_por',
    ])

    tipo_divergencia = RESULTADO_PARA_DIVERGENCIA.get(resultado)
    if tipo_divergencia:
        DivergenciaInventario.objects.create(
            item=item,
            conferencia_origem=conferencia,
            tipo=tipo_divergencia,
            descricao=observacoes or conferencia.get_resultado_display(),
            responsavel=usuario,
        )

    return conferencia


@transaction.atomic
def encerrar_divergencia(*, divergencia, usuario, status, resolucao):
    if status not in {'REGULARIZADA', 'CONFIRMADA_PARA_BAIXA', 'IMPROCEDENTE'}:
        raise ValueError('Status de encerramento inválido.')
    if not resolucao.strip():
        raise ValueError('Informe a resolução da divergência.')
    if not usuario_pode_gerir_ciclo(usuario, divergencia.item.ciclo):
        raise PermissionError('Usuário não possui permissão para encerrar divergências.')

    divergencia.status = status
    divergencia.resolucao = resolucao.strip()
    divergencia.resolvido_por = usuario
    divergencia.resolvido_em = timezone.now()
    divergencia.save(update_fields=['status', 'resolucao', 'resolvido_por', 'resolvido_em', 'atualizado_em'])
    return divergencia
