import os
import sys
import django

# Adiciona o diretório raiz ao path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

from telematica.models import ManutencaoTI
from policiais.models import Policial

for m in ManutencaoTI.objects.all():
    name = m.tecnico_responsavel
    # Tenta achar o policial pelo nome
    # "3º SGT PM RENALDO" -> tira o posto
    clean_name = name.split(' PM ')[-1] if ' PM ' in name else name
    
    p = Policial.objects.filter(nome__icontains=clean_name).first()
    if p:
        m.policial_tecnico = p
        m.save(update_fields=['policial_tecnico'])
        print(f"Mapped MNT {m.id}: {name} -> {p.nome}")
    else:
        print(f"No match for MNT {m.id}: {name}")
