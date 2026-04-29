import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

from solicitacoes.models import Solicitacao
print(f"Model Solicitacao found: {Solicitacao}")
