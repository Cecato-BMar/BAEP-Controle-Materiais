def user_groups(request):
    """
    Injeta a lista de nomes dos grupos do usuário logado no contexto de templates.
    Permite checagens simplificadas no menu lateral e nas páginas:
    ex: {% if 'materiais' in user_groups or user.is_superuser %}
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        return {
            'user_groups': list(request.user.groups.values_list('name', flat=True))
        }
    return {
        'user_groups': []
    }
