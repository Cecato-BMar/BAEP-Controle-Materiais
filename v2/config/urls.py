"""
URL configuration for BAEP V2.0
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

from config import views

urlpatterns = [
    # Root
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Core apps
    path('conta/', include('apps.core.urls', namespace='core')),
    path('auth/', include('apps.core.auth_urls', namespace='auth')),
    
    # Apps modules
    path('reserva/', include('apps.reserva.urls', namespace='reserva')),
    path('frota/', include('apps.frota.urls', namespace='frota')),
    path('estoque/', include('apps.estoque.urls', namespace='estoque')),
    path('patrimonio/', include('apps.patrimonio.urls', namespace='patrimonio')),
    
    # API
    path('api/', include('api.urls')),
    path('api/schema/', SchemaView.as_view(), name='openapi-schema'),
    
    # Pages
    path('ajuda/', TemplateView.as_view(template_name='pages/ajuda.html'), name='ajuda'),
    path('sobre/', TemplateView.as_view(template_name='pages/sobre.html'), name='sobre'),
]

# Media files in debug
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Error handlers
handler404 = 'config.views.handler404'
handler500 = 'config.views.handler500'
handler403 = 'config.views.handler403'
handler400 = 'config.views.handler400'