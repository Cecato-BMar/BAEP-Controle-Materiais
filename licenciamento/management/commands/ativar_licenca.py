from django.core.management.base import BaseCommand
from licenciamento.license_core import LicenseManager
from licenciamento.models import LicenseRecord
import datetime
from django.utils import timezone

class Command(BaseCommand):
    help = 'Ativa uma licença no sistema usando um token base64'

    def add_arguments(self, parser):
        parser.add_argument('token', type=str, help='O token de licença fornecido pelo desenvolvedor')

    def handle(self, *args, **options):
        token = options['token']
        
        is_valid, payload = LicenseManager.verify_token(token)
        
        if not payload:
            self.stdout.write(self.style.ERROR('Token inválido ou corrompido.'))
            return

        # Desativa licenças anteriores
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

        if is_valid:
            self.stdout.write(self.style.SUCCESS(f'Licença ativada com sucesso para: {payload.get("client_name")}'))
            self.stdout.write(f'Válida até: {expires_at.strftime("%d/%m/%Y %H:%M:%S")}')
        else:
            self.stdout.write(self.style.WARNING(f'Licença ativada, mas encontra-se expirada/em período de tolerância.'))
