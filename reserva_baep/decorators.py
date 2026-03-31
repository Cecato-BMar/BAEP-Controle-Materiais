from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps

def require_module_permission(module_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('usuarios:login')
            
            # Superuser always has access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            # Check if user belongs to the required group
            if request.user.groups.filter(name=module_name).exists():
                return view_func(request, *args, **kwargs)
                
            raise PermissionDenied(f"Acesso negado ao módulo: {module_name}")
        return _wrapped_view
    return decorator
