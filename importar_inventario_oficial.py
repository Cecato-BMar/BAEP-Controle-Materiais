import os
import sys
import django

# Configurar Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

from inventario.services import InventarioExcelImporter

EXCEL_FILE = r'c:\Users\2BAEP\.antigravity-ide\BAEP-Controle-Materiais\INVENTÁRIO - 2ºBAEP - EM - 2025..xlsx'

def main():
    print("=" * 70)
    print("INICIANDO CARGA INICIAL DO INVENTÁRIO FÍSICO E CONTÁBIL — 2º BAEP")
    print("=" * 70)

    if not os.path.exists(EXCEL_FILE):
        print(f"ERRO: Arquivo não encontrado: {EXCEL_FILE}")
        sys.exit(1)

    print(f"Lendo planilha oficial: {EXCEL_FILE}")

    importer = InventarioExcelImporter(
        file_path_or_stream=EXCEL_FILE,
        titulo="Inventário Físico e Contábil de Material Permanente — 1º Semestre / 2026",
        ano=2026,
        semestre=1,
        detentor="Cap PM Felipe Torres Vieira",
        termo_numero="2BAEP - 001/40/2026"
    )

    resultado = importer.process()
    ciclo = resultado['ciclo']

    print("\n" + "=" * 70)
    print("CARGA INICIAL CONCLUÍDA COM SUCESSO!")
    print(f" -> Ciclo de Inventário ID : {ciclo.id}")
    print(f" -> Termo Nº                : {ciclo.termo_numero}")
    print(f" -> Título                  : {ciclo.titulo}")
    print(f" -> Detentor Executivo      : {ciclo.detentor_executivo}")
    print(f" -> Contas Contábeis        : {resultado['total_contas']}")
    print(f" -> Bens Inventariados      : {resultado['total_itens']}")
    print(f" -> Valor Contábil Total    : R$ {resultado['valor_total']:,.2f}")
    print("=" * 70)

if __name__ == '__main__':
    main()
