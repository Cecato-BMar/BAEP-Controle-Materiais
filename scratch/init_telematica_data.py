import os
import sys
import django

# Adiciona o diretório atual ao sys.path para encontrar o projeto
sys.path.append(os.getcwd())

# Configuração do ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

from telematica.models import CategoriaEquipamento

def run():
    categorias = [
        {'nome': 'Computador / Desktop', 'icone': 'fas fa-desktop', 'descricao': 'Estações de trabalho fixas.'},
        {'nome': 'Notebook / Laptop', 'icone': 'fas fa-laptop', 'descricao': 'Equipamentos portáteis.'},
        {'nome': 'Rádio HT (Portátil)', 'icone': 'fas fa-walkie-talkie', 'descricao': 'Rádios comunicadores portáteis.'},
        {'nome': 'Rádio Móvel (Vtr)', 'icone': 'fas fa-broadcast-tower', 'descricao': 'Rádios instalados em viaturas.'},
        {'nome': 'TPD / Tablet', 'icone': 'fas fa-tablet-alt', 'descricao': 'Terminais Portáteis de Dados e Tablets.'},
        {'nome': 'Smartphone / Celular', 'icone': 'fas fa-mobile-alt', 'descricao': 'Aparelhos celulares corporativos.'},
        {'nome': 'Impressora / Scanner', 'icone': 'fas fa-print', 'descricao': 'Equipamentos de impressão e digitalização.'},
        {'nome': 'Ativo de Rede (Switch/AP)', 'icone': 'fas fa-network-wired', 'descricao': 'Switches, Access Points e Roteadores.'},
        {'nome': 'Monitor', 'icone': 'fas fa-tv', 'descricao': 'Monitores de vídeo.'},
    ]

    print("Iniciando cadastro de categorias padrão de Telemática...")
    for cat_data in categorias:
        obj, created = CategoriaEquipamento.objects.get_or_create(
            nome=cat_data['nome'],
            defaults={
                'icone': cat_data['icone'],
                'descricao': cat_data['descricao']
            }
        )
        if created:
            print(f"  [+] Categoria '{obj.nome}' criada.")
        else:
            print(f"  [.] Categoria '{obj.nome}' já existe.")
    
    print("\nProcesso concluído com sucesso!")

if __name__ == "__main__":
    run()
