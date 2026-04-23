import os
import sys
import django
import io

# Adiciona o diretório atual ao sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

from relatorios.providers import (
    SituacaoAtualProvider, 
    MateriaisProvider, 
    MovimentacoesProvider, 
    FrotaGeralProvider, 
    FrotaAbastecimentoProvider,
    FrotaManutencaoProvider,
    PatrimonioProvider
)
from relatorios.utils import PDFReportGenerator

def test_providers():
    buffer = io.BytesIO()
    gen = PDFReportGenerator(buffer=buffer, title="Teste de Provedores")
    
    providers = [
        ('Situação Atual', SituacaoAtualProvider),
        ('Materiais', MateriaisProvider),
        ('Movimentações', MovimentacoesProvider),
        ('Frota Geral', FrotaGeralProvider),
        ('Frota Abastecimento', FrotaAbastecimentoProvider),
        ('Frota Manutenção', FrotaManutencaoProvider),
        ('Patrimônio', PatrimonioProvider)
    ]

    print(f"{'Provedor':<20} | {'Status':<10} | {'Resultado'}")
    print("-" * 50)

    for name, provider_class in providers:
        try:
            provider = provider_class(gen)
            elements = provider.get_elements()
            
            if elements and len(elements) > 0:
                status = "OK"
                result = f"{len(elements)} elementos gerados"
            else:
                status = "AVISO"
                result = "Nenhum elemento gerado"
            
            print(f"{name:<20} | {status:<10} | {result}")
            
        except Exception as e:
            print(f"{name:<20} | ERRO       | {str(e)}")

if __name__ == "__main__":
    test_providers()
