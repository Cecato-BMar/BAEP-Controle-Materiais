from django.urls import path
from . import views
from . import api

app_name = 'materiais'

urlpatterns = [
    path('', views.lista_materiais, name='lista_materiais'),
    path('<int:material_id>/', views.detalhe_material, name='detalhe_material'),
    path('novo/', views.novo_material, name='novo_material'),
    path('importar-xml/', views.importar_armas_xml, name='importar_armas_xml'),
    path('<int:material_id>/editar/', views.editar_material, name='editar_material'),
    path('lotes/', views.lista_lotes, name='lista_lotes'),
    path('lotes/novo/', views.novo_lote, name='novo_lote'),
    path('lotes/<int:lote_id>/editar/', views.editar_lote, name='editar_lote'),
    path('lotes/<int:lote_id>/excluir/', views.excluir_lote, name='excluir_lote'),
    
    # APIs
    path('api/materiais/', api.api_materiais, name='api_materiais'),
    path('api/materiais/<int:material_id>/', api.api_material_detalhe, name='api_material_detalhe'),
]