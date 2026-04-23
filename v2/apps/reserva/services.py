"""
Services for reserva app
"""

from typing import Optional
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError


class MaterialService:
    """Service layer for material operations"""
    
    @staticmethod
    @transaction.atomic
    def create_material(data: dict) -> 'Material':
        """Create new material with validation"""
        from apps.reserva.models import Material
        
        material = Material(**data)
        material.full_clean()
        material.save()
        return material
    
    @staticmethod
    @transaction.atomic
    def update_material(material_id: int, data: dict) -> 'Material':
        """Update material"""
        from apps.reserva.models import Material
        
        material = Material.objects.get(pk=material_id)
        for key, value in data.items():
            setattr(material, key, value)
        material.full_clean()
        material.save()
        return material
    
    @staticmethod
    @transaction.atomic
    def delete_material(material_id: int, hard: bool = False):
        """Delete material (soft or hard)"""
        from apps.reserva.models import Material
        
        material = Material.objects.get(pk=material_id)
        if hard:
            material.delete()
        else:
            material.delete(hard=False)
    
    @staticmethod
    def get_available_materials(filters: Optional[dict] = None):
        """Get available materials"""
        from apps.reserva.models import Material
        
        qs = Material.objects.filter(status='DISPONIVEL', is_active=True)
        if filters:
            qs = qs.filter(**filters)
        return qs.select_related('localizacao')
    
    @staticmethod
    def check_availability(material_id: int, quantity: int = 1) -> bool:
        """Check if material is available"""
        from apps.reserva.models import Material
        
        try:
            material = Material.objects.get(pk=material_id)
            return material.quantidade_disponivel >= quantity
        except Material.DoesNotExist:
            return False


class CautelaService:
    """Service layer for cautela operations"""
    
    @staticmethod
    @transaction.atomic
    def create_cautela(material_id: int, policial_id: int, quantidade: int, obs: str = '') -> 'Cautela':
        """Create new cautela (withdrawal)"""
        from apps.reserva.models import Material, Cautela, Policial
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Get objects
        material = Material.objects.get(pk=material_id)
        policial = Policial.objects.get(pk=policial_id)
        
        # Check availability
        if material.quantidade_disponivel < quantidade:
            raise ValidationError(f"Estoque insuficiente. Disponível: {material.quantidade_disponivel}")
        
        # Create cautela
        cautela = Cautela.objects.create(
            material=material,
            policial=policial,
            qtde_retirada=quantidade,
            obs_retirada=obs,
            registro_por=User.objects.get(pk=1)  # TODO: get current user
        )
        
        # Update material
        material.quantidade_disponivel -= quantidade
        material.quantidade_em_uso += quantidade
        material.status = 'EM_USO'
        material.save()
        
        return cautela
    
    @staticmethod
    @transaction.atomic
    def devolve_cautela(cautela_id: int, quantidade: int, obs: str = '') -> 'Cautela':
        """Return cautela"""
        from apps.reserva.models import Cautela
        
        cautela = Cautela.objects.get(pk=cautela_id)
        
        cautela.data_devolucao = timezone.now()
        cautela.qtde_devolvida = quantidade
        cautela.obs_devolucao = obs
        cautela.status = 'DEVOLVIDA'
        cautela.save()
        
        # Update material
        material = cautela.material
        material.quantidade_disponivel += quantidade
        material.quantidade_em_uso -= quantidade
        
        # Check if all returned
        if material.quantidade_em_uso == 0:
            material.status = 'DISPONIVEL'
        
        material.save()
        
        return cautela
    
    @staticmethod
    @transaction.atomic
    def registra_extravio(cautela_id: int) -> 'Cautela':
        """Register material as lost"""
        from apps.reserva.models import Cautela
        
        cautela = Cautela.objects.get(pk=cautela_id)
        
        cautela.status = 'EXTRAVIADA'
        cautela.save()
        
        # Update material
        material = cautela.material
        material.quantidade_em_uso -= cautela.qtde_retirada
        material.status = 'BAIXADO'
        material.save()
        
        return cautela
    
    @staticmethod
    def get_active_cautelas(policial_id: Optional[int] = None):
        """Get active cautelas"""
        from apps.reserva.models import Cautela
        
        qs = Cautela.objects.filter(status='ATIVA')
        if policial_id:
            qs = qs.filter(policial_id=policial_id)
        return qs.select_related('material', 'policial')


class PolicialService:
    """Service layer for policial operations"""
    
    @staticmethod
    def get_all(filters: Optional[dict] = None):
        """Get all active policiais"""
        from apps.reserva.models import Policial
        
        qs = Policial.objects.filter(is_active=True)
        if filters:
            qs = qs.filter(**filters)
        return qs
    
    @staticmethod
    def search(query: str):
        """Search policial by RE or name"""
        from apps.reserva.models import Policial
        
        return Policial.objects.filter(
            models.Q(re__icontains=query) |
            models.Q(nome_guerra__icontains=query) |
            models.Q(nome_completo__icontains=query)
        )