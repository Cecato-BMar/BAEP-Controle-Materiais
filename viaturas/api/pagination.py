"""
viaturas/api/pagination.py
Paginação padronizada para todas as APIs do módulo Frota.
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """
    Paginação padrão do projeto.

    Query params:
        page     — número da página (default: 1)
        page_size — itens por página (default: 25, max: 200)
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'count': {'type': 'integer', 'description': 'Total de registros'},
                'next': {'type': 'string', 'nullable': True, 'description': 'URL da próxima página'},
                'previous': {'type': 'string', 'nullable': True, 'description': 'URL da página anterior'},
                'results': schema,
            },
        }
