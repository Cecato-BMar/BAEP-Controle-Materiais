"""
Script para importação dos Kits Operacionais da aba 'KIT OP'
da PLANILHA DE MATERIAS - Atualizada .xlsx do 2º BAEP

Estrutura da planilha (colunas 0-indexed):
- Kits ficam em pares, 2 por bloco de linhas
- Kit Esquerdo: col B(1)=TIPO, C(2)=PATRIMÔNIO, D(3)=RED DOT, E(4)=MAGNIFER
- Kit Direito: col G(6)=TIPO, H(7)=PATRIMÔNIO, I(8)=RED DOT, J(9)=MAGNIFER

Tipos de linha de dados por kit:
  'SCAR CAL. 556'      → fuzil_556_1 / fuzil_556_2
  'SCAR CAL. 762'      → fuzil_762
  'IMBEL IA2 CAL. 556' → fuzil_556_1 / fuzil_556_2
  'BENELLI CAL. 12 Nº' → espingarda
  'HT Nº '             → radio_ht (col C=patrimônio) + AM-640 (col E=série)
  'ESCUDO Nº '         → escudo (col C=numero)
"""
import os, sys, django

sys.path.insert(0, '/home/servidor-sys-baep/BAEP-Controle-Materiais')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

import openpyxl
from material_belico.models import (
    KitOperacional, Fuzil, EspingardaCal12, RadioHT, AM640, EscudoBalistico
)

EXCEL_PATH = '/home/servidor-sys-baep/BAEP-Controle-Materiais/BAEP-Controle-Materiais-2/PLANILHA DE MATERIAS - Atualizada .xlsx'


def clean(v):
    if v is None:
        return None
    s = str(v).strip()
    if s in ('', 'None', '────────', '---------', '----------', '#REF!', '#N/A', 'S/ ACESSÓRIO'):
        return None
    return s


def parse_kit_number(titulo):
    """Converte título da aba para numero_kit válido no model."""
    if titulo is None:
        return None
    t = str(titulo).strip().upper()
    # KIT OPERACIONAL 01 → '1'
    if 'OPERACIONAL' in t:
        for i in range(1, 13):
            if str(i).zfill(2) in t or f' {i}' in t:
                return str(i)
    # CMT / SUBCMT
    if 'COMANDANTE' in t and 'SUB' not in t:
        return 'CMT'
    if 'SUBCOMANDANTE' in t or ('SUB' in t and 'COMANDANTE' in t):
        return 'SUBCMT'
    # AT-01 .. AT-04
    for at in ['AT-01', 'AT-02', 'AT-03', 'AT-04']:
        if at in t or (f'AT-0{at[-1]}' in t):
            return at
    if 'AT-01' in t or '(AT-01)' in t: return 'AT-01'
    if 'AT-02' in t or '(AT-02)' in t: return 'AT-02'
    if 'AT-03' in t or '(AT-03)' in t: return 'AT-03'
    if 'AT-04' in t or '(AT-04)' in t: return 'AT-04'
    if 'GUARDA' in t: return 'GUARDA'
    return None


def get_fuzil(patrimonio_or_serie):
    v = clean(patrimonio_or_serie)
    if not v:
        return None
    obj = Fuzil.objects.filter(patrimonio=v).first()
    if not obj:
        obj = Fuzil.objects.filter(observacoes__icontains=f'Série: {v}').first()
    return obj


def get_espingarda(numero):
    v = clean(numero)
    if not v:
        return None
    return EspingardaCal12.objects.filter(numero_espingarda=v).first()


def get_radio_ht(patrimonio):
    v = clean(patrimonio)
    if not v:
        return None
    obj = RadioHT.objects.filter(patrimonio=v).first()
    if not obj:
        obj = RadioHT.objects.filter(serie=v).first()
    return obj


def get_am640(serie):
    v = clean(serie)
    if not v:
        return None
    return AM640.objects.filter(serie=v).first()


def get_escudo(numero):
    v = clean(numero)
    if not v:
        return None
    try:
        return EscudoBalistico.objects.filter(numero=int(v)).first()
    except (ValueError, TypeError):
        return None


def parse_single_kit(rows, num_kit):
    """
    Recebe lista de rows de um bloco de kit (cols 0-4 = kit esquerdo, 5-10 = direito)
    e num_kit string válido. Retorna dict com os campos para KitOperacional.
    """
    dados = {
        'fuzil_556_1': None,
        'fuzil_556_2': None,
        'fuzil_762': None,
        'espingarda': None,
        'radio_ht': None,
        'am640': None,
        'escudo': None,
    }
    fuzis_556 = []

    for row in rows:
        tipo = clean(row[0])
        pat = clean(row[1])
        col2 = clean(row[2])  # RED DOT ou AM-640 label
        col3 = clean(row[3])  # MAGNIFER ou AM-640 série

        if not tipo:
            continue

        tipo_up = tipo.upper()

        if 'SCAR CAL. 556' in tipo_up or 'IA2' in tipo_up:
            if pat:
                f = get_fuzil(pat)
                if f:
                    fuzis_556.append(f)

        elif 'SCAR CAL. 762' in tipo_up:
            if pat:
                dados['fuzil_762'] = get_fuzil(pat)

        elif 'BENELLI' in tipo_up or 'CAL. 12' in tipo_up:
            if pat:
                dados['espingarda'] = get_espingarda(pat)

        elif 'HT' in tipo_up:
            if pat:
                dados['radio_ht'] = get_radio_ht(pat)
            # AM-640 está na mesma linha: col2='AM-640', col3=série
            if col2 == 'AM-640' and col3:
                dados['am640'] = get_am640(col3)

        elif 'ESCUDO' in tipo_up:
            if pat:
                dados['escudo'] = get_escudo(pat)

    if fuzis_556:
        dados['fuzil_556_1'] = fuzis_556[0]
    if len(fuzis_556) >= 2:
        dados['fuzil_556_2'] = fuzis_556[1]

    return dados


def import_kits():
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb['KIT OP']

    all_rows = list(ws.iter_rows(values_only=True))

    # Estado do parser
    kit_blocks = []  # lista de (numero_kit, [rows_left], [rows_right])
    current_left_num = None
    current_right_num = None
    collecting = False
    left_rows = []
    right_rows = []

    for r_idx, row in enumerate(all_rows, start=1):
        col_b = row[1] if len(row) > 1 else None   # Col B (index 1)
        col_g = row[6] if len(row) > 6 else None   # Col G (index 6)

        b_str = str(col_b).strip() if col_b else ''
        g_str = str(col_g).strip() if col_g else ''

        # Detecta início de novo bloco de kit
        is_kit_header_left = (
            'KIT OPERACIONAL' in b_str.upper() or
            'KIT COMANDANTE' in b_str.upper() or
            'KIT SUBCOMANDANTE' in b_str.upper() or
            'ATIRADORES' in b_str.upper() or
            'GUARDA' in b_str.upper()
        )

        if is_kit_header_left:
            # Salva kit anterior
            if current_left_num and left_rows:
                kit_blocks.append((current_left_num, left_rows[:]))
            if current_right_num and right_rows:
                kit_blocks.append((current_right_num, right_rows[:]))

            current_left_num = parse_kit_number(col_b)
            current_right_num = parse_kit_number(col_g)
            left_rows = []
            right_rows = []
            collecting = True
            continue

        if 'TIPO DE MATERIAL' in b_str.upper():
            # Skip header row
            continue

        if collecting:
            # Linha de dados — cols para kit esquerdo: B,C,D,E (idx 1,2,3,4)
            # Cols para kit direito: G,H,I,J (idx 6,7,8,9)
            left_row_data = (
                row[1] if len(row) > 1 else None,
                row[2] if len(row) > 2 else None,
                row[3] if len(row) > 3 else None,
                row[4] if len(row) > 4 else None,
            )
            right_row_data = (
                row[6] if len(row) > 6 else None,
                row[7] if len(row) > 7 else None,
                row[8] if len(row) > 8 else None,
                row[9] if len(row) > 9 else None,
            )

            # Para 'ATIRADORES' tratamos as linhas de forma especial
            if any(v is not None for v in left_row_data):
                left_rows.append(left_row_data)
            if any(v is not None for v in right_row_data):
                right_rows.append(right_row_data)

    # Salva último bloco
    if current_left_num and left_rows:
        kit_blocks.append((current_left_num, left_rows))
    if current_right_num and right_rows:
        kit_blocks.append((current_right_num, right_rows))

    # Agora monta / salva os kits
    criados = 0
    atualizados = 0
    erros = []

    for num_kit, rows in kit_blocks:
        if not num_kit:
            continue

        # Valida que numero_kit é opção válida
        valid_choices = [c[0] for c in KitOperacional.NUMERO_KIT_CHOICES]
        if num_kit not in valid_choices:
            erros.append(f'Kit "{num_kit}" não é uma opção válida, ignorado.')
            continue

        try:
            dados = parse_single_kit(rows, num_kit)
            obj, created = KitOperacional.objects.get_or_create(numero_kit=num_kit)

            for campo, valor in dados.items():
                if valor is not None:
                    setattr(obj, campo, valor)

            # Salva sem validação completa (clean pode falhar por kits parciais)
            obj.save_base(raw=True)

            if created:
                criados += 1
                print(f'  ✅ Kit {num_kit} CRIADO — '
                      f'F556:{dados["fuzil_556_1"]} '
                      f'F762:{dados["fuzil_762"]} '
                      f'ESP:{dados["espingarda"]} '
                      f'HT:{dados["radio_ht"]} '
                      f'AM:{dados["am640"]} '
                      f'ESC:{dados["escudo"]}')
            else:
                atualizados += 1
                print(f'  🔄 Kit {num_kit} ATUALIZADO — '
                      f'F556:{dados["fuzil_556_1"]} '
                      f'F762:{dados["fuzil_762"]} '
                      f'ESP:{dados["espingarda"]} '
                      f'HT:{dados["radio_ht"]} '
                      f'AM:{dados["am640"]} '
                      f'ESC:{dados["escudo"]}')

        except Exception as e:
            erros.append(f'Kit {num_kit}: {e}')
            print(f'  ❌ Erro Kit {num_kit}: {e}')

    print()
    print('====================================')
    print(f'Kits Operacionais: {criados} criados, {atualizados} atualizados')
    if erros:
        print('Erros:')
        for e in erros:
            print(f'  - {e}')
    print('====================================')


if __name__ == '__main__':
    import_kits()
