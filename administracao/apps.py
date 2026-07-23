from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class AdministracaoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'administracao'
    verbose_name = _('Administração & Consultas')
