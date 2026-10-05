import os
import logging
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from reserva_baep.decorators import require_module_permission

logger = logging.getLogger('administracao')


def _registrar_log_bloqueio(admin_username, target_username, motivo):
    """
    Registra tentativa bloqueada de alteração de permissão no arquivo baep_sistema.log
    e nos logs do sistema.
    Formato: [PERMISSAO-BLOQUEIO] user=<admin> target=<username> motivo=<auto-bloqueio|master-protegido> ts=<ISO8601>
    """
    ts = timezone.now().isoformat()
    log_msg = f"[PERMISSAO-BLOQUEIO] user={admin_username} target={target_username} motivo={motivo} ts={ts}"
    logger.warning(log_msg)
    try:
        log_dir = settings.BASE_DIR / 'logs'
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / 'baep_sistema.log'
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    except Exception as exc:
        logger.error(f"Erro ao registrar log de bloqueio de permissão: {exc}")

# Definição canônica dos grupos de módulos do SIS LOGÍSTICA 2º BAEP
MODULOS_SISTEMA = [
    {
        'group': 'materiais',
        'nome': 'Material de Consumo (Estoque / Almoxarifado)',
        'descricao': 'Acesso ao módulo de estoque de consumo, entradas, saídas, catálogo de materiais e inventários.',
        'icone': 'fas fa-warehouse',
        'destaque': True,
    },
    {
        'group': 'reserva_armas',
        'nome': 'Reserva de Armas (Armamentos & Cautelas)',
        'descricao': 'Controle de armamentos convencionais, cautelas operacionais e efetivo policial.',
        'icone': 'fas fa-gun',
        'destaque': False,
    },
    {
        'group': 'material_belico',
        'nome': 'Material Bélico (Arsenal Tático & Kits)',
        'descricao': 'Controle de fuzis, calibres 12, pistolas Glock, munições químicas/convencionais e kits operacionais.',
        'icone': 'fas fa-shield-alt',
        'destaque': False,
    },
    {
        'group': 'frota',
        'nome': 'Frota de Viaturas (Despachos & Manutenção)',
        'descricao': 'Despacho de viaturas, controle de hodômetro, abastecimento, checklists e manutenções.',
        'icone': 'fas fa-car-side',
        'destaque': False,
    },
    {
        'group': 'patrimonio',
        'nome': 'Patrimônio Permanente (Tombamento)',
        'descricao': 'Gestão de bens duráveis, tombamentos, contas patrimoniais e termos de responsabilidade.',
        'icone': 'fas fa-barcode',
        'destaque': False,
    },
    {
        'group': 'inventario',
        'nome': 'Inventário Semestral (Conferência Cega)',
        'descricao': 'Ciclo de inventário semestral com conferência cega, apuração de divergências e termo oficial.',
        'icone': 'fas fa-clipboard-check',
        'destaque': False,
    },
    {
        'group': 'telematica',
        'nome': 'Telemática & TI (Rádios & Suporte)',
        'descricao': 'Inventário de radiocomunicação, linhas móveis, câmeras corporais e chamados de suporte técnico.',
        'icone': 'fas fa-satellite-dish',
        'destaque': False,
    },
    {
        'group': 'relatorios',
        'nome': 'Relatórios Oficiais',
        'descricao': 'Geração de relatórios executivos, mapas de carga e certidões em PDF e Excel.',
        'icone': 'fas fa-file-alt',
        'destaque': False,
    },
    {
        'group': 'administracao',
        'nome': 'Administração Geral do Sistema',
        'descricao': 'Gestão de usuários, concessão de permissões de módulos e visão consolidada da unidade.',
        'icone': 'fas fa-user-shield',
        'destaque': False,
    },
]


@login_required
@require_module_permission('administracao')
def listar_usuarios_permissoes(request):
    """
    Lista todos os usuários do sistema com destaque para o status de permissão
    ao módulo 'Material de Consumo' (grupo 'materiais') e demais módulos.
    """
    termo_busca = request.GET.get('q', '').strip()
    status_consumo = request.GET.get('status_consumo', 'TODOS').strip()

    usuarios_qs = User.objects.all().select_related('perfil', 'perfil__policial').prefetch_related('groups').order_by('username')

    if termo_busca:
        usuarios_qs = usuarios_qs.filter(
            Q(username__icontains=termo_busca) |
            Q(first_name__icontains=termo_busca) |
            Q(last_name__icontains=termo_busca) |
            Q(email__icontains=termo_busca) |
            Q(perfil__policial__nome__icontains=termo_busca) |
            Q(perfil__policial__re__icontains=termo_busca)
        )

    # Identifica o grupo 'materiais'
    try:
        grupo_materiais = Group.objects.get(name='materiais')
    except Group.DoesNotExist:
        grupo_materiais = Group.objects.create(name='materiais')

    # Filtragem por status de acesso ao módulo Material de Consumo
    if status_consumo == 'LIBERADO':
        # Usuários que são superuser OU pertencem ao grupo 'materiais'
        usuarios_qs = usuarios_qs.filter(Q(is_superuser=True) | Q(groups=grupo_materiais)).distinct()
    elif status_consumo == 'BLOQUEADO':
        # Usuários não-superusuários que NÃO estão no grupo 'materiais'
        usuarios_qs = usuarios_qs.filter(is_superuser=False).exclude(groups=grupo_materiais).distinct()

    paginator = Paginator(usuarios_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Anota informações calculadas para apresentação direta no template
    for u in page_obj:
        user_groups_set = set(g.name for g in u.groups.all())
        u.tem_acesso_consumo = u.is_superuser or ('materiais' in user_groups_set)
        u.qtd_modulos = len(user_groups_set)
        u.grupos_nomes = sorted(list(user_groups_set))

    total_com_acesso = User.objects.filter(Q(is_superuser=True) | Q(groups=grupo_materiais)).distinct().count()
    total_geral = User.objects.count()

    context = {
        'page_obj': page_obj,
        'termo_busca': termo_busca,
        'status_consumo': status_consumo,
        'total_com_acesso': total_com_acesso,
        'total_bloqueados': total_geral - total_com_acesso,
        'total_usuarios': usuarios_qs.count(),
    }
    return render(request, 'administracao/permissoes_lista.html', context)


@login_required
@require_module_permission('administracao')
def gerenciar_permissoes_usuario(request, user_id):
    """
    Exibe formulário para conceder ou revogar o acesso ao módulo
    'Material de Consumo' (grupo 'materiais') e demais módulos do sistema
    para um usuário específico.
    """
    usuario_alvo = get_object_or_404(User.objects.select_related('perfil', 'perfil__policial'), id=user_id)

    # Assegura que todos os grupos do sistema existam no banco
    for mod in MODULOS_SISTEMA:
        Group.objects.get_or_create(name=mod['group'])

    if request.method == 'POST':
        grupos_selecionados = set(request.POST.getlist('grupos'))

        # VALIDAÇÃO B — Proteção do master:
        admin_master_user = os.getenv('ADMIN_USERNAME', 'master')
        if usuario_alvo.username == 'master' or usuario_alvo.username == admin_master_user:
            _registrar_log_bloqueio(request.user.username, usuario_alvo.username, 'master-protegido')
            messages.error(request, "As permissões do usuário master não podem ser alteradas.")
            return redirect('administracao:listar_permissoes')

        # VALIDAÇÃO A — Auto-proteção de admin:
        if usuario_alvo.id == request.user.id and 'administracao' not in grupos_selecionados:
            grupos_selecionados.add('administracao')
            _registrar_log_bloqueio(request.user.username, usuario_alvo.username, 'auto-bloqueio')
            messages.error(request, "Você não pode remover sua própria permissão de administração.")

        # Grupos anteriores para fins de auditoria/log
        grupos_anteriores = set(usuario_alvo.groups.values_list('name', flat=True))

        for mod in MODULOS_SISTEMA:
            grp_name = mod['group']
            grp_obj = Group.objects.get(name=grp_name)
            if grp_name in grupos_selecionados:
                usuario_alvo.groups.add(grp_obj)
            else:
                usuario_alvo.groups.remove(grp_obj)

        grupos_novos = set(usuario_alvo.groups.values_list('name', flat=True))
        concedidos = grupos_novos - grupos_anteriores
        revogados = grupos_anteriores - grupos_novos

        # Registro de log e auditoria
        msg_auditoria = (
            f"PERMISSÕES ATUALIZADAS | Usuário-alvo: '{usuario_alvo.username}' (ID {usuario_alvo.id}) | "
            f"Operador: '{request.user.username}' (ID {request.user.id}) | "
            f"Concedidos: {list(concedidos) or 'Nenhum'} | "
            f"Revogados: {list(revogados) or 'Nenhum'} | "
            f"Grupos Finais: {list(grupos_novos)}"
        )
        logger.info(msg_auditoria)

        # Se o perfil tiver suporte a simple_history, salva para gerar registro
        if hasattr(usuario_alvo, 'perfil') and hasattr(usuario_alvo.perfil, 'history'):
            usuario_alvo.perfil.save()

        nome_exibicao = usuario_alvo.get_full_name() or usuario_alvo.username
        if 'materiais' in concedidos:
            messages.success(request, f"Acesso ao módulo 'Material de Consumo' CONCEDIDO para {nome_exibicao}.")
        elif 'materiais' in revogados:
            messages.warning(request, f"Acesso ao módulo 'Material de Consumo' REVOGADO para {nome_exibicao}.")
        else:
            messages.success(request, f"Permissões de {nome_exibicao} atualizadas com sucesso.")

        return redirect('administracao:listar_permissoes')

    # GET: Monta estrutura com status de cada grupo
    grupos_usuario = set(usuario_alvo.groups.values_list('name', flat=True))
    lista_modulos = []
    for mod in MODULOS_SISTEMA:
        lista_modulos.append({
            'group': mod['group'],
            'nome': mod['nome'],
            'descricao': mod['descricao'],
            'icone': mod['icone'],
            'destaque': mod['destaque'],
            'checked': mod['group'] in grupos_usuario,
        })

    context = {
        'usuario_alvo': usuario_alvo,
        'lista_modulos': lista_modulos,
        'is_master': usuario_alvo.username == 'master',
    }
    return render(request, 'administracao/permissoes_form.html', context)
