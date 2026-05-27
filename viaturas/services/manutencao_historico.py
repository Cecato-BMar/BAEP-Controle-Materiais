"""Serviços de auditoria append-only para manutenções de viaturas."""
from decimal import Decimal

from django.db import transaction

from viaturas.models import Manutencao, RegistroHistoricoManutencao, ServicoManutencao

LABELS_CAMPOS = {
    'viatura': 'Viatura',
    'tipo': 'Tipo de Manutenção',
    'status': 'Status',
    'data_inicio': 'Data de Início',
    'data_conclusao': 'Data de Conclusão',
    'odometro': 'Odômetro',
    'descricao': 'Motivo / Problema',
    'oficina': 'Oficina (texto)',
    'oficina_fk': 'Oficina',
    'custo_pecas': 'Custo Peças',
    'custo_mao_obra': 'Custo Mão de Obra',
    'ordem_servico': 'O.S. Nº',
    'servicos_executados_corretamente': 'Serviços Aprovados',
    'detalhamento_servicos': 'Detalhamento dos Serviços',
    'detalhamento_pecas_garantia': 'Peças / Garantia',
    'data_validade_garantia': 'Validade Garantia (Data)',
    'km_validade_garantia': 'Validade Garantia (Km)',
    'nota_fiscal': 'Nota Fiscal',
    'termo_garantia': 'Termo de Garantia',
    'parecer_aprovacao': 'Parecer de Aprovação',
    'motivo_cancelamento': 'Motivo do Cancelamento',
}

CAMPOS_SERVICO = frozenset({
    'detalhamento_servicos',
    'detalhamento_pecas_garantia',
    'custo_pecas',
    'custo_mao_obra',
    'odometro',
})


def _formatar_valor(valor):
    if valor is None or valor == '':
        return '(vazio)'
    if isinstance(valor, bool):
        return 'Sim' if valor else 'Não'
    if isinstance(valor, Decimal):
        return f'{valor:.2f}'
    if hasattr(valor, 'pk'):
        return str(valor)
    return str(valor)


def _extrair_novo_texto(anterior, novo):
    """Retorna o trecho novo quando o usuário acrescenta texto; None se não houve mudança."""
    ant = (anterior or '').strip()
    nov = (novo or '').strip()
    if not nov or nov == ant:
        return None
    if ant and nov.startswith(ant):
        delta = nov[len(ant):].strip()
        return delta or nov
    return nov


def sincronizar_resumo_servicos(manutencao):
    """Atualiza o campo agregado detalhamento_servicos a partir dos registros imutáveis."""
    linhas = []
    for s in manutencao.servicos.order_by('data_registro'):
        bloco = s.descricao.strip()
        if s.detalhamento and s.detalhamento.strip() != s.descricao.strip():
            bloco = f"{bloco}\n{s.detalhamento.strip()}"
        if s.pecas_garantia:
            bloco = f"{bloco}\n[Peças/Garantia] {s.pecas_garantia.strip()}"
        linhas.append(bloco)
    texto = '\n\n---\n\n'.join(linhas)
    if manutencao.detalhamento_servicos != texto:
        Manutencao.objects.filter(pk=manutencao.pk).update(detalhamento_servicos=texto or None)


@transaction.atomic
def registrar_servico(
    manutencao,
    usuario,
    descricao,
    *,
    detalhamento=None,
    pecas_garantia=None,
    custo_pecas=None,
    custo_mao_obra=None,
    odometro=None,
):
    """Cria um registro imutável de serviço e o evento correspondente no histórico."""
    servico = ServicoManutencao.objects.create(
        manutencao=manutencao,
        descricao=descricao.strip(),
        detalhamento=detalhamento.strip() if detalhamento else None,
        pecas_garantia=pecas_garantia.strip() if pecas_garantia else None,
        custo_pecas=custo_pecas if custo_pecas is not None else Decimal('0'),
        custo_mao_obra=custo_mao_obra if custo_mao_obra is not None else Decimal('0'),
        odometro=odometro or manutencao.odometro,
        status_na_epoca=manutencao.status,
        registrado_por=usuario,
    )
    RegistroHistoricoManutencao.objects.create(
        manutencao=manutencao,
        tipo='SERVICO',
        titulo='Serviço registrado',
        descricao=descricao.strip(),
        servico=servico,
        metadados={
            'custo_pecas': str(servico.custo_pecas),
            'custo_mao_obra': str(servico.custo_mao_obra),
            'odometro': str(servico.odometro) if servico.odometro else None,
        },
        registrado_por=usuario,
    )
    sincronizar_resumo_servicos(manutencao)
    return servico


def registrar_evento(manutencao, usuario, tipo, titulo, descricao='', *, servico=None, metadados=None):
    return RegistroHistoricoManutencao.objects.create(
        manutencao=manutencao,
        tipo=tipo,
        titulo=titulo,
        descricao=descricao,
        servico=servico,
        metadados=metadados,
        registrado_por=usuario,
    )


def registrar_abertura(manutencao, usuario):
    motivo = (manutencao.descricao or '').strip() or 'Manutenção aberta'
    registrar_evento(
        manutencao,
        usuario,
        'ABERTURA',
        'Abertura da manutenção',
        descricao=(
            f"Motivo: {motivo}. "
            f"Tipo: {manutencao.get_tipo_display()}. "
            f"Status: {manutencao.get_status_display()}. "
            f"O.S.: {manutencao.ordem_servico or 'não informada'}."
        ),
        metadados={
            'tipo': manutencao.tipo,
            'status': manutencao.status,
            'odometro': str(manutencao.odometro),
            'motivo': motivo,
        },
    )
    if manutencao.detalhamento_servicos and manutencao.detalhamento_servicos.strip():
        registrar_servico(
            manutencao,
            usuario,
            manutencao.detalhamento_servicos.strip(),
            detalhamento=manutencao.detalhamento_servicos.strip(),
            pecas_garantia=manutencao.detalhamento_pecas_garantia,
            custo_pecas=manutencao.custo_pecas,
            custo_mao_obra=manutencao.custo_mao_obra,
            odometro=manutencao.odometro,
        )


def registrar_alteracoes_form(manutencao, usuario, instancia_anterior):
    """
    Compara instância anterior com a atual e gera:
    - um ServicoManutencao para cada alteração em campos de serviço;
    - um evento ATUALIZACAO/STATUS para demais campos.
    """
    if not instancia_anterior:
        return

    mudancas_servico = []
    mudancas_admin = []

    for campo in LABELS_CAMPOS:
        antigo = getattr(instancia_anterior, campo, None)
        novo = getattr(manutencao, campo, None)
        if _formatar_valor(antigo) == _formatar_valor(novo):
            continue
        rotulo = LABELS_CAMPOS[campo]
        if campo in CAMPOS_SERVICO:
            mudancas_servico.append((campo, rotulo, antigo, novo))
        else:
            mudancas_admin.append((campo, rotulo, antigo, novo))

    if 'detalhamento_servicos' in {c[0] for c in mudancas_servico}:
        _, _, antigo, novo = next(c for c in mudancas_servico if c[0] == 'detalhamento_servicos')
        texto_novo = _extrair_novo_texto(antigo, novo)
        if texto_novo:
            pecas = None
            custo_p = None
            custo_m = None
            for c, _, a, n in mudancas_servico:
                if c == 'detalhamento_pecas_garantia':
                    pecas = _extrair_novo_texto(a, n) or (n or '').strip() or None
                elif c == 'custo_pecas':
                    custo_p = n
                elif c == 'custo_mao_obra':
                    custo_m = n
            registrar_servico(
                manutencao,
                usuario,
                texto_novo,
                detalhamento=texto_novo,
                pecas_garantia=pecas,
                custo_pecas=custo_p,
                custo_mao_obra=custo_m,
            )
        mudancas_servico = [c for c in mudancas_servico if c[0] != 'detalhamento_servicos']

    for campo, rotulo, antigo, novo in mudancas_servico:
        if campo == 'detalhamento_pecas_garantia':
            texto = _extrair_novo_texto(antigo, novo) or (novo or '').strip()
            if texto:
                registrar_servico(
                    manutencao,
                    usuario,
                    f'Peças / garantia: {texto}',
                    pecas_garantia=texto,
                )
        elif campo in ('custo_pecas', 'custo_mao_obra', 'odometro'):
            registrar_servico(
                manutencao,
                usuario,
                f'Atualização de {rotulo}: {_formatar_valor(antigo)} → {_formatar_valor(novo)}',
                **{campo: novo},
            )

    if not mudancas_admin:
        return

    linhas = [
        f'{rotulo}: {_formatar_valor(antigo)} → {_formatar_valor(novo)}'
        for _, rotulo, antigo, novo in mudancas_admin
    ]
    status_alterado = any(c[0] == 'status' for c in mudancas_admin)
    tipo_evento = 'STATUS' if status_alterado else 'ATUALIZACAO'
    titulo = 'Mudança de status' if status_alterado else 'Atualização administrativa'

    registrar_evento(
        manutencao,
        usuario,
        tipo_evento,
        titulo,
        descricao='\n'.join(linhas),
        metadados={
            'alteracoes': [
                {'campo': c, 'rotulo': r, 'anterior': _formatar_valor(a), 'novo': _formatar_valor(n)}
                for c, r, a, n in mudancas_admin
            ],
        },
    )


def registrar_conclusao(manutencao, usuario):
    registrar_evento(
        manutencao,
        usuario,
        'CONCLUSAO',
        'Manutenção concluída',
        descricao=(
            f"Aprovado por {usuario.get_full_name() or usuario.username}. "
            f"Custo total: R$ {manutencao.custo_total:.2f}."
        ),
        metadados={
            'data_conclusao': str(manutencao.data_conclusao),
            'custo_total': str(manutencao.custo_total),
        },
    )


def registrar_cancelamento(manutencao, usuario, motivo=''):
    registrar_evento(
        manutencao,
        usuario,
        'CANCELAMENTO',
        'Manutenção cancelada',
        descricao=motivo or manutencao.motivo_cancelamento or '',
    )


def registrar_evidencia(manutencao, usuario, evidencia):
    registrar_evento(
        manutencao,
        usuario,
        'EVIDENCIA',
        f'Evidência anexada: {evidencia.get_tipo_display()}',
        descricao=evidencia.descricao or '',
        metadados={'tipo': evidencia.tipo, 'arquivo': evidencia.arquivo.name},
    )


def garantir_historico_estruturado(manutencao):
    """Garante histórico estruturado para uma manutenção específica (uso pontual na view)."""
    if manutencao.registros_historico.exists():
        return
    usuario = manutencao.registrado_por
    RegistroHistoricoManutencao.objects.create(
        manutencao=manutencao,
        tipo='ABERTURA',
        titulo='Abertura da manutenção (migração)',
        descricao=manutencao.descricao or 'Registro importado do sistema anterior.',
        registrado_por=usuario,
    )
    if manutencao.detalhamento_servicos and manutencao.detalhamento_servicos.strip():
        servico = ServicoManutencao.objects.create(
            manutencao=manutencao,
            descricao=manutencao.detalhamento_servicos.strip(),
            detalhamento=manutencao.detalhamento_servicos.strip(),
            pecas_garantia=manutencao.detalhamento_pecas_garantia,
            custo_pecas=manutencao.custo_pecas,
            custo_mao_obra=manutencao.custo_mao_obra,
            odometro=manutencao.odometro,
            status_na_epoca=manutencao.status,
            registrado_por=usuario,
        )
        RegistroHistoricoManutencao.objects.create(
            manutencao=manutencao,
            tipo='SERVICO',
            titulo='Serviço registrado (migração)',
            descricao=servico.descricao,
            servico=servico,
            registrado_por=usuario,
        )


def backfill_servicos_existentes():
    """Cria registros de serviço para manutenções que ainda não possuem histórico estruturado."""
    from django.db.models import Count

    qs = Manutencao.objects.annotate(qtd_servicos=Count('servicos')).filter(qtd_servicos=0)
    for man in qs.iterator():
        usuario = man.registrado_por
        if not man.registros_historico.exists():
            RegistroHistoricoManutencao.objects.create(
                manutencao=man,
                tipo='ABERTURA',
                titulo='Abertura da manutenção (migração)',
                descricao=man.descricao or 'Registro importado do sistema anterior.',
                registrado_por=usuario,
            )
        if man.detalhamento_servicos and man.detalhamento_servicos.strip():
            servico = ServicoManutencao.objects.create(
                manutencao=man,
                descricao=man.detalhamento_servicos.strip(),
                detalhamento=man.detalhamento_servicos.strip(),
                pecas_garantia=man.detalhamento_pecas_garantia,
                custo_pecas=man.custo_pecas,
                custo_mao_obra=man.custo_mao_obra,
                odometro=man.odometro,
                status_na_epoca=man.status,
                registrado_por=usuario,
            )
            RegistroHistoricoManutencao.objects.create(
                manutencao=man,
                tipo='SERVICO',
                titulo='Serviço registrado (migração)',
                descricao=servico.descricao,
                servico=servico,
                registrado_por=usuario,
            )
            sincronizar_resumo_servicos(man)
