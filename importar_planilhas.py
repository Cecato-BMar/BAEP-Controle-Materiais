"""
Importação das planilhas:
  1. Efetivo - MARÇO.xls  → policiais.Policial
  2. lcm_diversos_categorizado.xlsx → estoque (Categoria, Subcategoria, Produto, NumeroSerie, ContaPatrimonial)
"""
import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

import pandas as pd
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.db import transaction

from policiais.models import Policial
from estoque.models import (
    Categoria, Subcategoria, Produto, NumeroSerie,
    ContaPatrimonial, UnidadeMedida
)
from django.contrib.auth.models import User

# =============================================================================
# MAPS
# =============================================================================
POSTO_MAP = {
    'CEL PM': 'CEL_PM',
    'TEN CEL PM': 'TENCEL_PM',
    'MAJ PM': 'MAJ_PM',
    'CAP PM': 'CAP_PM',
    '1º TEN PM': '1TEN_PM',
    '2º TEN PM': '2TEN_PM',
    '1º SGT PM': '1SGT_PM',
    '2º SGT PM': '2SGT_PM',
    '3º SGT PM': '3SGT_PM',
    'SUBTEN PM': 'SUBTEN_PM',
    'STEN PM': 'STEN_PM',
    'CB PM': 'CB_PM',
    'SD PM': 'SD_PM',
    'SD PM 2ª C': 'SD_PM',
}

# =============================================================================
# 1) EFETIVO
# =============================================================================
def importar_efetivo():
    print("\n" + "="*60)
    print("IMPORTANDO EFETIVO - MARÇO")
    print("="*60)

    df = pd.read_excel('Efetivo - MARÇO.xls', engine='xlrd')
    criados = 0
    atualizados = 0
    erros = 0

    for _, row in df.iterrows():
        posto_raw = str(row.get('Posto/Grad', '')).strip()
        re_raw = str(row.get('RE', '')).strip()
        nome = str(row.get('NOME', '')).strip()
        cia = str(row.get('CIA', '')).strip() if pd.notna(row.get('CIA')) else ''
        funcao = str(row.get('FUNÇÃO', '')).strip() if pd.notna(row.get('FUNÇÃO')) else ''

        if not re_raw or re_raw == 'nan' or not nome or nome == 'nan':
            continue

        posto = POSTO_MAP.get(posto_raw)
        if not posto:
            print(f"  [WARN] Posto desconhecido: '{posto_raw}' para RE {re_raw} — pulando")
            erros += 1
            continue

        obs_parts = []
        if cia and cia != 'nan':
            obs_parts.append(f"CIA: {cia}")
        if funcao and funcao != 'nan':
            obs_parts.append(f"Função: {funcao}")
        obs = ' | '.join(obs_parts)

        try:
            pol, created = Policial.objects.update_or_create(
                re=re_raw,
                defaults={
                    'nome': nome[:100],
                    'posto': posto,
                    'situacao': 'ATIVO',
                    'observacoes': obs,
                }
            )
            if created:
                criados += 1
            else:
                atualizados += 1
        except Exception as e:
            print(f"  [ERRO] RE {re_raw}: {e}")
            erros += 1

    print(f"  Criados: {criados}")
    print(f"  Atualizados: {atualizados}")
    print(f"  Erros: {erros}")


# =============================================================================
# 2) LCM DIVERSOS
# =============================================================================
def parse_valor(val):
    if pd.isna(val) or val == 'R$ 1.00':
        return Decimal('0.00')
    try:
        s = str(val).replace('R$', '').replace(' ', '').replace(',', '.')
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return Decimal('0.00')


def parse_data(val):
    if pd.isna(val) or str(val).strip() in ('', 'nan'):
        return None
    try:
        if isinstance(val, datetime):
            return val.date()
        return datetime.strptime(str(val).strip()[:10], '%d/%m/%Y').date()
    except Exception:
        return None


def importar_lcm():
    print("\n" + "="*60)
    print("IMPORTANDO LCM DIVERSOS")
    print("="*60)

    df = pd.read_excel(
        'lcm_diversos_categorizado.xlsx',
        engine='openpyxl',
        header=None,
        skiprows=2,
    )
    df.columns = [
        'Categoria', 'Subcategoria', 'Cod', 'Patrimonio', 'Serie',
        'NL', 'Nome', 'Espec', 'Valor', 'DataInc', 'ContaPat',
        'Unidade', 'Subunidade'
    ]

    # Filtra linhas inválidas (primeira linha "Categoria" duplicada, etc.)
    df = df[df['Cod'].notna() & (df['Cod'] != 'Categoria')]

    master = User.objects.filter(username='master').first()
    if not master:
        print("  [ERRO] Usuário 'master' não encontrado!")
        return

    # --- Categorias ---
    cat_map = {}  # nome_categoria -> obj
    subcat_map = {}  # (cat_nome, subcat_nome) -> obj

    categorias_unicas = df['Categoria'].dropna().unique()
    codigo_cat = 100
    for cat_nome in categorias_unicas:
        cat_nome = str(cat_nome).strip()
        if not cat_nome:
            continue
        codigo_cat += 1
        obj, _ = Categoria.objects.get_or_create(
            nome=cat_nome[:100],
            defaults={'codigo': f'LCM-{codigo_cat:03d}', 'descricao': cat_nome}
        )
        cat_map[cat_nome] = obj

    # --- Subcategorias ---
    codigo_sub = 1000
    for _, row in df[['Categoria', 'Subcategoria']].drop_duplicates().iterrows():
        cat_nome = str(row['Categoria']).strip() if pd.notna(row['Categoria']) else ''
        sub_nome = str(row['Subcategoria']).strip() if pd.notna(row['Subcategoria']) else ''
        if not cat_nome or not sub_nome:
            continue
        cat_obj = cat_map.get(cat_nome)
        if not cat_obj:
            continue
        codigo_sub += 1
        obj, _ = Subcategoria.objects.get_or_create(
            nome=sub_nome[:100],
            categoria=cat_obj,
            defaults={'codigo': f'LCM-{codigo_sub:04d}'}
        )
        subcat_map[(cat_nome, sub_nome)] = obj

    print(f"  Categorias criadas/encontradas: {len(cat_map)}")
    print(f"  Subcategorias criadas/encontradas: {len(subcat_map)}")

    # --- Unidade de Medida padrão ---
    unid_medida, _ = UnidadeMedida.objects.get_or_create(
        sigla='UN', defaults={'nome': 'Unidade'}
    )

    # --- Produtos e Números de Série ---
    produtos_criados = 0
    series_criadas = 0
    produtos_atualizados = 0
    erros = 0

    # Agrupar por Cod para criar 1 produto por código
    codigos = df['Cod'].unique()
    total = len(codigos)
    print(f"  Códigos únicos: {total}")

    for i, cod in enumerate(codigos):
        if (i + 1) % 500 == 0:
            print(f"  Processando {i+1}/{total}...")

        rows = df[df['Cod'] == cod]
        first = rows.iloc[0]

        cat_nome = str(first['Categoria']).strip() if pd.notna(first['Categoria']) else ''
        sub_nome = str(first['Subcategoria']).strip() if pd.notna(first['Subcategoria']) else ''
        nome_mat = str(first['Nome']).strip() if pd.notna(first['Nome']) else f'Material {cod}'
        espec = str(first['Espec']).strip() if pd.notna(first['Espec']) else ''
        valor = parse_valor(first['Valor'])
        conta_pat_str = str(first['ContaPat']).strip() if pd.notna(first['ContaPat']) else ''

        cat_obj = cat_map.get(cat_nome)
        sub_obj = subcat_map.get((cat_nome, sub_nome))

        if not cat_obj:
            erros += 1
            continue

        # Conta Patrimonial
        conta_obj = None
        if conta_pat_str and conta_pat_str != 'nan':
            conta_obj, _ = ContaPatrimonial.objects.get_or_create(
                codigo=conta_pat_str[:30],
                defaults={'descricao': f'Conta {conta_pat_str}'}
            )

        cod_str = str(int(cod)) if isinstance(cod, float) else str(cod)

        try:
            with transaction.atomic():
                prod, created = Produto.objects.get_or_create(
                    codigo=cod_str,
                    defaults={
                        'nome': nome_mat[:200],
                        'descricao': espec[:500] if espec else '',
                        'categoria': cat_obj,
                        'subcategoria': sub_obj,
                        'preco_medio': valor,
                        'valor_unitario': valor,
                        'conta_patrimonial': conta_obj,
                        'unidade_medida': unid_medida,
                        'criado_por': master,
                        'status': 'ATIVO',
                        'controla_numero_serie': True,
                    }
                )
                if created:
                    produtos_criados += 1
                else:
                    produtos_atualizados += 1

                # Números de Série / Patrimônio
                for _, srow in rows.iterrows():
                    patrimonio = str(srow['Patrimonio']).strip() if pd.notna(srow['Patrimonio']) else ''
                    serie = str(srow['Serie']).strip() if pd.notna(srow['Serie']) else ''

                    if not patrimonio and not serie:
                        continue

                    # Usa patrimônio como chave se não tem série
                    ns_key = serie if serie and serie != 'nan' else f"PAT-{patrimonio}"
                    if not ns_key or ns_key == 'nan':
                        continue

                    try:
                        ns, ns_created = NumeroSerie.objects.get_or_create(
                            numero_serie=ns_key[:100],
                            defaults={
                                'produto': prod,
                                'patrimonio': patrimonio[:50] if patrimonio and patrimonio != 'nan' else None,
                                'status': 'ATIVO',
                            }
                        )
                        if ns_created:
                            series_criadas += 1
                    except Exception:
                        pass

        except Exception as e:
            erros += 1

    print(f"\n  Produtos criados: {produtos_criados}")
    print(f"  Produtos atualizados: {produtos_atualizados}")
    print(f"  Números de série criados: {series_criadas}")
    print(f"  Erros: {erros}")


# =============================================================================
if __name__ == '__main__':
    print("INICIANDO IMPORTAÇÃO DAS PLANILHAS")
    print("=" * 60)
    importar_efetivo()
    importar_lcm()
    print("\n" + "=" * 60)
    print("IMPORTAÇÃO CONCLUÍDA!")
    print("=" * 60)
