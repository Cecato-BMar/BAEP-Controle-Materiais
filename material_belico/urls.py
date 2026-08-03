"""URLs do módulo Material Bélico."""
from django.urls import path
from . import views

app_name = 'material_belico'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('importar-excel/', views.importar_excel, name='importar_excel'),
    path('relatorio-detalhado/', views.exportar_relatorio_detalhado, name='exportar_relatorio_detalhado'),

    # Fuzis
    path('fuzis/', views.fuzil_list, name='fuzil_list'),
    path('fuzis/novo/', views.fuzil_create, name='fuzil_create'),
    path('fuzis/<int:pk>/editar/', views.fuzil_edit, name='fuzil_edit'),
    path('fuzis/<int:pk>/excluir/', views.fuzil_delete, name='fuzil_delete'),

    # Espingardas Cal.12
    path('espingardas/', views.espingarda_list, name='espingarda_list'),
    path('espingardas/nova/', views.espingarda_create, name='espingarda_create'),
    path('espingardas/<int:pk>/editar/', views.espingarda_edit, name='espingarda_edit'),
    path('espingardas/<int:pk>/excluir/', views.espingarda_delete, name='espingarda_delete'),

    # Pistolas Glock
    path('pistolas-glock/', views.pistola_glock_list, name='pistola_glock_list'),
    path('pistolas-glock/nova/', views.pistola_glock_create, name='pistola_glock_create'),
    path('pistolas-glock/<int:pk>/editar/', views.pistola_glock_edit, name='pistola_glock_edit'),
    path('pistolas-glock/<int:pk>/excluir/', views.pistola_glock_delete, name='pistola_glock_delete'),

    # Pistolas Taurus
    path('pistolas-taurus/', views.pistola_taurus_list, name='pistola_taurus_list'),
    path('pistolas-taurus/nova/', views.pistola_taurus_create, name='pistola_taurus_create'),
    path('pistolas-taurus/<int:pk>/editar/', views.pistola_taurus_edit, name='pistola_taurus_edit'),
    path('pistolas-taurus/<int:pk>/excluir/', views.pistola_taurus_delete, name='pistola_taurus_delete'),

    # Transferências Pendentes
    path('transferencias/', views.transferencia_list, name='transferencia_list'),
    path('transferencias/nova/', views.transferencia_create, name='transferencia_create'),
    path('transferencias/<int:pk>/editar/', views.transferencia_edit, name='transferencia_edit'),
    path('transferencias/<int:pk>/excluir/', views.transferencia_delete, name='transferencia_delete'),

    # Red Dots
    path('red-dots/', views.reddot_list, name='reddot_list'),
    path('red-dots/novo/', views.reddot_create, name='reddot_create'),
    path('red-dots/<int:pk>/editar/', views.reddot_edit, name='reddot_edit'),
    path('red-dots/<int:pk>/excluir/', views.reddot_delete, name='reddot_delete'),

    # Magnificadores
    path('magnificadores/', views.magnificador_list, name='magnificador_list'),
    path('magnificadores/novo/', views.magnificador_create, name='magnificador_create'),
    path('magnificadores/<int:pk>/editar/', views.magnificador_edit, name='magnificador_edit'),
    path('magnificadores/<int:pk>/excluir/', views.magnificador_delete, name='magnificador_delete'),

    # Supressores
    path('supressores/', views.supressor_list, name='supressor_list'),
    path('supressores/novo/', views.supressor_create, name='supressor_create'),
    path('supressores/<int:pk>/editar/', views.supressor_edit, name='supressor_edit'),
    path('supressores/<int:pk>/excluir/', views.supressor_delete, name='supressor_delete'),

    # Vinculação Acessório–Fuzil
    path('vinculacoes/', views.vinculacao_list, name='vinculacao_list'),
    path('vinculacoes/nova/', views.vinculacao_create, name='vinculacao_create'),
    path('vinculacoes/<int:pk>/editar/', views.vinculacao_edit, name='vinculacao_edit'),
    path('vinculacoes/<int:pk>/excluir/', views.vinculacao_delete, name='vinculacao_delete'),

    # Kits Operacionais
    path('kits/', views.kit_list, name='kit_list'),
    path('kits/novo/', views.kit_create, name='kit_create'),
    path('kits/<int:pk>/editar/', views.kit_edit, name='kit_edit'),
    path('kits/<int:pk>/excluir/', views.kit_delete, name='kit_delete'),
    path('kits/<int:pk>/', views.kit_detail, name='kit_detail'),

    # Rádios HT
    path('radios-ht/', views.radio_ht_list, name='radio_ht_list'),
    path('radios-ht/novo/', views.radio_ht_create, name='radio_ht_create'),
    path('radios-ht/<int:pk>/editar/', views.radio_ht_edit, name='radio_ht_edit'),
    path('radios-ht/<int:pk>/excluir/', views.radio_ht_delete, name='radio_ht_delete'),

    # AM-640
    path('am640/', views.am640_list, name='am640_list'),
    path('am640/novo/', views.am640_create, name='am640_create'),
    path('am640/<int:pk>/editar/', views.am640_edit, name='am640_edit'),
    path('am640/<int:pk>/excluir/', views.am640_delete, name='am640_delete'),

    # AM-600
    path('am600/', views.am600_list, name='am600_list'),
    path('am600/novo/', views.am600_create, name='am600_create'),
    path('am600/<int:pk>/excluir/', views.am600_delete, name='am600_delete'),

    # Mosquetão Federal
    path('mosquetoes/', views.mosquetao_list, name='mosquetao_list'),
    path('mosquetoes/novo/', views.mosquetao_create, name='mosquetao_create'),
    path('mosquetoes/<int:pk>/excluir/', views.mosquetao_delete, name='mosquetao_delete'),

    # TASER
    path('tasers/', views.taser_list, name='taser_list'),
    path('tasers/novo/', views.taser_create, name='taser_create'),
    path('tasers/<int:pk>/editar/', views.taser_edit, name='taser_edit'),
    path('tasers/<int:pk>/excluir/', views.taser_delete, name='taser_delete'),

    # Algemas
    path('algemas/', views.algemas_list, name='algemas_list'),
    path('algemas/nova/', views.algemas_create, name='algemas_create'),
    path('algemas/<int:pk>/editar/', views.algemas_edit, name='algemas_edit'),
    path('algemas/<int:pk>/excluir/', views.algemas_delete, name='algemas_delete'),

    # Munições Químicas
    path('municao-quimica/', views.municao_quimica_list, name='municao_quimica_list'),
    path('municao-quimica/nova/', views.municao_quimica_create, name='municao_quimica_create'),
    path('municao-quimica/<int:pk>/editar/', views.municao_quimica_edit, name='municao_quimica_edit'),
    path('municao-quimica/<int:pk>/excluir/', views.municao_quimica_delete, name='municao_quimica_delete'),

    # Munições Convencionais
    path('municao-convencional/', views.municao_convencional_list, name='municao_convencional_list'),
    path('municao-convencional/nova/', views.municao_convencional_create, name='municao_convencional_create'),
    path('municao-convencional/<int:pk>/editar/', views.municao_convencional_edit, name='municao_convencional_edit'),
    path('municao-convencional/<int:pk>/excluir/', views.municao_convencional_delete, name='municao_convencional_delete'),

    # Coletes Balísticos
    path('coletes/', views.colete_list, name='colete_list'),
    path('coletes/novo/', views.colete_create, name='colete_create'),
    path('coletes/<int:pk>/editar/', views.colete_edit, name='colete_edit'),
    path('coletes/<int:pk>/excluir/', views.colete_delete, name='colete_delete'),

    # Escudos Balísticos
    path('escudos/', views.escudo_list, name='escudo_list'),
    path('escudos/novo/', views.escudo_create, name='escudo_create'),
    path('escudos/<int:pk>/editar/', views.escudo_edit, name='escudo_edit'),
    path('escudos/<int:pk>/excluir/', views.escudo_delete, name='escudo_delete'),

    # Capacetes Balísticos
    path('capacetes/', views.capacete_list, name='capacete_list'),
    path('capacetes/novo/', views.capacete_create, name='capacete_create'),
    path('capacetes/<int:pk>/editar/', views.capacete_edit, name='capacete_edit'),
    path('capacetes/<int:pk>/excluir/', views.capacete_delete, name='capacete_delete'),
]
