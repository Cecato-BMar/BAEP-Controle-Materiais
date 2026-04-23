import os

def refactor():
    file_path = r'c:\Users\2BAEP-32KVB92\Desktop\Projetos\BAEP-Controle-Materiais\relatorios\views.py'
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    new_lines = []
    skip = False
    
    # Definições das novas funções
    funcao_materiais = """@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_materiais(request):
    \"\"\"Gera relatório detalhado de materiais usando o motor unificado\"\"\"
    if request.method == 'POST':
        form = RelatorioMateriaisForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo') or "Relatório de Materiais"
            relatorio = _gerar_pdf_unificado(request, 'MATERIAIS', titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, 'Relatório de Materiais Gerado com Sucesso!')
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioMateriaisForm()
    return render(request, 'relatorios/form_relatorio_materiais.html', {'form': form})

"""

    funcao_movimentacoes = """@login_required
@require_module_permission('reserva_armas')
def gerar_relatorio_movimentacoes(request):
    \"\"\"Gera relatório de movimentações de arsenal usando o motor unificado\"\"\"
    if request.method == 'POST':
        form = RelatorioMovimentacoesForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo') or "Relatório de Movimentações"
            relatorio = _gerar_pdf_unificado(request, 'MOVIMENTACOES', titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, 'Relatório de Movimentações Gerado com Sucesso!')
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioMovimentacoesForm()
    return render(request, 'relatorios/form_relatorio_movimentacoes.html', {'form': form})

"""

    funcao_patrimonio = """@login_required
@require_module_permission('patrimonio')
def gerar_relatorio_patrimonio(request):
    \"\"\"Gera relatório de patrimônio usando o motor unificado\"\"\"
    if request.method == 'POST':
        form = RelatorioPatrimonioForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data.get('titulo') or "Relatório de Patrimônio"
            relatorio = _gerar_pdf_unificado(request, 'PATRIMONIO_INVENTARIO', titulo, form.cleaned_data)
            if relatorio:
                messages.success(request, 'Relatório de Patrimônio Gerado com Sucesso!')
                return redirect('relatorios:detalhe_relatorio', relatorio_id=relatorio.pk)
    else:
        form = RelatorioPatrimonioForm()
    return render(request, 'relatorios/form_relatorio_patrimonio.html', {'form': form})

"""

    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Detecta início das funções que queremos substituir ou remover
        if 'def gerar_relatorio_materiais' in line:
            new_lines.append(funcao_materiais)
            # Pula até a próxima função ou fim do arquivo
            i += 1
            while i < len(lines) and 'def gerar_relatorio_' not in lines[i]:
                i += 1
            continue
            
        if 'def gerar_relatorio_movimentacoes' in line:
            new_lines.append(funcao_movimentacoes)
            i += 1
            while i < len(lines) and 'def gerar_relatorio_' not in lines[i]:
                i += 1
            continue

        if 'def gerar_relatorio_patrimonio' in line:
            new_lines.append(funcao_patrimonio)
            i += 1
            while i < len(lines) and 'def gerar_relatorio_' not in lines[i]:
                i += 1
            # Se houver outra duplicata depois, o loop irá detectá-la pelo nome e podemos ignorá-la
            continue
            
        if 'def gerar_relatorio_estoque_movimentacoes' in line:
             # Por enquanto mantemos a primeira ocorrência mas limpamos se houver duplicata
             new_lines.append(line)
             i += 1
             continue

        new_lines.append(line)
        i += 1

    # Segunda passada para remover duplicatas exatas de nomes de função
    final_lines = []
    seen_functions = set()
    i = 0
    while i < len(new_lines):
        line = new_lines[i]
        if 'def ' in line and '(' in line:
            func_name = line.split('def ')[1].split('(')[0]
            if func_name in ['gerar_relatorio_patrimonio', 'gerar_relatorio_estoque_movimentacoes']:
                if func_name in seen_functions:
                    # Pula a duplicata
                    i += 1
                    while i < len(new_lines) and 'def ' not in new_lines[i] and '@login_required' not in new_lines[i]:
                        i += 1
                    continue
                seen_functions.add(func_name)
        final_lines.append(line)
        i += 1

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(final_lines)
    print("Refatoração concluída com sucesso!")

if __name__ == "__main__":
    refactor()
