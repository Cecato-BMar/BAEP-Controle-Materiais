import os
import sys
import django

# Adiciona o diretório atual ao sys.path para encontrar o projeto
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

from telematica.models import Equipamento, ManutencaoTI

print("--- Verificação de Inconsistências de Status ---")
equips_em_manutencao = Equipamento.objects.filter(status='MANUTENCAO')

for equip in equips_em_manutencao:
    tem_manutencao_aberta = ManutencaoTI.objects.filter(equipamento=equip, concluida=False).exists()
    if not tem_manutencao_aberta:
        print(f"Inconsistência encontrada: Equipamento {equip.id} ({equip}) está como MANUTENCAO mas NÃO tem manutenção aberta.")
        # Corrigindo
        equip.status = 'OPERACIONAL'
        equip.save()
        print(f"  [FIXED] Status alterado para OPERACIONAL.")
    else:
        print(f"Equipamento {equip.id} ({equip}) está corretamente em manutenção.")

print("\n--- Verificação de Equipamentos Operacionais com Manutenção Aberta ---")
equips_operacionais = Equipamento.objects.filter(status='OPERACIONAL')
for equip in equips_operacionais:
    tem_manutencao_aberta = ManutencaoTI.objects.filter(equipamento=equip, concluida=False).exists()
    if tem_manutencao_aberta:
        print(f"Inconsistência encontrada: Equipamento {equip.id} ({equip}) está como OPERACIONAL mas TEM manutenção aberta.")
        # Corrigindo
        equip.status = 'MANUTENCAO'
        equip.save()
        print(f"  [FIXED] Status alterado para MANUTENCAO.")

print("\nVerificação concluída.")
