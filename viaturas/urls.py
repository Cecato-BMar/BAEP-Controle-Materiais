from django.urls import path
from . import views

app_name = 'viaturas'

urlpatterns = [
    path('', views.dashboard_frota, name='dashboard'),

    # CRUD Viaturas
    path('viaturas/', views.lista_viaturas, name='lista_viaturas'),
    path('viaturas/nova/', views.criar_viatura, name='criar_viatura'),
    path('viaturas/<int:pk>/', views.detalhe_viatura, name='detalhe_viatura'),
    path('viaturas/<int:pk>/editar/', views.editar_viatura, name='editar_viatura'),

    # Despacho
    path('despachos/', views.lista_despachos, name='lista_despachos'),
    path('despachos/novo/', views.criar_despacho, name='criar_despacho'),
    path('despachos/<int:pk>/retorno/', views.retorno_despacho, name='retorno_despacho'),

    # Abastecimento
    path('abastecimentos/', views.lista_abastecimentos, name='lista_abastecimentos'),
    path('abastecimentos/novo/', views.criar_abastecimento, name='criar_abastecimento'),

    # Manutenção
    path('manutencoes/', views.lista_manutencoes, name='lista_manutencoes'),
    path('manutencoes/nova/', views.criar_manutencao, name='criar_manutencao'),
    path('manutencoes/<int:pk>/', views.detalhe_manutencao, name='detalhe_manutencao'),
    path('manutencoes/<int:pk>/editar/', views.editar_manutencao, name='editar_manutencao'),
    path('manutencoes/<int:pk>/concluir/', views.concluir_manutencao, name='concluir_manutencao'),

    # Marcas e Modelos (Auxiliares)
    path('marcas/', views.lista_marcas, name='lista_marcas'),
    path('marcas/nova/', views.criar_marca, name='criar_marca'),
    path('marcas/<int:pk>/editar/', views.editar_marca, name='editar_marca'),
    path('modelos/', views.lista_modelos, name='lista_modelos'),
    path('modelos/novo/', views.criar_modelo, name='criar_modelo'),
    path('modelos/<int:pk>/editar/', views.editar_modelo, name='editar_modelo'),

    # Oficinas
    path('oficinas/', views.lista_oficinas, name='lista_oficinas'),
    path('oficinas/nova/', views.criar_oficina, name='criar_oficina'),
    path('oficinas/<int:pk>/editar/', views.editar_oficina, name='editar_oficina'),
]
