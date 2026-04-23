"""
Custom middleware for V2.0
"""

import logging
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class AuditMiddleware(MiddlewareMixin):
    """Middleware for audit logging."""
    
    def process_request(self, request):
        request._start_time = time.time()
        if request.user.is_authenticated:
            logger.debug(f"User {request.user} accessing {request.path}")
        return None
    
    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            response['X-Response-Time'] = f"{duration:.3f}s"
        return response


class RequestLogMiddleware(MiddlewareMixin):
    """Middleware for structured request logging."""
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        request._view_name = f"{view_func.__module__}.{view_func.__name__}"
        return None
    
    def process_response(self, request, response):
        if hasattr(request, '_view_name'):
            logger.info(
                f"{request.method} {request.path} -> {response.status_code}",
                extra={
                    'view': getattr(request, '_view_name', 'unknown'),
                    'user': str(request.user) if request.user.is_authenticated else 'anonymous',
                    'duration': getattr(request, '_start_time', 0),
                }
            )
        return response


class CORSMiddleware(MiddlewareMixin):
    """Custom CORS middleware with better defaults."""
    
    def process_response(self, request, response):
        if request.method == 'OPTIONS':
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
        return response