import xlrd

try:
    workbook = xlrd.open_workbook('Efetivo - MARÇO.xls')
    sheet = workbook.sheet_by_index(0)
    
    print(f"Planilha: {sheet.name}")
    print(f"Linhas: {sheet.nrows}")
    
    # Pegar as primeiras 5 linhas para ver cabeçalhos e dados
    for i in range(min(10, sheet.nrows)):
        print(f"Linha {i}: {sheet.row_values(i)}")

except Exception as e:
    print("Erro ao ler com xlrd:", e)
