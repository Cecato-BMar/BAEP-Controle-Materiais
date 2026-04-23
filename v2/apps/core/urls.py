"""
URLs for core app
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/editar/', views.perfil_editar, name='perfil_editar'),
    path('alterar-senha/', views.alterar_senha, name='alterar_senha'),
]