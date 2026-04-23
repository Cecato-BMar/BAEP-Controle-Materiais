from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from rest_framework import authentication, exceptions


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT Authentication para API REST.
    """
    
    keyword = 'Bearer'
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return None
        
        auth_parts = auth_header.split(' ')
        
        if len(auth_parts) != 2 or auth_parts[0] != self.keyword:
            return None
        
        token = auth_parts[1]
        
        return self.authenticate_token(token)
    
    def authenticate_token(self, token):
        from apps.core.models import Token
        
        try:
            token_obj = Token.objects.get(key=token, is_active=True)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed('Token inválido ou expirado')
        
        if token_obj.is_expired():
            raise exceptions.AuthenticationFailed('Token expirado')
        
        if not token_obj.user.is_active:
            raise exceptions.AuthenticationFailed('Usuário inativo')
        
        return (token_obj.user, token_obj)
    
    def authenticate_header(self, request):
        return self.keyword


class Token(models.Model):
    """
    Token de acesso JWT.
    """
    from apps.core.models import User
    
    key = models.CharField(_('Chave'), max_length=64, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
    description = models.CharField(_('Descrição'), max_length=255, blank=True)
    expires_at = models.DateTimeField(_('Expira em'), blank=True, null=True)
    is_active = models.BooleanField(_('Ativo'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(_('Último uso'), blank=True, null=True)
    
    class Meta:
        db_table = 'core_token'
        verbose_name = _('Token')
        verbose_name_plural = _('Tokens')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.description or self.key[:8]}"
    
    def is_expired(self):
        from django.utils import timezone
        if self.expires_at:
            return self.expires_at < timezone.now()
        return False
    
    def save(self, *args, **kwargs):
        if not self.key:
            import secrets
            self.key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)