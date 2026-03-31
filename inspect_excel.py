import pandas as pd
try:
    df = pd.read_excel('Efetivo - MARÇO.xls', engine='xlrd')
    print("Headers:", df.columns.tolist())
    print("Sample:\n", df.head(5))
except Exception as e:
    print("Error:", e)
