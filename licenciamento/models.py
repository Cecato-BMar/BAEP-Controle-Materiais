from django.db import models

class LicenseRecord(models.Model):
    client_id = models.CharField(max_length=100, unique=True, verbose_name="ID do Cliente")
    client_name = models.CharField(max_length=200, verbose_name="Nome do Cliente")
    token_base64 = models.TextField(verbose_name="Token Criptográfico")
    issued_at = models.DateTimeField(verbose_name="Data de Emissão")
    expires_at = models.DateTimeField(verbose_name="Data de Expiração")
    last_verified = models.DateTimeField(auto_now=True, verbose_name="Última Verificação")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    
    class Meta:
        verbose_name = "Registro de Licença"
        verbose_name_plural = "Registros de Licença"
        
    def __str__(self):
        return f"Licença - {self.client_name} (Expira: {self.expires_at.strftime('%d/%m/%Y')})"
