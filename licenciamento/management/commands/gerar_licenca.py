from django.core.management.base import BaseCommand
from licenciamento.license_core import LicenseManager

class Command(BaseCommand):
    help = 'Gera um token de licença RSA assinado'

    def add_arguments(self, parser):
        parser.add_argument('--client_id', type=str, required=True, help='ID único do cliente')
        parser.add_argument('--client_name', type=str, required=True, help='Nome legível do cliente')
        parser.add_argument('--days', type=int, default=7, help='Dias de validade da licença')

    def handle(self, *args, **options):
        client_id = options['client_id']
        client_name = options['client_name']
        days = options['days']

        token = LicenseManager.generate_token(client_id, client_name, days)
        
        self.stdout.write(self.style.SUCCESS(f'Token gerado com sucesso para {client_name}:'))
        self.stdout.write(token)
        self.stdout.write(self.style.WARNING('\nEnvie o código acima para o cliente.'))
