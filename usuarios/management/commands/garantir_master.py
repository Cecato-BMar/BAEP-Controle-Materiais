import os
import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from licenciamento.license_core import LicenseManager
from licenciamento.models import LicenseRecord


class Command(BaseCommand):
    help = "Garante que o usuário master e a licença estejam sempre ativos no boot do sistema"

    def handle(self, *args, **options):
        admin_user = os.getenv('ADMIN_USERNAME', 'master')
        admin_pass = os.getenv('ADMIN_PASSWORD', 'C3c4t0118*')
        admin_email = os.getenv('ADMIN_EMAIL', 'master@baep.com.br')

        # 1. Garante a existência do usuário master
        user, created = User.objects.get_or_create(username=admin_user)
        if created:
            user.set_password(admin_pass)
            user.email = admin_email
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superusuário '{admin_user}' criado com sucesso."))
        else:
            changed = False
            if not user.is_superuser or not user.is_staff:
                user.is_superuser = True
                user.is_staff = True
                changed = True
            # Se for solicitado reset explícito ou para garantir acesso contínuo
            if os.getenv('RESET_MASTER_PASSWORD', 'true').lower() == 'true':
                user.set_password(admin_pass)
                changed = True
            if changed:
                user.save()
            self.stdout.write(self.style.SUCCESS(f"Superusuário '{admin_user}' verificado e pronto para login."))

        # 2. Garante que exista uma licença ativa para o 2º BAEP
        try:
            status_info = LicenseManager.get_current_license_status()
            if status_info['status'] in ['NO_LICENSE', 'INVALID', 'EXPIRED']:
                token = LicenseManager.generate_token('baep-cliente', '2º Batalhão de Ações Especiais', 365)
                is_valid, payload = LicenseManager.verify_token(token)
                if is_valid or payload:
                    LicenseRecord.objects.all().update(is_active=False)
                    expires_at = datetime.datetime.fromtimestamp(payload['exp'], tz=datetime.timezone.utc)
                    issued_at = datetime.datetime.fromtimestamp(payload['iat'], tz=datetime.timezone.utc)
                    LicenseRecord.objects.create(
                        client_id=payload.get('client_id'),
                        client_name=payload.get('client_name'),
                        token_base64=token,
                        issued_at=issued_at,
                        expires_at=expires_at,
                        is_active=True
                    )
                    self.stdout.write(self.style.SUCCESS("Licença de 1 ano para o 2º BAEP gerada e ativada automaticamente."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Aviso ao inicializar licença: {e}"))
