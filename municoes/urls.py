from django.urls import path
from . import views
from . import api

app_name = 'municoes'

urlpatterns = [
    path('', views.lista_lotes, name='lista_lotes'),
    path('lotes/', views.lista_lotes, name='lista_lotes'),  # alias para compatibilidade com /municoes/lotes/
    path('lotes/novo/', views.novo_lote, name='novo_lote'),
    path('retirada/nova/', views.nova_retirada, name='nova_retirada'),
    path('devolucao/nova/', views.nova_devolucao, name='nova_devolucao'),
    path('api/lotes/', api.api_lotes, name='api_lotes'),
    path('api/retiradas-pendentes/', api.api_retiradas_pendentes, name='api_retiradas_pendentes'),
]
