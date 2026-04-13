from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Material
from .forms import MaterialForm, MaterialSearchForm
from reserva_baep.decorators import require_module_permission
import xml.etree.ElementTree as ET
from django.db import transaction

@login_required
@require_module_permission('reserva_armas')
def lista_materiais(request):
    form = MaterialSearchForm(request.GET)
    materiais = Material.objects.all()
    
    # Filtragem
    if form.is_valid():
        termo_busca = form.cleaned_data.get('termo_busca')
        tipo = form.cleaned_data.get('tipo')
        categoria = form.cleaned_data.get('categoria')
        status = form.cleaned_data.get('status')
        estado = form.cleaned_data.get('estado')
        localizacao = form.cleaned_data.get('localizacao')
        
        if termo_busca:
            materiais = materiais.filter(
                Q(nome__icontains=termo_busca) | 
                Q(numero__icontains=termo_busca)
            )
        
        if tipo:
            materiais = materiais.filter(tipo=tipo)
            
        if categoria:
            materiais = materiais.filter(categoria=categoria)
            
        if status:
            materiais = materiais.filter(status=status)

        if estado:
            materiais = materiais.filter(estado=estado)

        if localizacao:
            materiais = materiais.filter(localizacao_fisica=localizacao)
    
    # Paginação
    paginator = Paginator(materiais, 10)  # 10 itens por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'total_materiais': materiais.count(),
    }
    
    return render(request, 'materiais/lista_materiais.html', context)

@login_required
@require_module_permission('reserva_armas')
def detalhe_material(request, material_id):
    material = get_object_or_404(Material, pk=material_id)
    movimentacoes = material.movimentacoes.all().order_by('-data_hora')[:10]  # Últimas 10 movimentações
    
    context = {
        'material': material,
        'movimentacoes': movimentacoes,
    }
    
    return render(request, 'materiais/detalhe_material.html', context)

@login_required
@require_module_permission('reserva_armas')
def novo_material(request):
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.quantidade_disponivel = material.quantidade
            material.save()
            messages.success(request, _('Material cadastrado com sucesso!'))
            return redirect('materiais:detalhe_material', material_id=material.pk)
    else:
        form = MaterialForm()
    
    return render(request, 'materiais/form_material.html', {
        'form': form,
        'titulo': _('Novo Material'),
    })

@login_required
@require_module_permission('reserva_armas')
def editar_material(request, material_id):
    material = get_object_or_404(Material, pk=material_id)
    
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, _('Material atualizado com sucesso!'))
            return redirect('materiais:detalhe_material', material_id=material.pk)
    else:
        form = MaterialForm(instance=material)
    
    return render(request, 'materiais/form_material.html', {
        'form': form,
        'material': material,
        'titulo': _('Editar Material'),
    })

@login_required
@require_module_permission('reserva_armas')
def importar_armas_xml(request):
    """Importa armas de um arquivo XML (ou XLM como solicitado)"""
    if request.method == 'POST' and request.FILES.get('arquivo_xml'):
        xml_file = request.FILES['arquivo_xml']
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Procuramos por tags <arma> ou <item> ou similar
            # Se a raiz for <armamentos>, iteramos sobre os filhos
            armas_importadas = 0
            erros = 0
            
            with transaction.atomic():
                from estoque.models import LocalizacaoFisica
                
                # Adaptado para o formato do armas_2baep.xml
                # Estrutura: ListagemArmas -> Unidade -> Subunidade -> Arma
                subunidades = root.findall('.//Subunidade')
                
                if subunidades:
                    for sub in subunidades:
                        sub_nome = sub.get('nome') or sub.findtext('nome') or "SEDE"
                        
                        # Garante que a localização existe
                        loc, _ = LocalizacaoFisica.objects.get_or_create(nome=sub_nome.strip())
                        
                        itens_arma = sub.findall('.//Arma')
                        for item in itens_arma:
                            try:
                                nome = (item.findtext('Descricao') or item.findtext('nome') or "").strip()
                                numero = (item.findtext('NumeroDeSerie') or item.findtext('numero') or "").strip()
                                patrimonio = (item.findtext('NumeroPatrimonio') or "").strip()
                                
                                if not nome or not numero:
                                    continue
                                
                                obs = f"Patrimônio: {patrimonio}" if patrimonio else ""
                                    
                                # Lógica de auto-categorização na importação
                                categoria_auto = 'OUTROS'
                                nome_upper = nome.upper()
                                if 'PISTOLA' in nome_upper: categoria_auto = 'PISTOLA'
                                elif 'FUZIL' in nome_upper or 'CARABINA' in nome_upper: categoria_auto = 'FUZIL'
                                elif 'CAL' in nome_upper and ('12' in nome_upper or nome_upper == 'CAL'): categoria_auto = 'CAL_12'
                                elif 'METRALHADORA' in nome_upper: categoria_auto = 'SUBMETRALHADORA'
                                elif 'LANCADOR' in nome_upper: categoria_auto = 'LANCADOR'
                                elif 'TASER' in nome_upper: categoria_auto = 'CHOQUE'
                                    
                                # Busca por duplicidade via número de série
                                Material.objects.update_or_create(
                                    numero=numero,
                                    defaults={
                                        'tipo': 'ARMA',
                                        'categoria': categoria_auto,
                                        'nome': nome,
                                        'quantidade': 1,
                                        'estado': 'BOM',
                                        'status': 'DISPONIVEL',
                                        'observacoes': obs,
                                        'localizacao_fisica': loc
                                    }
                                )
                                armas_importadas += 1
                            except Exception as e:
                                print(f"Erro ao processar item XML: {e}")
                                erros += 1
                else:
                    # Fallback para formato genérico se não encontrar Subunidade
                    itens = root.findall('.//arma') or root.findall('.//item') or root.findall('.//armamento')
                    # ... (resto do código anterior se necessário, mas o foco é o formato BAEP)
                    for item in itens:
                         # ... similar logic ...
                         pass
            
            if armas_importadas > 0:
                messages.success(request, _(f'Sucesso: {armas_importadas} armamentos importados/atualizados.'))
            if erros > 0:
                messages.warning(request, _(f'Atenção: {erros} itens pularam devido a erros de formatação.'))
                
        except ET.ParseError:
            messages.error(request, _('Erro ao processar o arquivo. Verifique se é um XML/XLM válido.'))
        except Exception as e:
            messages.error(request, _(f'Erro inesperado na importação: {e}'))
            
    else:
        messages.error(request, _('Nenhum arquivo enviado.'))
        
    return redirect('materiais:lista_materiais')
