from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('ciclos/', views.lista_ciclos, name='lista_ciclos'),
    path('ciclos/novo/', views.novo_ciclo, name='novo_ciclo'),
    path('ciclos/<int:ciclo_id>/', views.detalhe_ciclo, name='detalhe_ciclo'),
    path('ciclos/<int:ciclo_id>/pdf/', views.termo_pdf, name='termo_pdf'),
    path('ciclos/<int:ciclo_id>/exportar/', views.exportar_excel, name='exportar_excel'),
    path('ciclos/<int:ciclo_id>/conferir-lote/', views.conferir_lote, name='conferir_lote'),
    path('importar/', views.importar_inventario, name='importar'),
    path('item/<int:item_id>/conferir/', views.conferir_item, name='conferir_item'),
]
