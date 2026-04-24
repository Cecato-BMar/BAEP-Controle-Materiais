from django.urls import path
from . import views

app_name = 'telematica'

urlpatterns = [
    path('', views.dashboard_telematica, name='dashboard'),
    
    # Equipamentos
    path('equipamentos/', views.lista_equipamentos, name='lista_equipamentos'),
    path('equipamentos/novo/', views.criar_equipamento, name='criar_equipamento'),
    path('equipamentos/<int:pk>/', views.detalhe_equipamento, name='detalhe_equipamento'),
    path('equipamentos/<int:pk>/editar/', views.editar_equipamento, name='editar_equipamento'),
    
    # Manutenções
    path('manutencoes/', views.lista_manutencoes, name='lista_manutencoes'),
    path('manutencoes/nova/', views.criar_manutencao, name='criar_manutencao'),
    
    # Serviços e Redes
    path('servicos/', views.lista_servicos, name='lista_servicos'),
    path('servicos/novo/', views.criar_servico, name='criar_servico'),
    path('servicos/<int:pk>/editar/', views.editar_servico, name='editar_servico'),
    
    # Linhas Móveis
    path('linhas/', views.lista_linhas, name='lista_linhas'),
    path('linhas/nova/', views.criar_linha, name='criar_linha'),
    path('linhas/<int:pk>/editar/', views.editar_linha, name='editar_linha'),

    # Configurações / Auxiliares
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/nova/', views.criar_categoria, name='criar_categoria'),

    # Fallback para URLs legadas (Redireciona para o novo Dashboard)
    path('mapa/', views.dashboard_telematica, name='mapa_rastreamento'),
]
