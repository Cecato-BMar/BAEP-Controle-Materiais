from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group as AuthGroup
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class User(AbstractUser):
    """
    Custom User model com campos adicionais para o sistema BAEP.
    """
    TIPO_POSTO_CHOICES = [
        ('soldado', 'Soldado'),
        ('cb', 'Cabo'),
        ('sgt', 'Sargento'),
        ('tenente', 'Tenente'),
        ('capitão', 'Capitão'),
        ('major', 'Major'),
        ('tenente_coronel', 'Tenente-Coronel'),
        ('coronel', 'Coronel'),
    ]
    
    # Pessoal
    re = models.CharField(_('RE'), max_length=20, unique=True, null=True, blank=True)
    nome_guerra = models.CharField(_('Nome de Guerra'), max_length=50, null=True, blank=True)
    tipo_posto = models.CharField(_('Posto'), max_length=20, choices=TIPO_POSTO_CHOICES, blank=True, null=True)
    
    # Contato
    telefone = models.CharField(_('Telefone'), max_length=20, blank=True, null=True)
    telefone_whatsapp = models.BooleanField(_('Tem WhatsApp'), default=False)
    
    # Foto
    foto = models.ImageField(_('Foto'), upload_to='usuarios/fotos/', blank=True, null=True)
    
    # Controle
    ultimo_acesso = models.DateTimeField(_('Último Acesso'), blank=True, null=True)
    ip_ultimo_acesso = models.GenericIPAddressField(_('IP Último Acesso'), blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(_('Ativo'), default=True)
    data_desligamento = models.DateField(_('Data Desligamento'), blank=True, null=True)
    
    class Meta:
        db_table = 'core_user'
        verbose_name = _('Usuário')
        verbose_name_plural = _('Usuários')
        ordering = ['username']
    
    def __str__(self):
        return self.get_full_name() or self.username
    
    def save(self, *args, **kwargs):
        if self.pk and self.is_authenticated:
            self.ultimo_acesso = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def posto_display(self):
        if self.tipo_posto:
            return self.get_tipo_posto_display()
        return None
    
    @property
    def is_operacional(self):
        """Verifica se o usuário tem acesso operacional"""
        return self.groups.filter(name__in=['reserva_armas', 'frota', 'operacional']).exists()
    
    @property
    def is_gestor(self):
        """Verifica se o usuário é gestor"""
        return self.is_superuser or self.groups.filter(name='gestor').exists()
    
    @property
    def can_access_module(self, module: str):
        """Verifica acesso a módulo específico"""
        if self.is_superuser:
            return True
        return self.groups.filter(name=module).exists()


class Grupo(AuthGroup):
    """
    Extended Group model para controle de acesso por módulo.
    """
    MODULO_CHOICES = [
        ('reserva', 'Reserva de Armas'),
        ('frota', 'Frota de Viaturas'),
        ('estoque', 'Estoque de Consumo'),
        ('patrimonio', 'Patrimônio'),
        ('admin', 'Administração'),
        ('relatorio', 'Relatórios'),
    ]
    
    modulo = models.CharField(_('Módulo'), max_length=20, choices=MODULO_CHOICES, blank=True)
    descricao = models.TextField(_('Descrição'), blank=True)
    ativo = models.BooleanField(_('Ativo'), default=True)
    
    class Meta:
        db_table = 'core_group'
        verbose_name = _('Grupo')
        verbose_name_plural = _('Grupos')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class AuditableModel(models.Model):
    """
    Abstract base model com auditoria automática.
    """
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_created', verbose_name=_('Criado por')
    )
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_updated', verbose_name=_('Atualizado por')
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.get_current() if hasattr(get_user_model(), 'objects.get_current') else None
        
        if not self.pk:
            self.created_by = user
        self.updated_by = user
        super().save(*args, **kwargs)


class SoftDeleteManager(models.Manager):
    """Manager que filtra registros deletados."""
    
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)
    
    def all_with_deleted(self):
        return super().get_queryset()
    
    def deleted_only(self):
        return super().get_queryset().filter(deleted_at__isnull=False)


class SoftDeleteModel(models.Model):
    """
    Abstract base model com soft delete.
    """
    deleted_at = models.DateTimeField(_('Excluído em'), blank=True, null=True)
    deleted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_deleted'
    )
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()
    
    class Meta:
        abstract = True
    
    def delete(self, hard=False):
        if hard:
            super().delete()
        else:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.get_current() if hasattr(get_user_model(), 'objects.get_current') else None
            self.deleted_at = timezone.now()
            self.deleted_by = user
            self.save()
    
    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        self.save()
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None


class ActiveManager(models.Manager):
    """Manager que retorna apenas registros ativos."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ActiveModel(models.Model):
    """
    Abstract base model com campo is_active.
    """
    is_active = models.BooleanField(_('Ativo'), default=True)
    
    objects = ActiveManager()
    all_objects = models.Manager()
    
    class Meta:
        abstract = True