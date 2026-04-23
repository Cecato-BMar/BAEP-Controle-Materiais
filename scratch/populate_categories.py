import os
import django
import re

import sys

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
sys.path.append(os.getcwd())
django.setup()

from estoque.models import Categoria, Subcategoria

def populate():
    # Caminho do arquivo
    html_file = 'categorias_materiais_consumo.html'
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Encontrar blocos de categorias
    # Ex: <div class="cat-card"> ... <span class="cat-title">1. Material de escritório</span> ... </div>
    cat_blocks = re.split(r'<div class="cat-card">', content)[1:]
    
    for block in cat_blocks:
        # Extrair título da categoria
        # <span class="cat-title">1. Material de escritório</span>
        title_match = re.search(r'<span class="cat-title">(.*?)</span>', block)
        if not title_match:
            continue
            
        full_title = title_match.group(1).strip()
        # "1. Material de escritório" -> code="01", name="Material de escritório"
        parts = full_title.split('.', 1)
        cat_code = parts[0].strip().zfill(2)
        cat_name = parts[1].strip()
        
        print(f"Processando Categoria: {cat_code} - {cat_name}")
        
        # Criar ou atualizar Categoria
        categoria, created = Categoria.objects.update_or_create(
            codigo=cat_code,
            defaults={'nome': cat_name}
        )
        
        # Encontrar subcategorias
        # <div class="sub-item"><div class="sub-name">1.1 Papel e impressão</div><div class="sub-ex">Resma A4, papel ofício, fotocópia</div></div>
        sub_items = re.findall(r'<div class="sub-item">.*?<div class="sub-name">(.*?)</div>.*?<div class="sub-ex">(.*?)</div>.*?</div>', block, re.DOTALL)
        
        for sub_name_full, sub_ex in sub_items:
            sub_name_full = sub_name_full.strip()
            sub_ex = sub_ex.strip()
            
            # "1.1 Papel e impressão" -> sub_code="01.01", sub_name="Papel e impressão"
            sub_parts = sub_name_full.split(' ', 1)
            sub_code_raw = sub_parts[0].strip() # "1.1"
            sub_name = sub_parts[1].strip()
            
            # Formatando código da subcategoria: "1.1" -> "01.01"
            code_parts = sub_code_raw.split('.')
            sub_code = f"{code_parts[0].zfill(2)}.{code_parts[1].zfill(2)}"
            
            print(f"  - Subcategoria: {sub_code} - {sub_name}")
            
            # Criar ou atualizar Subcategoria
            Subcategoria.objects.update_or_create(
                codigo=sub_code,
                defaults={
                    'categoria': categoria,
                    'nome': sub_name,
                    'descricao': sub_ex
                }
            )

if __name__ == '__main__':
    populate()
    print("População concluída com sucesso!")
