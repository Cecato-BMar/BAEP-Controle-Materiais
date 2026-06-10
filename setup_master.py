"""Script de setup do usuario master para o container de teste."""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

from django.contrib.auth.models import User, Group

u, created = User.objects.get_or_create(
    username='master',
    defaults={'email': 'master@2baep.pol.br', 'is_staff': True, 'is_superuser': True}
)
u.set_password('master2024')
u.save()
g, _ = Group.objects.get_or_create(name='material_belico')
u.groups.add(g)
print('master OK' if created else 'master ja existia, senha atualizada OK')
