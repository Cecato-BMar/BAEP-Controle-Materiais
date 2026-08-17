from django.urls import path
from . import views

app_name = 'tutorial'

urlpatterns = [
    path('', views.index, name='index'),
    path('<slug:slug>/', views.detalhe_modulo, name='modulo'),
]