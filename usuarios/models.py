from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from policiais.models import Policial

class Perfil(models.Model):
    NIVEL_ACESSO_CHOICES = [
        ('ADMIN', 'Administrador'),
        ('GESTOR', 'Gestor'),
        ('OPERADOR', 'Operador'),
        ('VISUALIZADOR', 'Visualizador'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil', verbose_name=_('Usuário'))
    policial = models.OneToOneField(Policial, on_delete=models.SET_NULL, null=True, blank=True, related_name='perfil_usuario', verbose_name=_('Policial'))
    nivel_acesso = models.CharField(_('Nível de Acesso'), max_length=20, choices=NIVEL_ACESSO_CHOICES, default='VISUALIZADOR')
    telefone = models.CharField(_('Telefone'), max_length=20, blank=True, null=True)
    data_ultimo_acesso = models.DateTimeField(_('Último Acesso'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('Perfil')
        verbose_name_plural = _('Perfis')
    
    def __str__(self):
        return f"{self.user.username} - {self.get_nivel_acesso_display()}"

@receiver(post_save, sender=User)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    """Cria automaticamente um perfil para cada novo usuário criado"""
    if created:
        Perfil.objects.create(user=instance)

@receiver(post_save, sender=User)
def salvar_perfil_usuario(sender, instance, **kwargs):
    """Salva o perfil do usuário sempre que o usuário for salvo"""
    instance.perfil.save()
