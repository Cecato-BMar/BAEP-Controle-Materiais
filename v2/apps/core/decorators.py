"""
Custom decorators for V2.0
"""

from functools import wraps
from django.core.cache import cache
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse


def require_module_permission(module_name):
    """
    Decorator para exigir permissão de módulo.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Faça login para continuar.')
                return redirect('login')
            
            if not request.user.can_access_module(module_name):
                messages.error(request, 'Você não tem permissão para acessar este módulo.')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_superuser(view_func):
    """Decorator para exigir superusuário."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Autenticação requerida'}, status=401)
        if not request.user.is_superuser:
            return JsonResponse({'error': 'Permissão negada'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def require_ajax(view_func):
    """Decorator para exigir requisição AJAX."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Requisição inválida'}, status=400)
        return view_func(request, *args, **kwargs)
    return wrapper


def rate_limit(key_prefix, limit=10, duration=60):
    """
    Decorator para rate limiting em views.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            cache_key = f"rate_limit:{request.user.id}:{key_prefix}" if request.user.is_authenticated else f"rate_limit:ip:{request.META.get('REMOTE_ADDR')}:{key_prefix}"
            
            count = cache.get(cache_key, 0)
            if count >= limit:
                return JsonResponse({'error': 'Limite de requisições excedido'}, status=429)
            
            cache.set(cache_key, count + 1, duration)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """Decorator para exigir admin ou gestor."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Autenticação requerida'}, status=401)
        if not request.user.is_gestor:
            return JsonResponse({'error': 'Permissão negada'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper