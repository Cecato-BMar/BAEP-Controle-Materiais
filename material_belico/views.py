"""Views do módulo Material Bélico."""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from reserva_baep.decorators import require_module_permission
from .models import (
    Fuzil, EspingardaCal12, PistolaGlock, PistolaTaurus, ArmaTransferenciaPendente,
    RedDot, Magnificador, Supressor, VinculacaoAcessorioFuzil,
    KitOperacional, RadioHT, AM640, AM600, MosquetaoFederal,
    TASER, Algemas, MunicaoQuimica,
    MunicaoConvencional, DistribuicaoMunicaoKit,
    ColeteBalistico, EscudoBalistico, CapaceteBalistico,
    STATUS_ARMA_CHOICES,
)
from .forms import (
    FuzilForm, EspingardaCal12Form, PistolaGlockForm, PistolaTaurusForm,
    ArmaTransferenciaPendenteForm,
    RedDotForm, MagnificadorForm, SupressorForm, VinculacaoAcessorioFuzilForm,
    KitOperacionalForm, RadioHTForm, AM640Form, AM600Form, MosquetaoFederalForm,
    TASERForm, AlgemasForm, MunicaoQuimicaForm,
    MunicaoConvencionalForm, DistribuicaoMunicaoKitForm,
    ColeteBalisticoForm, EscudoBalisticoForm, CapaceteBalisticoForm,
)


# =============================================================================
# DASHBOARD
# =============================================================================

@login_required
@require_module_permission('material_belico')
def dashboard(request):
    """Dashboard principal com totalizadores e alertas."""
    total_fuzis = Fuzil.objects.exclude(status='BAIXADO').count()
    total_fuzis_762 = Fuzil.objects.filter(tipo='SCAR_762').exclude(status='BAIXADO').count()
    total_fuzis_556 = Fuzil.objects.filter(tipo__in=['SCAR_556', 'IMBEL_IA2']).exclude(status='BAIXADO').count()
    total_espingardas = EspingardaCal12.objects.exclude(status='BAIXADO').count()
    total_glocks = PistolaGlock.objects.count()
    total_taurus = PistolaTaurus.objects.count()
    total_kits = KitOperacional.objects.count()
    total_radios = RadioHT.objects.filter(situacao='OP').count()
    total_tasers = TASER.objects.count()
    total_coletes = ColeteBalistico.objects.filter(situacao='DISPONIVEL').count()
    total_escudos_op = EscudoBalistico.objects.filter(situacao='OP').count()
    total_capacetes_op = CapaceteBalistico.objects.filter(condicao='OPERANDO').count()
    total_transferencias = ArmaTransferenciaPendente.objects.count()

    # Alertas RN-02
    armas_sindiciancia = Fuzil.objects.filter(status='SINDICANCIA')
    glocks_apreendidas = PistolaGlock.objects.filter(situacao_reserva='APREENDIDA')

    # Alertas RN-03
    municoes_quimicas_vencidas = [mq for mq in MunicaoQuimica.objects.all() if mq.vencida]
    escudos_validade_vencida = [e for e in EscudoBalistico.objects.filter(situacao='OP') if e.alerta_validade]
    capacetes_vencidos = CapaceteBalistico.objects.filter(condicao='OPERANDO', validade__iexact='VENCIDO')
    coletes_validade_vencida = [c for c in ColeteBalistico.objects.filter(situacao='DISPONIVEL') if c.validade_vencida]

    # Alertas RN-07
    tasers_bateria_baixa = TASER.objects.filter(carga_bateria_percent__lt=50)
    tasers_bloqueados = TASER.objects.filter(carga_bateria_percent=0)

    # Transferências
    transferencias_paradas = ArmaTransferenciaPendente.objects.filter(status='PARADO')

    context = {
        'total_fuzis': total_fuzis, 'total_fuzis_762': total_fuzis_762,
        'total_fuzis_556': total_fuzis_556, 'total_espingardas': total_espingardas,
        'total_glocks': total_glocks, 'total_taurus': total_taurus,
        'total_kits': total_kits, 'total_radios': total_radios,
        'total_tasers': total_tasers, 'total_coletes': total_coletes,
        'total_escudos_op': total_escudos_op, 'total_capacetes_op': total_capacetes_op,
        'total_transferencias': total_transferencias,
        'armas_sindiciancia': armas_sindiciancia,
        'glocks_apreendidas': glocks_apreendidas,
        'municoes_quimicas_vencidas': municoes_quimicas_vencidas,
        'escudos_validade_vencida': escudos_validade_vencida,
        'capacetes_vencidos': capacetes_vencidos,
        'coletes_validade_vencida': coletes_validade_vencida,
        'tasers_bateria_baixa': tasers_bateria_baixa,
        'tasers_bloqueados': tasers_bloqueados,
        'transferencias_paradas': transferencias_paradas,
    }
    return render(request, 'material_belico/dashboard.html', context)


# =============================================================================
# HELPER CRUD GENÉRICO
# =============================================================================

def _crud_list(request, model, form_class, template_list, template_form, redirect_name,
               titulo, extra_qs=None, order_by=None):
    """Helper reutilizável para operações CRUD padrão."""
    qs = model.objects.all()
    if extra_qs:
        qs = extra_qs(qs)
    if order_by:
        qs = qs.order_by(*order_by)
    if request.method == 'POST':
        pk = request.POST.get('pk')
        if pk:
            obj = get_object_or_404(model, pk=pk)
            form = form_class(request.POST, instance=obj)
            msg_ok = f'{titulo} atualizado com sucesso.'
        else:
            form = form_class(request.POST)
            msg_ok = f'{titulo} cadastrado com sucesso.'
        if form.is_valid():
            form.save()
            messages.success(request, msg_ok)
            return redirect(redirect_name)
        else:
            messages.error(request, 'Corrija os erros abaixo.')
            return render(request, template_form, {'form': form, 'titulo': titulo, 'itens': qs})
    else:
        form = form_class()
    return render(request, template_list, {'itens': qs, 'form': form, 'titulo': titulo,
                                            'template_form': template_form, 'redirect_name': redirect_name})


def _crud_create(request, form_class, template_form, redirect_name, titulo, context_extra=None):
    """Helper para criar."""
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'{titulo} cadastrado(a) com sucesso.')
            return redirect(redirect_name)
    else:
        form = form_class()
    ctx = {'form': form, 'titulo': f'Novo(a) {titulo}', 'is_create': True}
    if context_extra:
        ctx.update(context_extra)
    return render(request, template_form, ctx)


def _crud_edit(request, pk, model, form_class, template_form, redirect_name, titulo, context_extra=None):
    """Helper para editar."""
    obj = get_object_or_404(model, pk=pk)
    if request.method == 'POST':
        form = form_class(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'{titulo} atualizado(a) com sucesso.')
            return redirect(redirect_name)
    else:
        form = form_class(instance=obj)
    ctx = {'form': form, 'titulo': f'Editar {titulo}', 'obj': obj, 'is_create': False}
    if context_extra:
        ctx.update(context_extra)
    return render(request, template_form, ctx)


def _crud_delete(request, pk, model, redirect_name, titulo):
    """Helper para excluir."""
    obj = get_object_or_404(model, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, f'{titulo} excluído(a) com sucesso.')
        return redirect(redirect_name)
    return render(request, 'material_belico/confirmar_exclusao.html',
                  {'obj': obj, 'titulo': titulo, 'redirect_name': redirect_name})


# =============================================================================
# CRUD: FUZIS
# =============================================================================

@login_required
@require_module_permission('material_belico')
def fuzil_list(request):
    itens = Fuzil.objects.all().order_by('tipo', 'patrimonio')
    # Extrair localizações únicas dos dados existentes
    locs = sorted(set(itens.values_list('localizacao', flat=True)))
    loc_map = dict(Fuzil._meta.get_field('localizacao').choices)
    tipo_map = dict(Fuzil.TIPO_CHOICES)
    status_map = dict(Fuzil._meta.get_field('status').choices)
    filter_fields = [
        {'label': 'Tipo', 'field': 'tipo', 'choices': [{'value': v, 'label': l} for v, l in Fuzil.TIPO_CHOICES]},
        {'label': 'Status', 'field': 'status', 'choices': [{'value': v, 'label': l} for v, l in STATUS_ARMA_CHOICES]},
        {'label': 'Localização', 'field': 'localizacao', 'choices': [{'value': loc, 'label': loc_map.get(loc, loc)} for loc in locs]},
    ]
    return render(request, 'material_belico/fuzil_list.html', {'itens': itens, 'titulo': 'Fuzis', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def fuzil_create(request):
    return _crud_create(request, FuzilForm, 'material_belico/form_generico.html', 'material_belico:fuzil_list', 'Fuzil')

@login_required
@require_module_permission('material_belico')
def fuzil_edit(request, pk):
    return _crud_edit(request, pk, Fuzil, FuzilForm, 'material_belico/form_generico.html', 'material_belico:fuzil_list', 'Fuzil')

@login_required
@require_module_permission('material_belico')
def fuzil_delete(request, pk):
    return _crud_delete(request, pk, Fuzil, 'material_belico:fuzil_list', 'Fuzil')


# =============================================================================
# CRUD: ESPINGARDAS CAL.12
# =============================================================================

@login_required
@require_module_permission('material_belico')
def espingarda_list(request):
    itens = EspingardaCal12.objects.all()
    status_map = dict(EspingardaCal12.STATUS_CHOICES)
    filter_fields = [
        {'label': 'Status', 'field': 'status', 'choices': [{'value': v, 'label': l} for v, l in EspingardaCal12.STATUS_CHOICES]},
    ]
    return render(request, 'material_belico/espingarda_list.html', {'itens': itens, 'titulo': 'Espingardas Cal.12', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def espingarda_create(request):
    return _crud_create(request, EspingardaCal12Form, 'material_belico/form_generico.html', 'material_belico:espingarda_list', 'Espingarda Cal.12')

@login_required
@require_module_permission('material_belico')
def espingarda_edit(request, pk):
    return _crud_edit(request, pk, EspingardaCal12, EspingardaCal12Form, 'material_belico/form_generico.html', 'material_belico:espingarda_list', 'Espingarda Cal.12')

@login_required
@require_module_permission('material_belico')
def espingarda_delete(request, pk):
    return _crud_delete(request, pk, EspingardaCal12, 'material_belico:espingarda_list', 'Espingarda Cal.12')


# =============================================================================
# CRUD: PISTOLAS GLOCK
# =============================================================================

@login_required
@require_module_permission('material_belico')
def pistola_glock_list(request):
    itens = PistolaGlock.objects.all()
    modelos = sorted(set(itens.values_list('modelo', flat=True)))
    filter_fields = [
        {'label': 'Situação', 'field': 'situacao', 'choices': [{'value': v, 'label': l} for v, l in PistolaGlock.SITUACAO_CHOICES]},
        {'label': 'Modelo', 'field': 'modelo', 'choices': [{'value': m, 'label': m} for m in modelos]},
    ]
    return render(request, 'material_belico/glock_list.html', {'itens': itens, 'titulo': 'Pistolas Glock', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def pistola_glock_create(request):
    return _crud_create(request, PistolaGlockForm, 'material_belico/form_generico.html', 'material_belico:pistola_glock_list', 'Pistola Glock')

@login_required
@require_module_permission('material_belico')
def pistola_glock_edit(request, pk):
    return _crud_edit(request, pk, PistolaGlock, PistolaGlockForm, 'material_belico/form_generico.html', 'material_belico:pistola_glock_list', 'Pistola Glock')

@login_required
@require_module_permission('material_belico')
def pistola_glock_delete(request, pk):
    return _crud_delete(request, pk, PistolaGlock, 'material_belico:pistola_glock_list', 'Pistola Glock')


# =============================================================================
# CRUD: PISTOLAS TAURUS
# =============================================================================

@login_required
@require_module_permission('material_belico')
def pistola_taurus_list(request):
    itens = PistolaTaurus.objects.all()
    filter_fields = [
        {'label': 'Modelo', 'field': 'modelo', 'choices': [{'value': v, 'label': l} for v, l in PistolaTaurus.MODELO_CHOICES]},
    ]
    return render(request, 'material_belico/taurus_list.html', {'itens': itens, 'titulo': 'Pistolas Taurus', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def pistola_taurus_create(request):
    return _crud_create(request, PistolaTaurusForm, 'material_belico/form_generico.html', 'material_belico:pistola_taurus_list', 'Pistola Taurus')

@login_required
@require_module_permission('material_belico')
def pistola_taurus_edit(request, pk):
    return _crud_edit(request, pk, PistolaTaurus, PistolaTaurusForm, 'material_belico/form_generico.html', 'material_belico:pistola_taurus_list', 'Pistola Taurus')

@login_required
@require_module_permission('material_belico')
def pistola_taurus_delete(request, pk):
    return _crud_delete(request, pk, PistolaTaurus, 'material_belico:pistola_taurus_list', 'Pistola Taurus')


# =============================================================================
# CRUD: TRANSFERÊNCIAS PENDENTES
# =============================================================================

@login_required
@require_module_permission('material_belico')
def transferencia_list(request):
    itens = ArmaTransferenciaPendente.objects.all()
    filter_fields = [
        {'label': 'Espécie', 'field': 'especie', 'choices': [{'value': v, 'label': l} for v, l in ArmaTransferenciaPendente.ESPECIE_CHOICES]},
        {'label': 'Situação', 'field': 'situacao', 'choices': [{'value': v, 'label': l} for v, l in ArmaTransferenciaPendente.SITUACAO_CHOICES]},
        {'label': 'Status', 'field': 'status', 'choices': [{'value': v, 'label': l} for v, l in ArmaTransferenciaPendente.STATUS_CHOICES]},
    ]
    return render(request, 'material_belico/transferencia_list.html', {'itens': itens, 'titulo': 'Transferências Pendentes', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def transferencia_create(request):
    return _crud_create(request, ArmaTransferenciaPendenteForm, 'material_belico/form_generico.html', 'material_belico:transferencia_list', 'Transferência Pendente')

@login_required
@require_module_permission('material_belico')
def transferencia_edit(request, pk):
    return _crud_edit(request, pk, ArmaTransferenciaPendente, ArmaTransferenciaPendenteForm, 'material_belico/form_generico.html', 'material_belico:transferencia_list', 'Transferência Pendente')

@login_required
@require_module_permission('material_belico')
def transferencia_delete(request, pk):
    return _crud_delete(request, pk, ArmaTransferenciaPendente, 'material_belico:transferencia_list', 'Transferência Pendente')


# =============================================================================
# CRUD: RED DOT
# =============================================================================

@login_required
@require_module_permission('material_belico')
def reddot_list(request):
    itens = RedDot.objects.all()
    locs = sorted(set(itens.values_list('localizacao', flat=True)))
    loc_map = dict(RedDot._meta.get_field('localizacao').choices)
    filter_fields = [
        {'label': 'Localização', 'field': 'localizacao', 'choices': [{'value': loc, 'label': loc_map.get(loc, loc)} for loc in locs]},
    ]
    return render(request, 'material_belico/acessorio_list.html', {'itens': itens, 'titulo': 'Red Dots', 'tipo': 'reddot', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def reddot_create(request):
    return _crud_create(request, RedDotForm, 'material_belico/form_generico.html', 'material_belico:reddot_list', 'Red Dot')

@login_required
@require_module_permission('material_belico')
def reddot_edit(request, pk):
    return _crud_edit(request, pk, RedDot, RedDotForm, 'material_belico/form_generico.html', 'material_belico:reddot_list', 'Red Dot')

@login_required
@require_module_permission('material_belico')
def reddot_delete(request, pk):
    return _crud_delete(request, pk, RedDot, 'material_belico:reddot_list', 'Red Dot')


# =============================================================================
# CRUD: MAGNIFICADOR
# =============================================================================

@login_required
@require_module_permission('material_belico')
def magnificador_list(request):
    itens = Magnificador.objects.all()
    locs = sorted(set(itens.values_list('localizacao', flat=True)))
    loc_map = dict(Magnificador._meta.get_field('localizacao').choices)
    filter_fields = [
        {'label': 'Localização', 'field': 'localizacao', 'choices': [{'value': loc, 'label': loc_map.get(loc, loc)} for loc in locs]},
        {'label': 'Status', 'field': 'status', 'choices': [{'value': v, 'label': l} for v, l in Magnificador.STATUS_CHOICES]},
    ]
    return render(request, 'material_belico/acessorio_list.html', {'itens': itens, 'titulo': 'Magnificadores', 'tipo': 'magnificador', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def magnificador_create(request):
    return _crud_create(request, MagnificadorForm, 'material_belico/form_generico.html', 'material_belico:magnificador_list', 'Magnificador')

@login_required
@require_module_permission('material_belico')
def magnificador_edit(request, pk):
    return _crud_edit(request, pk, Magnificador, MagnificadorForm, 'material_belico/form_generico.html', 'material_belico:magnificador_list', 'Magnificador')

@login_required
@require_module_permission('material_belico')
def magnificador_delete(request, pk):
    return _crud_delete(request, pk, Magnificador, 'material_belico:magnificador_list', 'Magnificador')


# =============================================================================
# CRUD: SUPRESSOR
# =============================================================================

@login_required
@require_module_permission('material_belico')
def supressor_list(request):
    itens = Supressor.objects.all()
    filter_fields = [
        {'label': 'Localização', 'field': 'localizacao', 'choices': [{'value': v, 'label': l} for v, l in Supressor.LOCALIZACAO_SUPRESSOR]},
    ]
    return render(request, 'material_belico/acessorio_list.html', {'itens': itens, 'titulo': 'Supressores', 'tipo': 'supressor', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def supressor_create(request):
    return _crud_create(request, SupressorForm, 'material_belico/form_generico.html', 'material_belico:supressor_list', 'Supressor')

@login_required
@require_module_permission('material_belico')
def supressor_edit(request, pk):
    return _crud_edit(request, pk, Supressor, SupressorForm, 'material_belico/form_generico.html', 'material_belico:supressor_list', 'Supressor')

@login_required
@require_module_permission('material_belico')
def supressor_delete(request, pk):
    return _crud_delete(request, pk, Supressor, 'material_belico:supressor_list', 'Supressor')


# =============================================================================
# CRUD: VINCULAÇÃO ACESSÓRIO–FUZIL
# =============================================================================

@login_required
@require_module_permission('material_belico')
def vinculacao_list(request):
    itens = VinculacaoAcessorioFuzil.objects.select_related('fuzil', 'red_dot', 'magnificador', 'supressor')
    filter_fields = [
        {'label': 'Tipo de Fuzil', 'field': 'tipo_fuzil', 'choices': [{'value': v, 'label': l} for v, l in Fuzil.TIPO_CHOICES]},
    ]
    return render(request, 'material_belico/vinculacao_list.html', {'itens': itens, 'titulo': 'Vinculação Acessório–Fuzil', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def vinculacao_create(request):
    return _crud_create(request, VinculacaoAcessorioFuzilForm, 'material_belico/form_generico.html', 'material_belico:vinculacao_list', 'Vinculação Acessório–Fuzil')

@login_required
@require_module_permission('material_belico')
def vinculacao_edit(request, pk):
    return _crud_edit(request, pk, VinculacaoAcessorioFuzil, VinculacaoAcessorioFuzilForm, 'material_belico/form_generico.html', 'material_belico:vinculacao_list', 'Vinculação Acessório–Fuzil')

@login_required
@require_module_permission('material_belico')
def vinculacao_delete(request, pk):
    return _crud_delete(request, pk, VinculacaoAcessorioFuzil, 'material_belico:vinculacao_list', 'Vinculação')


# =============================================================================
# CRUD: KITS OPERACIONAIS
# =============================================================================

@login_required
@require_module_permission('material_belico')
def kit_list(request):
    itens = KitOperacional.objects.select_related(
        'fuzil_556_1', 'fuzil_556_2', 'fuzil_762', 'espingarda', 'radio_ht', 'am640', 'escudo'
    )
    filter_fields = [
        {'label': 'Kit', 'field': 'numero_kit', 'choices': [{'value': v, 'label': l} for v, l in KitOperacional.NUMERO_KIT_CHOICES]},
    ]
    return render(request, 'material_belico/kit_list.html', {'itens': itens, 'titulo': 'Kits Operacionais', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def kit_create(request):
    return _crud_create(request, KitOperacionalForm, 'material_belico/form_generico.html', 'material_belico:kit_list', 'Kit Operacional')

@login_required
@require_module_permission('material_belico')
def kit_edit(request, pk):
    return _crud_edit(request, pk, KitOperacional, KitOperacionalForm, 'material_belico/form_generico.html', 'material_belico:kit_list', 'Kit Operacional')

@login_required
@require_module_permission('material_belico')
def kit_delete(request, pk):
    return _crud_delete(request, pk, KitOperacional, 'material_belico:kit_list', 'Kit Operacional')

@login_required
@require_module_permission('material_belico')
def kit_detail(request, pk):
    """View detalhada do kit com composição visual."""
    kit = get_object_or_404(KitOperacional.objects.select_related(
        'fuzil_556_1', 'fuzil_556_2', 'fuzil_762', 'espingarda', 'radio_ht', 'am640', 'escudo'
    ), pk=pk)
    distribuicoes = kit.distribuicoes_municao.all()
    return render(request, 'material_belico/kit_detail.html', {'kit': kit, 'distribuicoes': distribuicoes})


# =============================================================================
# CRUD: RÁDIO HT
# =============================================================================

@login_required
@require_module_permission('material_belico')
def radio_ht_list(request):
    itens = RadioHT.objects.all()
    filter_fields = [
        {'label': 'Situação', 'field': 'situacao', 'choices': [{'value': v, 'label': l} for v, l in RadioHT.SITUACAO_CHOICES]},
    ]
    return render(request, 'material_belico/comunicacao_list.html', {'itens': itens, 'titulo': 'Rádios HT', 'tipo': 'radio_ht', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def radio_ht_create(request):
    return _crud_create(request, RadioHTForm, 'material_belico/form_generico.html', 'material_belico:radio_ht_list', 'Rádio HT')

@login_required
@require_module_permission('material_belico')
def radio_ht_edit(request, pk):
    return _crud_edit(request, pk, RadioHT, RadioHTForm, 'material_belico/form_generico.html', 'material_belico:radio_ht_list', 'Rádio HT')

@login_required
@require_module_permission('material_belico')
def radio_ht_delete(request, pk):
    return _crud_delete(request, pk, RadioHT, 'material_belico:radio_ht_list', 'Rádio HT')


# =============================================================================
# CRUD: AM-640
# =============================================================================

@login_required
@require_module_permission('material_belico')
def am640_list(request):
    itens = AM640.objects.all()
    filter_fields = [
        {'label': 'Situação', 'field': 'situacao', 'choices': [{'value': v, 'label': l} for v, l in AM640.SITUACAO_CHOICES]},
    ]
    return render(request, 'material_belico/comunicacao_list.html', {'itens': itens, 'titulo': 'AM-640', 'tipo': 'am640', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def am640_create(request):
    return _crud_create(request, AM640Form, 'material_belico/form_generico.html', 'material_belico:am640_list', 'AM-640')

@login_required
@require_module_permission('material_belico')
def am640_edit(request, pk):
    return _crud_edit(request, pk, AM640, AM640Form, 'material_belico/form_generico.html', 'material_belico:am640_list', 'AM-640')

@login_required
@require_module_permission('material_belico')
def am640_delete(request, pk):
    return _crud_delete(request, pk, AM640, 'material_belico:am640_list', 'AM-640')


# =============================================================================
# CRUD: AM-600
# =============================================================================

@login_required
@require_module_permission('material_belico')
def am600_list(request):
    itens = AM600.objects.all()
    return render(request, 'material_belico/comunicacao_list.html', {'itens': itens, 'titulo': 'AM-600', 'tipo': 'am600', 'filter_fields': []})

@login_required
@require_module_permission('material_belico')
def am600_create(request):
    return _crud_create(request, AM600Form, 'material_belico/form_generico.html', 'material_belico:am600_list', 'AM-600')

@login_required
@require_module_permission('material_belico')
def am600_delete(request, pk):
    return _crud_delete(request, pk, AM600, 'material_belico:am600_list', 'AM-600')


# =============================================================================
# CRUD: MOSQUETÃO FEDERAL
# =============================================================================

@login_required
@require_module_permission('material_belico')
def mosquetao_list(request):
    itens = MosquetaoFederal.objects.all()
    return render(request, 'material_belico/comunicacao_list.html', {'itens': itens, 'titulo': 'Mosquetão Federal 201/Z', 'tipo': 'mosquetao', 'filter_fields': []})

@login_required
@require_module_permission('material_belico')
def mosquetao_create(request):
    return _crud_create(request, MosquetaoFederalForm, 'material_belico/form_generico.html', 'material_belico:mosquetao_list', 'Mosquetão Federal')

@login_required
@require_module_permission('material_belico')
def mosquetao_delete(request, pk):
    return _crud_delete(request, pk, MosquetaoFederal, 'material_belico:mosquetao_list', 'Mosquetão Federal')


# =============================================================================
# CRUD: TASER
# =============================================================================

@login_required
@require_module_permission('material_belico')
def taser_list(request):
    itens = TASER.objects.all()
    situacoes = sorted(set(itens.values_list('situacao', flat=True)))
    filter_fields = [
        {'label': 'Situação', 'field': 'situacao', 'choices': [{'value': s, 'label': s} for s in situacoes]},
        {'label': 'Bateria', 'field': 'bateria', 'choices': [
            {'value': 'ok', 'label': '≥50% OK'}, {'value': 'baixa', 'label': '<50% Recarregar'}, {'value': 'zero', 'label': '0% Bloqueado'},
        ]},
    ]
    return render(request, 'material_belico/nao_letal_list.html', {'itens': itens, 'titulo': 'TASER', 'tipo': 'taser', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def taser_create(request):
    return _crud_create(request, TASERForm, 'material_belico/form_generico.html', 'material_belico:taser_list', 'TASER')

@login_required
@require_module_permission('material_belico')
def taser_edit(request, pk):
    return _crud_edit(request, pk, TASER, TASERForm, 'material_belico/form_generico.html', 'material_belico:taser_list', 'TASER')

@login_required
@require_module_permission('material_belico')
def taser_delete(request, pk):
    return _crud_delete(request, pk, TASER, 'material_belico:taser_list', 'TASER')


# =============================================================================
# CRUD: ALGEMAS
# =============================================================================

@login_required
@require_module_permission('material_belico')
def algemas_list(request):
    itens = Algemas.objects.all()
    return render(request, 'material_belico/nao_letal_list.html', {'itens': itens, 'titulo': 'Algemas', 'tipo': 'algemas', 'filter_fields': []})

@login_required
@require_module_permission('material_belico')
def algemas_create(request):
    return _crud_create(request, AlgemasForm, 'material_belico/form_generico.html', 'material_belico:algemas_list', 'Algemas')

@login_required
@require_module_permission('material_belico')
def algemas_edit(request, pk):
    return _crud_edit(request, pk, Algemas, AlgemasForm, 'material_belico/form_generico.html', 'material_belico:algemas_list', 'Algemas')

@login_required
@require_module_permission('material_belico')
def algemas_delete(request, pk):
    return _crud_delete(request, pk, Algemas, 'material_belico:algemas_list', 'Algemas')


# =============================================================================
# CRUD: MUNIÇÃO QUÍMICA
# =============================================================================

@login_required
@require_module_permission('material_belico')
def municao_quimica_list(request):
    itens = MunicaoQuimica.objects.all()
    filter_fields = [
        {'label': 'Tipo', 'field': 'tipo', 'choices': [{'value': v, 'label': l} for v, l in MunicaoQuimica.TIPO_CHOICES]},
    ]
    return render(request, 'material_belico/municao_quimica_list.html', {'itens': itens, 'titulo': 'Munições Químicas', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def municao_quimica_create(request):
    return _crud_create(request, MunicaoQuimicaForm, 'material_belico/form_generico.html', 'material_belico:municao_quimica_list', 'Munição Química')

@login_required
@require_module_permission('material_belico')
def municao_quimica_edit(request, pk):
    return _crud_edit(request, pk, MunicaoQuimica, MunicaoQuimicaForm, 'material_belico/form_generico.html', 'material_belico:municao_quimica_list', 'Munição Química')

@login_required
@require_module_permission('material_belico')
def municao_quimica_delete(request, pk):
    return _crud_delete(request, pk, MunicaoQuimica, 'material_belico:municao_quimica_list', 'Munição Química')


# =============================================================================
# CRUD: MUNIÇÃO CONVENCIONAL
# =============================================================================

@login_required
@require_module_permission('material_belico')
def municao_convencional_list(request):
    itens = MunicaoConvencional.objects.all().order_by('calibre', 'subtipo', 'secao')
    filter_fields = [
        {'label': 'Calibre', 'field': 'calibre', 'choices': [{'value': v, 'label': l} for v, l in MunicaoConvencional.CALIBRE_CHOICES]},
        {'label': 'Subtipo', 'field': 'subtipo', 'choices': [{'value': v, 'label': l} for v, l in MunicaoConvencional.SUBTIPO_CHOICES]},
        {'label': 'Seção', 'field': 'secao', 'choices': [{'value': v, 'label': l} for v, l in MunicaoConvencional.SECAO_CHOICES]},
    ]
    return render(request, 'material_belico/municao_convencional_list.html', {'itens': itens, 'titulo': 'Munições Convencionais', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def municao_convencional_create(request):
    return _crud_create(request, MunicaoConvencionalForm, 'material_belico/form_generico.html', 'material_belico:municao_convencional_list', 'Munição Convencional')

@login_required
@require_module_permission('material_belico')
def municao_convencional_edit(request, pk):
    return _crud_edit(request, pk, MunicaoConvencional, MunicaoConvencionalForm, 'material_belico/form_generico.html', 'material_belico:municao_convencional_list', 'Munição Convencional')

@login_required
@require_module_permission('material_belico')
def municao_convencional_delete(request, pk):
    return _crud_delete(request, pk, MunicaoConvencional, 'material_belico:municao_convencional_list', 'Munição Convencional')


# =============================================================================
# CRUD: COLETE BALÍSTICO
# =============================================================================

@login_required
@require_module_permission('material_belico')
def colete_list(request):
    itens = ColeteBalistico.objects.all()
    tamanhos = sorted(set(itens.values_list('tamanho', flat=True)))
    filter_fields = [
        {'label': 'Marca', 'field': 'marca', 'choices': [{'value': v, 'label': l} for v, l in ColeteBalistico.MARCA_CHOICES]},
        {'label': 'Tamanho', 'field': 'tamanho', 'choices': [{'value': t, 'label': t} for t in tamanhos]},
        {'label': 'Situação', 'field': 'situacao', 'choices': [{'value': v, 'label': l} for v, l in ColeteBalistico.SITUACAO_CHOICES]},
    ]
    return render(request, 'material_belico/protecao_list.html', {'itens': itens, 'titulo': 'Coletes Balísticos', 'tipo': 'colete', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def colete_create(request):
    return _crud_create(request, ColeteBalisticoForm, 'material_belico/form_generico.html', 'material_belico:colete_list', 'Colete Balístico')

@login_required
@require_module_permission('material_belico')
def colete_edit(request, pk):
    return _crud_edit(request, pk, ColeteBalistico, ColeteBalisticoForm, 'material_belico/form_generico.html', 'material_belico:colete_list', 'Colete Balístico')

@login_required
@require_module_permission('material_belico')
def colete_delete(request, pk):
    return _crud_delete(request, pk, ColeteBalistico, 'material_belico:colete_list', 'Colete Balístico')


# =============================================================================
# CRUD: ESCUDO BALÍSTICO
# =============================================================================

@login_required
@require_module_permission('material_belico')
def escudo_list(request):
    itens = EscudoBalistico.objects.all()
    filter_fields = [
        {'label': 'Situação', 'field': 'situacao', 'choices': [{'value': v, 'label': l} for v, l in EscudoBalistico.SITUACAO_CHOICES]},
        {'label': 'Lote/Cia', 'field': 'lote', 'choices': [{'value': v, 'label': l} for v, l in EscudoBalistico.LOTE_CHOICES]},
    ]
    return render(request, 'material_belico/protecao_list.html', {'itens': itens, 'titulo': 'Escudos Balísticos', 'tipo': 'escudo', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def escudo_create(request):
    return _crud_create(request, EscudoBalisticoForm, 'material_belico/form_generico.html', 'material_belico:escudo_list', 'Escudo Balístico')

@login_required
@require_module_permission('material_belico')
def escudo_edit(request, pk):
    return _crud_edit(request, pk, EscudoBalistico, EscudoBalisticoForm, 'material_belico/form_generico.html', 'material_belico:escudo_list', 'Escudo Balístico')

@login_required
@require_module_permission('material_belico')
def escudo_delete(request, pk):
    return _crud_delete(request, pk, EscudoBalistico, 'material_belico:escudo_list', 'Escudo Balístico')


# =============================================================================
# CRUD: CAPACETE BALÍSTICO
# =============================================================================

@login_required
@require_module_permission('material_belico')
def capacete_list(request):
    itens = CapaceteBalistico.objects.all()
    filter_fields = [
        {'label': 'Material', 'field': 'material', 'choices': [{'value': v, 'label': l} for v, l in CapaceteBalistico.MATERIAL_CHOICES]},
        {'label': 'Condição', 'field': 'condicao', 'choices': [{'value': v, 'label': l} for v, l in CapaceteBalistico.CONDICAO_CHOICES]},
    ]
    return render(request, 'material_belico/protecao_list.html', {'itens': itens, 'titulo': 'Capacetes Balísticos', 'tipo': 'capacete', 'filter_fields': filter_fields})

@login_required
@require_module_permission('material_belico')
def capacete_create(request):
    return _crud_create(request, CapaceteBalisticoForm, 'material_belico/form_generico.html', 'material_belico:capacete_list', 'Capacete Balístico')

@login_required
@require_module_permission('material_belico')
def capacete_edit(request, pk):
    return _crud_edit(request, pk, CapaceteBalistico, CapaceteBalisticoForm, 'material_belico/form_generico.html', 'material_belico:capacete_list', 'Capacete Balístico')

@login_required
@require_module_permission('material_belico')
def capacete_delete(request, pk):
    return _crud_delete(request, pk, CapaceteBalistico, 'material_belico:capacete_list', 'Capacete Balístico')
