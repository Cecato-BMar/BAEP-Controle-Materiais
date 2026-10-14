from django.urls import path
from . import views

app_name = "uniformes"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('tipos/', views.lista_tipos, name='lista_tipos'),
    path('tipos/novo/', views.criar_tipo, name='criar_tipo'),
    path('tipos/<int:pk>/editar/', views.editar_tipo, name='editar_tipo'),
    path('entregas/', views.lista_entregas, name='lista_entregas'),
    path('entregas/nova/', views.criar_entrega, name='criar_entrega'),
    path('entregas/<int:pk>/', views.detalhe_entrega, name='detalhe_entrega'),
    path('entregas/<int:pk>/editar/', views.editar_entrega, name='editar_entrega'),
    path('entregas/<int:pk>/excluir/', views.excluir_entrega, name='excluir_entrega'),
    path('alertas/', views.lista_alertas, name='lista_alertas'),
    path('alertas/<int:pk>/lido/', views.marcar_alerta_lido, name='marcar_alerta_lido'),
]
