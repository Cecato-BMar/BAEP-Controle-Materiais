from django.urls import path
from . import views
from . import api

app_name = 'policiais'

urlpatterns = [
    path('', views.lista_policiais, name='lista_policiais'),
    path('<int:policial_id>/', views.detalhe_policial, name='detalhe_policial'),
    path('novo/', views.novo_policial, name='novo_policial'),
    path('<int:policial_id>/editar/', views.editar_policial, name='editar_policial'),
    path('importar/', views.importar_policiais_excel, name='importar_policiais_excel'),

    # APIs
    path('api/policiais/', api.api_policiais, name='api_policiais'),
    path('api/policiais/<int:policial_id>/', api.api_policial_detalhe, name='api_policial_detalhe'),
]