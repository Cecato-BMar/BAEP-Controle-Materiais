from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from decimal import Decimal

from .models import MarcaViatura, ModeloViatura, Viatura, DespachoViatura, Abastecimento, Manutencao, Oficina, ChecklistViatura, SolicitacaoBaixaViatura
from .forms import (ViaturaForm, DespachoSaidaForm, DespachoRetornoForm,
                    AbastecimentoForm, ManutencaoForm, AgendamentoManutencaoForm, MarcaViaturaForm, 
                    ModeloViaturaForm, OficinaForm, ImportarFrotaForm, ChecklistViaturaForm,
                    SolicitacaoBaixaViaturaForm, AnaliseBaixaViaturaForm)
from reserva_baep.decorators import require_module_permission

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
    from django.utils import timezone as tz
    hoje = tz.now().date()
    agendamentos = Manutencao.objects.filter(status='AGENDADA').select_related('viatura', 'oficina_fk').order_by('data_inicio')
    agendamentos_atrasados = agendamentos.filter(data_inicio__lt=hoje).count()

    # Últimos abastecimentos
    ultimos_abastecimentos = Abastecimento.objects.select_related('viatura', 'motorista').order_by('-data_abastecimento')[:5]

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
    manutencoes = viatura.manutencoes.order_by('-data_inicio')[:10]
    despacho_ativo = viatura.despachos.filter(data_retorno__isnull=True).first()

    # Totais
    total_km_rodado = (
        viatura.despachos.filter(km_retorno__isnull=False)
        .aggregate(total=Sum('km_retorno') - Sum('km_saida'))['total'] or Decimal('0')
    )
    total_combustivel = viatura.abastecimentos.aggregate(total=Sum('quantidade_litros'))['total'] or Decimal('0')
    custo_total_manutencao = sum(m.custo_total for m in viatura.manutencoes.all())

    return render(request, 'viaturas/detalhe_viatura.html', {
        'viatura': viatura,
        'despachos': despachos,
        'abastecimentos': abastecimentos,
        'manutencoes': manutencoes,
        'despacho_ativo': despacho_ativo,
        'total_km_rodado': total_km_rodado,
        'total_combustivel': total_combustivel,
        'custo_total_manutencao': custo_total_manutencao,
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
            messages.success(request, f'Despacho da viatura {despacho.viatura.prefixo} registrado!')
            return redirect('viaturas:lista_despachos')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = DespachoSaidaForm()
    return render(request, 'viaturas/form_despacho.html', {'form': form, 'titulo': 'Registrar Despacho (Saída)'})


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
    man = get_object_or_404(Manutencao.objects.select_related('viatura', 'oficina_fk', 'registrado_por'), pk=pk)
    return render(request, 'viaturas/detalhe_manutencao.html', {'manutencao': man})


@login_required
@require_module_permission('frota')
def concluir_manutencao(request, pk):
    man = get_object_or_404(Manutencao, pk=pk, data_conclusao__isnull=True)
    man.data_conclusao = timezone.now().date()
    man.status = 'CONCLUIDA'
    man.save() # O método save do modelo Manutencao já cuida de liberar a viatura
    
    viatura = man.viatura
    
    messages.success(request, f'Manutenção da viatura {viatura.prefixo} marcada como concluída!')
    return redirect('viaturas:lista_manutencoes')


@login_required
@require_module_permission('frota')
def criar_manutencao(request):
    if request.method == 'POST':
        form = ManutencaoForm(request.POST, request.FILES)
        if form.is_valid():
            man = form.save(commit=False)
            man.registrado_por = request.user
            man.save() # O método save do modelo Manutencao atualiza o status e a localização da viatura automaticamente
            
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
        form = ManutencaoForm(request.POST, request.FILES, instance=man)
        if form.is_valid():
            m = form.save() # O método save do modelo Manutencao atualiza o status e a localização da viatura automaticamente
            
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
    agend.status = 'ABERTA'
    agend.data_inicio = timezone.now().date()
    agend.save()
    messages.success(request, f'Agendamento da viatura {agend.viatura.prefixo} iniciado como manutenção Em Aberto!')
    return redirect('viaturas:lista_manutencoes')


@login_required
@require_module_permission('frota')
def cancelar_agendamento(request, pk):
    """Cancela um agendamento."""
    agend = get_object_or_404(Manutencao, pk=pk, status='AGENDADA')
    agend.status = 'CANCELADA'
    agend.save()
    messages.warning(request, f'Agendamento da viatura {agend.viatura.prefixo} cancelado.')
    return redirect('viaturas:lista_agendamentos')


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
    """View para o gestor de frota analisar (Aprovar/Negar) uma baixa."""
    solicitacao = get_object_or_404(SolicitacaoBaixaViatura, pk=pk)
    
    if request.method == 'POST':
        form = AnaliseBaixaViaturaForm(request.POST, instance=solicitacao)
        if form.is_valid():
            analise = form.save(commit=False)
            analise.analisado_por = request.user
            analise.data_analise = timezone.now()
            analise.save() # Se for APROVADA, o método save() do model já altera o status da viatura
            messages.success(request, f'Solicitação #{analise.id} atualizada com sucesso.')
            return redirect('viaturas:lista_baixas')
    else:
        form = AnaliseBaixaViaturaForm(instance=solicitacao)

    return render(request, 'viaturas/analisar_baixa.html', {'form': form, 'solicitacao': solicitacao})

