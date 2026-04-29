import os
import django
import sys

# Adiciona o diretório atual ao sys.path para encontrar o módulo reserva_baep
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
sys.path.append(os.getcwd())
django.setup()

from telematica.models import SolicitacaoSuporteTI

def run():
    print("Limpando dados de teste de Telemática...")
    
    count, _ = SolicitacaoSuporteTI.objects.all().delete()
    
    print(f"Sucesso! {count} chamados removidos.")
    print("O sistema está pronto para produção.")

if __name__ == '__main__':
    run()
