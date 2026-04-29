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
    path('equipamentos/<int:pk>/excluir/', views.excluir_equipamento, name='excluir_equipamento'),
    
    # Manutenções
    path('manutencoes/', views.lista_manutencoes, name='lista_manutencoes'),
    path('manutencoes/nova/', views.criar_manutencao, name='criar_manutencao'),
    path('manutencoes/<int:pk>/editar/', views.editar_manutencao, name='editar_manutencao'),
    path('manutencoes/<int:pk>/excluir/', views.excluir_manutencao, name='excluir_manutencao'),
    path('ajax/buscar-equipamentos/', views.buscar_equipamentos_ajax, name='buscar_equipamentos_ajax'),
    
    # Serviços e Redes
    path('servicos/', views.lista_servicos, name='lista_servicos'),
    path('servicos/novo/', views.criar_servico, name='criar_servico'),
    path('servicos/<int:pk>/editar/', views.editar_servico, name='editar_servico'),
    path('servicos/<int:pk>/excluir/', views.excluir_servico, name='excluir_servico'),
    
    # Linhas Móveis
    path('linhas/', views.lista_linhas, name='lista_linhas'),
    path('linhas/nova/', views.criar_linha, name='criar_linha'),
    path('linhas/<int:pk>/editar/', views.editar_linha, name='editar_linha'),
    path('linhas/<int:pk>/excluir/', views.excluir_linha, name='excluir_linha'),

    # Configurações / Auxiliares
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/nova/', views.criar_categoria, name='criar_categoria'),
    path('categorias/<int:pk>/editar/', views.editar_categoria, name='editar_categoria'),
    path('categorias/<int:pk>/excluir/', views.excluir_categoria, name='excluir_categoria'),

    # Fallback para URLs legadas (Redireciona para o novo Dashboard)
    path('mapa/', views.dashboard_telematica, name='mapa_rastreamento'),

    # Solicitações de Suporte (Suporte ao Usuário)
    path('suporte/solicitar/', views.solicitar_suporte, name='solicitar_suporte'),
    path('suporte/meus-pedidos/', views.minhas_solicitacoes_suporte, name='minhas_solicitacoes_suporte'),
    # Suporte Técnico & Gestão Unificada
    path('suporte/gestao/', views.lista_manutencoes, name='gerenciar_suportes'),
    path('suporte/atender/<int:pk>/', views.atender_suporte, name='atender_suporte'),
]
