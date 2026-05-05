from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from .license_core import LicenseManager

class LicenseCheckMiddleware:
    """
    Middleware que intercepta requisições e verifica a validade da licença.
    Bloqueia o acesso a rotas que não sejam da própria licença ou autenticação
    quando a licença estiver expirada ou ausente.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ignorar caminhos estáticos, mídia e admin
        if request.path.startswith(settings.STATIC_URL) or \
           request.path.startswith(settings.MEDIA_URL) or \
           request.path.startswith('/admin/'):
            return self.get_response(request)

        # Ignorar rotas de licenciamento e autenticação para evitar loop de redirecionamento
        allowed_paths = [
            reverse('licenciamento:bloqueado'),
            reverse('licenciamento:ativar'),
            reverse('licenciamento:master'),
            reverse('usuarios:login'),
            reverse('usuarios:logout'),
        ]
        
        if request.path in allowed_paths:
            return self.get_response(request)

        # Verifica o status da licença
        status_info = LicenseManager.get_current_license_status()
        
        # Injeta no request para uso em templates (como mostrar o aviso de Grace Period)
        request.license_info = status_info

        if status_info['status'] in ['NO_LICENSE', 'INVALID', 'EXPIRED']:
            # Se não estiver logado, continua para o login normalmente
            # Mas se tentar acessar sistema, vai pro bloqueio
            if request.user.is_authenticated and request.user.username != 'master':
                return redirect('licenciamento:bloqueado')
            else:
                # Rotas públicas que não precisam de login (caso existam) ou login
                if request.path != '/':
                    pass # Será pego pelo login_required depois
                    
        return self.get_response(request)
