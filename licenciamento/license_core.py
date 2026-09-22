import os
import jwt
import datetime
from django.utils import timezone
from .models import LicenseRecord

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAkixkFNthiGOtftI7e6jv
NIEawYWcCHsPYNl+ZgDWgnDryMQJ6qXWjNftrJYrDlWZVgwN12tNQsT96UtIeBbp
ZwiRbG5dvaFqB9vdW4VlWGKwGz4tjGmzyYDb2//Sdu3xc78aSAwGHKrw1h4RgYcU
g2malIl5sJdFLNJbbEgCKr9MrMgk4oFnH7dY84HeoGf9Xp27vAdfYWeQXhV/mSRy
KNe9b/z/6S2K/X5Pck9PXY3mNYk72kVfcFASggV74Who+4od0osTLa3+g1jZ1Sym
YX1S6tgfpCuswkwvVHyyR5yDE0Xi1FTAVC8FjlztYLFypQE+UK8Cymj7UvvC7Pxp
RwIDAQAB
-----END PUBLIC KEY-----"""

# A chave privada NÃO deve ser versionada no código.
# Em ambientes que precisam gerar tokens, forneça via variável de ambiente LICENSE_PRIVATE_KEY.
PRIVATE_KEY = os.getenv('LICENSE_PRIVATE_KEY', '')

class LicenseManager:
    @staticmethod
    def verify_token(token):
        try:
            payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
            return True, payload
        except jwt.ExpiredSignatureError:
            # Pegamos o payload mesmo expirado para verificar os dias de tolerância
            payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"], options={"verify_exp": False})
            return False, payload
        except jwt.InvalidTokenError:
            return False, None

    @staticmethod
    def get_current_license_status():
        record = LicenseRecord.objects.filter(is_active=True).order_by('-issued_at').first()
        if not record:
            return {
                'status': 'NO_LICENSE',
                'message': 'Nenhuma licença instalada.',
                'grace_period': 0
            }

        record.last_verified = timezone.now()
        record.save()

        is_valid, payload = LicenseManager.verify_token(record.token_base64)

        if not payload:
            return {
                'status': 'INVALID',
                'message': 'Token de licença corrompido ou forjado.',
                'grace_period': 0
            }

        expires_at = datetime.datetime.fromtimestamp(payload['exp'], tz=datetime.timezone.utc)
        now = timezone.now()

        if now <= expires_at:
            delta = expires_at - now
            return {
                'status': 'VALID',
                'message': 'Licença ativa e válida.',
                'grace_period': 0,
                'client': payload.get('client_name'),
                'expires_at': expires_at,
                'days_remaining': delta.days
            }

        # Verifica período de tolerância (grace period de 3 dias)
        delta = now - expires_at
        if delta.days <= 3:
            return {
                'status': 'GRACE_PERIOD',
                'message': f'Sua licença expirou há {delta.days} dia(s). Renove imediatamente para evitar o bloqueio.',
                'grace_period': 3 - delta.days,
                'client': payload.get('client_name'),
                'expires_at': expires_at
            }
        
        return {
            'status': 'EXPIRED',
            'message': 'Licença expirada. O sistema foi bloqueado.',
            'grace_period': 0,
            'client': payload.get('client_name')
        }

    @staticmethod
    def generate_token(client_id, client_name, days_valid=7):
        now = timezone.now()
        expires_at = now + datetime.timedelta(days=days_valid)
        
        payload = {
            "client_id": client_id,
            "client_name": client_name,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "modules": ["materiais", "frota", "estoque", "patrimonio", "telematica"],
            "version": "2.2"
        }
        
        if not PRIVATE_KEY:
            raise ValueError(
                "Chave privada de licenciamento não configurada (LICENSE_PRIVATE_KEY). "
                "A emissão de tokens só é permitida em ambiente administrativo seguro."
            )
        token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
        return token
