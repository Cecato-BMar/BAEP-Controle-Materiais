from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from .models import CategoriaPatrimonio, BemPatrimonial, ItemPatrimonial, MovimentacaoPatrimonio
from .forms import BemPatrimonialForm, ItemPatrimonialForm, MovimentacaoPatrimonioForm
from reserva_baep.decorators import require_module_permission

@login_required
@require_module_permission('patrimonio')
def dashboard_patrimonio(request):
    total_itens = ItemPatrimonial.objects.count()
    em_uso = ItemPatrimonial.objects.filter(status='EM_USO').count()
    disponiveis = ItemPatrimonial.objects.filter(status='DISPONIVEL').count()
    manutencao = ItemPatrimonial.objects.filter(status='MANUTENCAO').count()
    
    valor_total = ItemPatrimonial.objects.aggregate(total=Sum('bem__valor_unitario_estimado'))['total'] or 0
    
    ultimas_movimentacoes = MovimentacaoPatrimonio.objects.select_related('item', 'item__bem', 'policial', 'registrado_por').order_by('-data_hora')[:10]
    
    por_categoria = CategoriaPatrimonio.objects.annotate(total=Count('bens__itens')).filter(total__gt=0)
    
    # Dados para Gráficos
    status_counts_qs = ItemPatrimonial.objects.values('status').annotate(total=Count('id'))
    status_map = dict(ItemPatrimonial.STATUS_CHOICES)
    status_labels = [status_map.get(s['status']) for s in status_counts_qs]
    status_data = [s['total'] for s in status_counts_qs]
    
    cat_labels = [c.nome for c in por_categoria]
    cat_data = [c.total for c in por_categoria]
    
    context = {
        'total_itens': total_itens,
        'em_uso': em_uso,
        'disponiveis': disponiveis,
        'manutencao': manutencao,
        'valor_total': valor_total,
        'ultimas_movimentacoes': ultimas_movimentacoes,
        'por_categoria': por_categoria,
        'status_labels': status_labels,
        'status_data': status_data,
        'cat_labels': cat_labels,
        'cat_data': cat_data,
    }
    return render(request, 'patrimonio/dashboard.html', context)

@login_required
@require_module_permission('patrimonio')
def lista_itens(request):
    qs = ItemPatrimonial.objects.select_related('bem', 'bem__categoria', 'localizacao', 'responsavel_atual').all()
    q = request.GET.get('q')
    status = request.GET.get('status')
    categoria = request.GET.get('categoria')
    
    if q:
        qs = qs.filter(
            Q(numero_patrimonio__icontains=q) |
            Q(numero_serie__icontains=q) |
            Q(bem__nome__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    if categoria:
        qs = qs.filter(bem__categoria_id=categoria)
        
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    categorias = CategoriaPatrimonio.objects.all()
    
    return render(request, 'patrimonio/lista_itens.html', {
        'page_obj': page_obj,
        'q': q,
        'status_filtro': status,
        'categoria_filtro': categoria,
        'categorias': categorias,
        'status_choices': ItemPatrimonial.STATUS_CHOICES,
    })

@login_required
@require_module_permission('patrimonio')
def detalhe_item(request, pk):
    item = get_object_or_404(ItemPatrimonial.objects.select_related('bem', 'bem__categoria', 'localizacao', 'responsavel_atual'), pk=pk)
    historico = item.historico.select_related('policial', 'local_destino', 'registrado_por').order_by('-data_hora')
    
    return render(request, 'patrimonio/detalhe_item.html', {
        'item': item,
        'historico': historico,
    })

@login_required
@require_module_permission('patrimonio')
def novo_item(request):
    if request.method == 'POST':
        form = ItemPatrimonialForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'Item {item.numero_patrimonio} cadastrado com sucesso!')
            return redirect('patrimonio:detalhe_item', pk=item.pk)
    else:
        form = ItemPatrimonialForm()
    return render(request, 'patrimonio/form_item.html', {'form': form, 'titulo': 'Novo Item Patrimonial'})

@login_required
@require_module_permission('patrimonio')
def editar_item(request, pk):
    item = get_object_or_404(ItemPatrimonial, pk=pk)
    if request.method == 'POST':
        form = ItemPatrimonialForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f'Item {item.numero_patrimonio} atualizado!')
            return redirect('patrimonio:detalhe_item', pk=pk)
    else:
        form = ItemPatrimonialForm(instance=item)
    return render(request, 'patrimonio/form_item.html', {'form': form, 'titulo': f'Editar Item {item.numero_patrimonio}'})

@login_required
@require_module_permission('patrimonio')
def registrar_movimentacao(request):
    item_id = request.GET.get('item')
    initial = {}
    if item_id:
        initial['item'] = get_object_or_404(ItemPatrimonial, pk=item_id)
        
    if request.method == 'POST':
        form = MovimentacaoPatrimonioForm(request.POST)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.registrado_por = request.user
            mov.save()
            
            # Lógica de atualização de status do item
            item = mov.item
            if mov.tipo == 'CAUTELA':
                item.status = 'EM_USO'
                item.responsavel_atual = mov.policial
            elif mov.tipo == 'DEVOLUCAO':
                item.status = 'DISPONIVEL'
                item.responsavel_atual = None
            elif mov.tipo == 'MANUTENCAO_INICIO':
                item.status = 'MANUTENCAO'
            elif mov.tipo == 'MANUTENCAO_FIM':
                item.status = 'DISPONIVEL'
            elif mov.tipo == 'TRANSFERENCIA':
                if mov.local_destino:
                    item.localizacao = mov.local_destino
            elif mov.tipo == 'BAIXA':
                item.status = 'BAIXADO'
                
            item.save()
            messages.success(request, 'Movimentação registrada com sucesso!')
            return redirect('patrimonio:detalhe_item', pk=item.pk)
    else:
        form = MovimentacaoPatrimonioForm(initial=initial)
        
    return render(request, 'patrimonio/form_movimentacao.html', {'form': form, 'titulo': 'Registrar Movimentação de Patrimônio'})

@login_required
@require_module_permission('patrimonio')
def lista_bens(request):
    """Catálogo de tipos de bens"""
    qs = BemPatrimonial.objects.select_related('categoria').annotate(num_itens=Count('itens'))
    q = request.GET.get('q')
    if q:
        qs = qs.filter(nome__icontains=q)
    
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'patrimonio/lista_bens.html', {
        'page_obj': page_obj,
        'q': q
    })

@login_required
@require_module_permission('patrimonio')
def novo_bem(request):
    if request.method == 'POST':
        form = BemPatrimonialForm(request.POST)
        if form.is_valid():
            bem = form.save()
            messages.success(request, f'Bem "{bem.nome}" cadastrado no catálogo!')
            return redirect('patrimonio:lista_bens')
    else:
        form = BemPatrimonialForm()
    return render(request, 'patrimonio/form_bem.html', {'form': form, 'titulo': 'Novo Bem no Catálogo'})

@login_required
@require_module_permission('patrimonio')
def editar_bem(request, pk):
    bem = get_object_or_404(BemPatrimonial, pk=pk)
    if request.method == 'POST':
        form = BemPatrimonialForm(request.POST, instance=bem)
        if form.is_valid():
            form.save()
            messages.success(request, f'Bem "{bem.nome}" atualizado!')
            return redirect('patrimonio:lista_bens')
    else:
        form = BemPatrimonialForm(instance=bem)
    return render(request, 'patrimonio/form_bem.html', {'form': form, 'titulo': f'Editar {bem.nome}'})

@login_required
@require_module_permission('patrimonio')
def importar_bens(request):
    """Importa Bens Permanentes do arquivo XML do SILP (PMESP) ou planilha Excel.
    
    Estrutura XML esperada (SILP):
    <ListagemControleMaterial>
      <Categoria nome="...">
        <Subcategoria nome="...">
          <Item>
            <CodigoMaterial>...</CodigoMaterial>
            <NumeroPatrimonio>...</NumeroPatrimonio>
            <NumeroSerie>...</NumeroSerie>
            <NomeMaterial>...</NomeMaterial>
            <Especificacao>...</Especificacao>
            <ValorRS>...</ValorRS>
            <DataInclusao>...</DataInclusao>
            <ContaPatrimonial>...</ContaPatrimonial>
          </Item>
        </Subcategoria>
      </Categoria>
    </ListagemControleMaterial>
    """
    if request.method == 'POST' and request.FILES.get('arquivo_importacao'):
        arquivo = request.FILES['arquivo_importacao']
        nome_arquivo = arquivo.name.lower()
        
        itens_importados = 0
        bens_catalogo_criados = 0
        categorias_criadas = 0
        erros = 0
        
        try:
            if nome_arquivo.endswith('.xml'):
                import xml.etree.ElementTree as ET
                from datetime import datetime
                from decimal import Decimal, InvalidOperation
                
                tree = ET.parse(arquivo)
                root = tree.getroot()
                
                # Percorre a hierarquia Categoria > Subcategoria > Item
                for cat_elem in root.findall('.//Categoria'):
                    cat_nome = cat_elem.get('nome', 'GERAL')
                    cat_obj, cat_created = CategoriaPatrimonio.objects.get_or_create(nome=cat_nome)
                    if cat_created:
                        categorias_criadas += 1
                    
                    for subcat_elem in cat_elem.findall('.//Subcategoria'):
                        subcat_nome = subcat_elem.get('nome', '')
                        
                        for item_elem in subcat_elem.findall('.//Item'):
                            try:
                                codigo_material = (item_elem.findtext('CodigoMaterial') or '').strip()
                                num_patrimonio = (item_elem.findtext('NumeroPatrimonio') or '').strip()
                                num_serie = (item_elem.findtext('NumeroSerie') or '').strip()
                                nome_material = (item_elem.findtext('NomeMaterial') or '').strip()
                                especificacao = (item_elem.findtext('Especificacao') or '').strip()
                                valor_str = (item_elem.findtext('ValorRS') or '0').strip()
                                data_inclusao_str = (item_elem.findtext('DataInclusao') or '').strip()
                                
                                if not nome_material or not num_patrimonio:
                                    erros += 1
                                    continue
                                
                                # Valor: o SILP envia centavos (ex "16225" = R$ 162,25)
                                try:
                                    valor_centavos = int(valor_str)
                                    valor_decimal = Decimal(valor_centavos) / Decimal(100)
                                except (ValueError, InvalidOperation):
                                    valor_decimal = Decimal('0.00')
                                
                                # Data de inclusão
                                data_aquisicao = None
                                if data_inclusao_str:
                                    for fmt in ('%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d'):
                                        try:
                                            data_aquisicao = datetime.strptime(data_inclusao_str, fmt).date()
                                            break
                                        except ValueError:
                                            continue
                                
                                # Descrição do bem para o catálogo
                                descricao_catalogo = especificacao
                                if subcat_nome:
                                    descricao_catalogo = f"{subcat_nome} — {especificacao}" if especificacao else subcat_nome
                                
                                # Cria/obtém o tipo de bem no catálogo (BemPatrimonial)
                                bem_nome = nome_material[:200]
                                bem_obj, bem_created = BemPatrimonial.objects.get_or_create(
                                    nome=bem_nome,
                                    categoria=cat_obj,
                                    defaults={
                                        'descricao': descricao_catalogo,
                                        'valor_unitario_estimado': valor_decimal,
                                        'ativo': True,
                                    }
                                )
                                if bem_created:
                                    bens_catalogo_criados += 1
                                
                                # Cria o item individual (ItemPatrimonial)
                                item_obj, item_created = ItemPatrimonial.objects.update_or_create(
                                    numero_patrimonio=num_patrimonio,
                                    defaults={
                                        'bem': bem_obj,
                                        'numero_serie': num_serie if num_serie else None,
                                        'data_aquisicao': data_aquisicao,
                                        'status': 'DISPONIVEL',
                                        'estado_conservacao': 'BOM',
                                        'observacoes': f"Código SILP: {codigo_material}" if codigo_material else '',
                                    }
                                )
                                if item_created:
                                    itens_importados += 1
                                    
                            except Exception as e:
                                print(f"Erro importando item XML: {e}")
                                erros += 1
                
                # Caso o XML não tenha a hierarquia Categoria/Subcategoria (estrutura flat)
                if not root.findall('.//Categoria'):
                    for item_elem in root.findall('.//Item'):
                        try:
                            nome_material = (item_elem.findtext('NomeMaterial') or item_elem.findtext('nome') or '').strip()
                            num_patrimonio = (item_elem.findtext('NumeroPatrimonio') or '').strip()
                            
                            if not nome_material or not num_patrimonio:
                                erros += 1
                                continue
                            
                            cat_obj, _ = CategoriaPatrimonio.objects.get_or_create(nome='GERAL')
                            bem_obj, _ = BemPatrimonial.objects.get_or_create(
                                nome=nome_material[:200],
                                categoria=cat_obj,
                                defaults={'ativo': True}
                            )
                            
                            ItemPatrimonial.objects.update_or_create(
                                numero_patrimonio=num_patrimonio,
                                defaults={
                                    'bem': bem_obj,
                                    'status': 'DISPONIVEL',
                                    'estado_conservacao': 'BOM',
                                }
                            )
                            itens_importados += 1
                        except Exception as e:
                            print(f"Erro item XML flat: {e}")
                            erros += 1

            elif nome_arquivo.endswith('.xlsx') or nome_arquivo.endswith('.xls'):
                import pandas as pd
                from decimal import Decimal, InvalidOperation
                
                df = pd.read_excel(arquivo)
                df = df.fillna('')
                
                for _, row in df.iterrows():
                    try:
                        colunas_row = {str(k).lower().strip(): v for k, v in row.items()}
                        
                        nome = str(colunas_row.get('nomematerial', colunas_row.get('nome', colunas_row.get('bem', '')))).strip()
                        num_patrimonio = str(colunas_row.get('numeropatrimonio', colunas_row.get('patrimonio', colunas_row.get('nº patrimônio', '')))).strip()
                        
                        if not nome or not num_patrimonio:
                            erros += 1
                            continue
                            
                        nome_categoria = str(colunas_row.get('categoria', 'GERAL')).strip()
                        
                        cat_obj, _ = CategoriaPatrimonio.objects.get_or_create(nome=nome_categoria)
                        bem_obj, _ = BemPatrimonial.objects.get_or_create(
                            nome=nome[:200],
                            categoria=cat_obj,
                            defaults={'ativo': True}
                        )
                        
                        num_serie = str(colunas_row.get('numeroserie', colunas_row.get('serie', ''))).strip()
                        
                        ItemPatrimonial.objects.update_or_create(
                            numero_patrimonio=num_patrimonio,
                            defaults={
                                'bem': bem_obj,
                                'numero_serie': num_serie if num_serie else None,
                                'status': 'DISPONIVEL',
                                'estado_conservacao': 'BOM',
                            }
                        )
                        itens_importados += 1
                        
                    except Exception as e:
                        print(f"Erro linha Excel: {e}")
                        erros += 1
            else:
                messages.error(request, 'Formato de arquivo não suportado. Utilize .xlsx, .xls ou .xml.')
                return redirect('patrimonio:lista_bens')
                
            resultado = {
                'sucesso': True,
                'itens_importados': itens_importados,
                'bens_catalogo_criados': bens_catalogo_criados,
                'categorias_criadas': categorias_criadas,
                'erros': erros,
            }
            if itens_importados > 0 or bens_catalogo_criados > 0:
                summary = {
                    'itens': itens_importados,
                    'bens': bens_catalogo_criados,
                    'categorias': categorias_criadas,
                    'erros': erros,
                    'data': timezone.now().strftime('%d/%m/%Y %H:%M')
                }
                request.session['ultimo_import_patrimonio'] = summary
                
                messages.success(request,
                    f'Importação concluída! '
                    f'{itens_importados} itens patrimoniados importados, '
                    f'{bens_catalogo_criados} tipos de bem catalogados, '
                    f'{categorias_criadas} categorias criadas.'
                )
            if erros > 0:
                messages.warning(request, f'{erros} linhas/itens foram ignorados (dados faltantes ou duplicados).')

        except Exception as e:
            resultado = {
                'sucesso': False,
                'erro_geral': str(e),
                'itens_importados': 0,
                'bens_catalogo_criados': 0,
                'categorias_criadas': 0,
                'erros': 0,
            }
            messages.error(request, f'Erro durante a importação: {str(e)}')
        return redirect('patrimonio:importar_bens')

        
    ultimo_import = request.session.get('ultimo_import_patrimonio')
    return render(request, 'patrimonio/importar_bens.html', {
        'titulo': 'Importar Patrimônio (SILP/XML)',
        'ultimo_import': ultimo_import
    })


