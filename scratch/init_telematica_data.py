import os
import django
import random
from django.utils import timezone

import sys

# Adiciona o diretório atual ao sys.path para encontrar o módulo reserva_baep
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

from django.contrib.auth.models import User
from telematica.models import Equipamento, SolicitacaoSuporteTI, CategoriaEquipamento
from policiais.models import Policial

def run():
    print("Iniciando criação de dados de teste para Telemática Unificada...")
    
    users = User.objects.all()
    policiais = Policial.objects.all()
    equipamentos = Equipamento.objects.all()
    
    if not equipamentos.exists():
        print("Erro: Nenhum equipamento cadastrado. Cadastre equipamentos primeiro.")
        return

    admin = User.objects.filter(is_superuser=True).first()
    
    tipos = ['HARDWARE', 'SOFTWARE', 'REDE', 'RADIO', 'CELULAR', 'SISTEMA_BAEP', 'PREVENTIVA', 'CORRETIVA']
    status_list = ['PENDENTE', 'EM_ATENDIMENTO', 'AGUARDANDO_PECA', 'CONCLUIDA']
    prioridades = ['BAIXA', 'MEDIA', 'ALTA', 'URGENTE']
    
    # Criar 10 chamados
    for i in range(10):
        solicitante = random.choice(users)
        equip = random.choice(equipamentos)
        tipo = random.choice(tipos)
        status = random.choice(status_list)
        prio = random.choice(prioridades)
        
        origem = 'USUARIO' if i < 7 else 'INTERNO'
        
        suporte = SolicitacaoSuporteTI.objects.create(
            origem=origem,
            solicitante=solicitante,
            tipo_servico=tipo,
            equipamento=equip,
            descricao_problema=f"Problema de teste #{i+1} - {tipo}",
            prioridade=prio,
            status=status,
            aberto_por=admin
        )
        
        if status in ['EM_ATENDIMENTO', 'CONCLUIDA', 'AGUARDANDO_PECA']:
            suporte.tecnico_atribuido = random.choice(policiais)
            suporte.data_inicio_atendimento = timezone.now() - timezone.timedelta(hours=random.randint(1, 48))
            
            if status == 'CONCLUIDA':
                suporte.solucao_tecnica = "Solução de teste aplicada com sucesso."
                suporte.data_conclusao = timezone.now() - timezone.timedelta(hours=random.randint(0, 24))
                suporte.custo = random.randint(0, 500)
            
            suporte.save()
            
    print(f"Sucesso! 10 chamados de teste criados.")

if __name__ == '__main__':
    run()
