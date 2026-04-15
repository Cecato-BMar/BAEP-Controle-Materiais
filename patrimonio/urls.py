from django.urls import path
from . import views

app_name = 'patrimonio'

urlpatterns = [
    path('', views.dashboard_patrimonio, name='dashboard'),
    path('itens/', views.lista_itens, name='lista_itens'),
    path('itens/novo/', views.novo_item, name='novo_item'),
    path('itens/<int:pk>/', views.detalhe_item, name='detalhe_item'),
    path('itens/<int:pk>/editar/', views.editar_item, name='editar_item'),
    path('movimentacao/', views.registrar_movimentacao, name='registrar_movimentacao'),
    path('catalogo/', views.lista_bens, name='lista_bens'),
    path('catalogo/novo/', views.novo_bem, name='novo_bem'),
    path('catalogo/importar/', views.importar_bens, name='importar_bens'),
    path('catalogo/<int:pk>/editar/', views.editar_bem, name='editar_bem'),
]
