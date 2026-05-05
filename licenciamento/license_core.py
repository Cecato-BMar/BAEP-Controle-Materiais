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

# MANTENHA A CHAVE PRIVADA APENAS COM O DESENVOLVEDOR EM PRODUÇÃO!
# Incluída aqui para fins de demonstração e geração de novos tokens pelo próprio sistema.
PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCSLGQU22GIY61+
0jt7qO80gRrBhZwIew9g2X5mANaCcOvIxAnqpdaM1+2slisOVZlWDA3Xa01CxP3p
S0h4FulnCJFsbl29oWoH291bhWVYYrAbPi2MabPJgNvb/9J27fFzvxpIDAYcqvDW
HhGBhxSDaZqUiXmwl0Us0ltsSAIqv0ysyCTigWcft1jzgd6gZ/1enbu8B19hZ5Be
FX+ZJHIo171v/P/pLYr9fk9yT09djeY1iTvaRV9wUBKCBXvhaGj7ih3SixMtrf6D
WNnVLKZhfVLq2B+kK6zCTC9UfLJHnIMTReLUVMBULwWOXO1gsXKlAT5QrwLKaPtS
+8Ls/GlHAgMBAAECggEAAuwUmMl6otg3SjSYECn5lOegf3jqfHg//57UJOQ5uu7Y
pTFXb2j0UpQogg2Ye8ILUt830Z7UCGnZbPYJKK7F6L47m1rTe0HZqvbixHx0tmEh
Wydm5V/hl72Akl6EDcZGUEWO7XIhbHugXUTJnc4eWLLeQ7+XKV1vemy+0M8vDT1b
uzzt1syzGAyJKeQtaepom/m41C3I+lFYYARyj3OhcHqqx5u2tSn6k+IN+w7OldyI
kTEyp4gXmTCvfh6+Qdm6o38y6lUAfrwb46qAnfBnlJEeclDextb67ntKVmac7jUi
A679Op/cV6cfxRxfVhuLRr7Gl0A7HNXmMp+G77vjcQKBgQDExdejvwNVlwGifpHH
rrapcL773x0dZEqLCqKghnN5dUnBlay0K3zpvxQToj07q4FSZxCT5Qx3MFM0qsQ3
Gmn7nnd5GZJuPZmo2mPSKy+KAPGmbzAQUjwwVVOfYJMoh36G2Vr4eX97f97BOmrO
zpnUKouQn6hsOsP2w+x8+a2u9wKBgQC+K6eTEf8+0S0OuXRxVCQuwvs3uX5m1UmQ
1RAVgp2Etoel4+v/Gttfx+olc11XVZqkuq9EMkzYPM5Tq2ARPWfo+M1DR4+F443H
6Y5swoGuu8nniaFl+CJErjCDYKjD2bOU9pp2XZ3AJ0w+a4+NjxZGIshD0JWUK7r1
7rGzMLp0MQKBgBait6qzh3uqElsR+k0hMQwO1zl8Mgo2hki2YXzb2p7HOkPVpvdW
5ViyTWnwyOB7WzYSexq4R5XSbk/psQaxuC1kzlOU+H5MAcglz0PXCfHzJ9lAgyPt
gdUBi8wSvPr1kz2J9WgN+fdH/2T1BmJh69o3RrTNWP+SRwa1BRhfVHaDAoGAdnOQ
lF3QY9s8uoAvlGt5ghr3CXWj0v+lK+5ab1uFK+XZxi2akLK01AscwCkEieKLSXHy
u4KtNL9jMOB9HR/nekiG6hJHxni/ljbW/M2Go0Ta9TpX6sDM74SkOSDa3erbHb0g
5vtWyBpyNisfJmhq0lLV9M+Wa811TbxYuSlv6fECgYAN2ea+anjIqj+2WfstnMgv
j6WfB4hRe55BJReizqW+5/5IK0ZY2PP8HvNrfcKWizQfteCMHL1AzUfcAo9+t1Rr
yKeXbSBY/xs6F3c6uVmv2PIoat+T+DR+YtSCvlgFluMMQ8GDEgAoGkOP0ccBoGXG
K8FCUZRg2xj+MI8HRFHU/w==
-----END PRIVATE KEY-----"""

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
        
        token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
        return token
