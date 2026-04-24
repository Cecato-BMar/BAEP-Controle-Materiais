import os
import sys
import django

# Adiciona o diretório atual ao sys.path
sys.path.append(os.getcwd())

# Configuração do ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

from django.contrib.auth.models import Group

def run():
    group_name = 'telematica'
    obj, created = Group.objects.get_or_create(name=group_name)
    if created:
        print(f"Grupo '{group_name}' criado com sucesso.")
    else:
        print(f"Grupo '{group_name}' já existe.")

if __name__ == "__main__":
    run()
