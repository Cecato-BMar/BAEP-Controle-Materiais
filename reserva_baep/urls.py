"""
URL configuration for reserva_baep project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin/', admin.site.urls),
    path('materiais/', include('materiais.urls')),
    path('policiais/', include('policiais.urls')),
    path('movimentacoes/', include('movimentacoes.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('relatorios/', include('relatorios.urls')),
    path('estoque/', include('estoque.urls')),
    path('frota/', include('viaturas.urls', namespace='viaturas')),
    path('ajuda/', views.ajuda, name='ajuda'),
    path('termos/', views.termos, name='termos'),
    path('privacidade/', views.privacidade, name='privacidade'),
    path('sobre/', views.sobre, name='sobre'),
    path('manutencao/', views.manutencao, name='manutencao'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Configuração de handlers para páginas de erro
handler404 = views.handler404
handler500 = views.handler500
handler403 = views.handler403
handler400 = views.handler400
