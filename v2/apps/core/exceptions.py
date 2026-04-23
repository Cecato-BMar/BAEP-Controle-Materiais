"""
Custom exceptions for V2.0
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse


class AppException(Exception):
    """Base exception for app."""
    
    def __init__(self, message, code=None):
        self.message = message
        self.code = code or 'error'
        super().__init__(message)


class ValidationError(AppException):
    """Validation error."""
    pass


class PermissionError(AppException):
    """Permission error."""
    pass


class NotFoundError(AppException):
    """Not found error."""
    pass


class ConflictError(AppException):
    """Conflict error."""
    pass


def custom_exception_handler(exc, context):
    """Custom exception handler for DRF."""
    response = exception_handler(exc, context)
    
    if response is not None:
        response.data['status_code'] = response.status_code
    
    return response


def api_error_response(message, code='error', status_code=400, errors=None):
    """Helper para criar resposta de erro JSON."""
    data = {
        'success': False,
        'error': {
            'code': code,
            'message': message,
        }
    }
    if errors:
        data['error']['errors'] = errors
    
    return JsonResponse(data, status=status_code)


def api_success_response(data=None, message=None, status_code=200):
    """Helper para criar resposta de sucesso JSON."""
    response = {'success': True}
    if message:
        response['message'] = message
    if data:
        response['data'] = data
    
    return JsonResponse(response, status=status_code)