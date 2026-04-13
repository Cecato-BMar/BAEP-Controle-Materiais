import os
import django
import pdfplumber
import sys
from decimal import Decimal
from datetime import datetime

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

from estoque.models import Produto, Categoria, ContaPatrimonial, NumeroSerie
from django.contrib.auth.models import User

def parse_date(date_str):
    if not date_str or date_str == '0':
        return None
    try:
        # Expected formats: 05/30/2018 or 05/07/2020
        return datetime.strptime(date_str.split('\n')[0].strip(), '%m/%d/%Y').date()
    except Exception:
        return None

import re

def parse_value(val_str):
    if not val_str:
        return Decimal('0.00')
    try:
        # OCR on this PDF is messy. Values often look like "R$ 2735.00" or "F/RU$H 80000.0"
        # Try to find a pattern like XXX.XX or XXX,XX at the end or after $
        matches = re.findall(r'(\d+[.,]\d{2})', val_str)
        if matches:
            # Take the last match which is usually the price
            clean_val = matches[-1].replace(',', '.')
            res = Decimal(clean_val)
            if res < 500000: # Individual items > 500k are unlikely in this list
                return res
        
        # Fallback to older method but more restricted
        clean_val = "".join(c for c in val_str if c.isdigit() or c == '.')
        if '.' in clean_val:
            parts = clean_val.split('.')
            clean_val = parts[-2] + "." + parts[-1] if len(parts) > 1 else parts[0]
            
        if not clean_val or clean_val == '.':
            return Decimal('0.00')
            
        res = Decimal(clean_val)
        if res > 500000: 
             return Decimal('0.00')
        return res
    except Exception:
        return Decimal('0.00')

def import_materials(pdf_path):
    user = User.objects.filter(username='master').first()
    if not user:
        print("User 'master' not found. Cannot proceed.")
        return

    # Default category
    category, _ = Categoria.objects.get_or_create(nome='Geral', defaults={'codigo': '001'})

    count_products = 0
    count_series = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                headers = table[0]
                # Map headers to indices
                try:
                    idx_cod = headers.index('Cod Material')
                    idx_pat = headers.index('Patrimnio') if 'Patrimnio' in headers else headers.index('Patrimônio')
                    idx_serie = headers.index('N. Srie') if 'N. Srie' in headers else headers.index('N. Série')
                    idx_nome = headers.index('Nome do material')
                    idx_specs = headers.index('Especificaes') if 'Especificaes' in headers else headers.index('Especificações')
                    idx_valor = headers.index('Valor')
                    idx_data = headers.index('Data Incluso') if 'Data Incluso' in headers else headers.index('Data Inclusão')
                    idx_conta_pat = headers.index('Conta Pat')
                except ValueError as e:
                    print(f"Skipping table in page {page_idx+1}: Header missing - {e}")
                    continue

                for row in table[1:]:
                    if not row[idx_cod] or not row[idx_nome]:
                        continue

                    # Handle multiple entries in one row (newline-separated)
                    cods = str(row[idx_cod]).split('\n')
                    patrimonios = str(row[idx_pat]).split('\n')
                    series = str(row[idx_serie]).split('\n')
                    nomes = str(row[idx_nome]).split('\n')
                    specs = str(row[idx_specs]).split('\n')
                    val_str = str(row[idx_valor])
                    conta_pat_str = str(row[idx_conta_pat]).split('\n')[0].strip()

                    # Create ContaPatrimonial if exists
                    conta_obj = None
                    if conta_pat_str:
                        conta_obj, _ = ContaPatrimonial.objects.get_or_create(
                            codigo=conta_pat_str,
                            defaults={'descricao': f'Conta {conta_pat_str}'}
                        )

                    # Iterate over the sub-items in the row
                    # Usually if there are multiple, they correspond to multiple serial numbers for the same product type in that row
                    for i in range(max(len(cods), len(series), len(patrimonios))):
                        cur_cod = cods[i].strip() if i < len(cods) else cods[0].strip()
                        cur_nome = nomes[i].strip() if i < len(nomes) else nomes[0].strip()
                        cur_spec = specs[i].strip() if i < len(specs) else specs[0].strip()
                        cur_pat = patrimonios[i].strip() if i < len(patrimonios) else None
                        cur_ser = series[i].strip() if i < len(series) else None
                        
                        # Get or create Produkt
                        prod, created = Produto.objects.get_or_create(
                            codigo=cur_cod,
                            defaults={
                                'nome': cur_nome,
                                'descricao': cur_spec,
                                'categoria': category,
                                'preco_medio': parse_value(val_str),
                                'conta_patrimonial': conta_obj,
                                'criado_por': user,
                                'status': 'ATIVO'
                            }
                        )
                        if created:
                            count_products += 1
                        
                        # Handle Serial Number / Patrimony
                        if cur_ser and cur_ser != '0' or cur_pat and cur_pat != '0':
                            # Unique series for this product or global? Model says unique=True for numero_serie
                            ser_obj, ser_created = NumeroSerie.objects.get_or_create(
                                numero_serie=cur_ser if (cur_ser and cur_ser != '0') else f"PAT-{cur_pat}",
                                defaults={
                                    'produto': prod,
                                    'patrimonio': cur_pat if (cur_pat and cur_pat != '0') else None,
                                    'status': 'ATIVO'
                                }
                            )
                            if ser_created:
                                count_series += 1

    print(f"Import finished!")
    print(f"New Products: {count_products}")
    print(f"New Serial Numbers/Assets: {count_series}")

if __name__ == "__main__":
    import_materials("LCM-Diversos.pdf")
