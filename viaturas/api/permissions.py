"""
viaturas/api/permissions.py
Permissões customizadas baseadas em grupo de módulo (compatível com decorator existente).
"""
from rest_framework.permissions import BasePermission


class FrotaModulePermission(BasePermission):
    """
    Permite acesso somente a usuários autenticados que pertençam
    ao grupo 'frota' ou que sejam superusuários.

    Replicação da lógica de `require_module_permission('frota')` para DRF.

    - GET / HEAD / OPTIONS → qualquer usuário autenticado do grupo
    - POST / PUT / PATCH / DELETE → qualquer usuário autenticado do grupo
      (a validação fina de negócio está nos services)
    """
    message = 'Acesso negado ao módulo Frota. Solicite inclusão no grupo "frota".'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name='frota').exists()


class IsFrotaAdmin(BasePermission):
    """
    Permissão restrita: apenas superusuários ou membros do grupo 'frota_admin'.

    Usada em endpoints sensíveis (ex: exclusão em massa, aprovação de baixa).
    """
    message = 'Operação restrita a administradores da frota.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name__in=['frota_admin', 'frota']).exists()
