from django.urls import path
from . import views
from . import api

app_name = 'movimentacoes'

urlpatterns = [
    path('', views.lista_movimentacoes, name='lista_movimentacoes'),
    path('<int:pk>/', views.detalhe_movimentacao, name='detalhe_movimentacao'),
    path('retirada/nova/', views.nova_retirada, name='nova_retirada'),
    path('devolucao/nova/', views.nova_devolucao, name='nova_devolucao'),
    
    # APIs existentes
    path('api/retiradas-pendentes/', views.buscar_retiradas_pendentes, name='buscar_retiradas_pendentes'),
    path('api/materiais-disponiveis/', views.buscar_materiais_disponiveis, name='buscar_materiais_disponiveis'),
    
    # Novas APIs
    path('api/movimentacoes/retiradas/<int:retirada_id>/', api.api_retirada_detalhe, name='api_retirada_detalhe'),
    path('api/movimentacoes/retiradas-pendentes/', api.api_retiradas_pendentes, name='api_retiradas_pendentes'),
]