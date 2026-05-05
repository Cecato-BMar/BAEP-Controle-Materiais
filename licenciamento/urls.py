from django.urls import path
from . import views

app_name = 'licenciamento'

urlpatterns = [
    path('bloqueado/', views.bloqueado, name='bloqueado'),
    path('ativar/', views.ativar_licenca, name='ativar'),
    path('master/', views.panel_master, name='master'),
]
