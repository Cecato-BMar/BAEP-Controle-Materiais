import os
import django
import sys

# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
sys.path.append(os.getcwd())
django.setup()

from viaturas.models import Viatura, Manutencao, DespachoViatura

def fix_viaturas():
    count_m = 0
    count_d = 0
    
    for v in Viatura.objects.all():
        # Verifica se tem manutenção ativa
        if v.manutencoes.filter(status__in=['ABERTA', 'AGUARDANDO_PECA']).exists():
            if v.status != 'MANUTENCAO':
                v.status = 'MANUTENCAO'
                v.save(update_fields=['status'])
                count_m += 1
        # Verifica se tem despacho sem retorno (em uso)
        elif v.despachos.filter(data_retorno__isnull=True).exists():
            if v.status != 'EM_USO':
                v.status = 'EM_USO'
                v.save(update_fields=['status'])
                count_d += 1
        # Se não, e se estiver marcada como MANUTENCAO ou EM_USO erroneamente, volta pra DISPONIVEL
        elif v.status in ['MANUTENCAO', 'EM_USO']:
            v.status = 'DISPONIVEL'
            v.save(update_fields=['status'])
            
    print(f"Viaturas corrigidas para MANUTENCAO: {count_m}")
    print(f"Viaturas corrigidas para EM_USO: {count_d}")

if __name__ == '__main__':
    fix_viaturas()
