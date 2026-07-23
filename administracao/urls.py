from django.urls import path
from . import views

app_name = 'administracao'

urlpatterns = [
    path('', views.painel_administracao, name='dashboard'),
    path('consulta/', views.consulta_dinamica, name='consulta_dinamica'),
    path('consulta/exportar-excel/', views.exportar_excel, name='exportar_excel'),
    path('consulta/imprimir/', views.imprimir_relatorio, name='imprimir_relatorio'),
]
