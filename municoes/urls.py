from django.urls import path
from . import views
from . import api

app_name = 'municoes'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('lotes/', views.lista_lotes, name='lista_lotes'),
    path('relatorios/', views.relatorios, name='relatorios'),
    path('lotes/novo/', views.novo_lote, name='novo_lote'),
    path('retirada/nova/', views.nova_retirada, name='nova_retirada'),
    path('retirada/<int:retirada_id>/fechamento/pdf/', views.fechamento_retirada_pdf, name='fechamento_retirada_pdf'),
    path('devolucao/nova/', views.nova_devolucao, name='nova_devolucao'),
    path('devolucao/cpi/', views.devolucao_cpi, name='devolucao_cpi'),
    path('api/lotes/', api.api_lotes, name='api_lotes'),
    path('api/retiradas-pendentes/', api.api_retiradas_pendentes, name='api_retiradas_pendentes'),
    path('api/retirada/<int:retirada_id>/detalhe/', api.api_retirada_detalhe, name='api_retirada_detalhe'),
]

