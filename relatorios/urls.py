from django.urls import path
from . import views

app_name = 'relatorios'

urlpatterns = [
    path('', views.lista_relatorios, name='lista_relatorios'),
    path('<int:relatorio_id>/', views.detalhe_relatorio, name='detalhe_relatorio'),
    path('<int:relatorio_id>/download/', views.download_relatorio, name='download_relatorio'),
    # path('<int:relatorio_id>/download/arquivo/', views.download_relatorio_arquivo, name='download_relatorio_arquivo'),
    path('situacao-atual/', views.gerar_relatorio_situacao, name='gerar_relatorio_situacao_atual'),
    path('materiais/', views.gerar_relatorio_materiais, name='gerar_relatorio_materiais'),
    path('movimentacoes/', views.gerar_relatorio_movimentacoes, name='gerar_relatorio_movimentacoes'),
    path('movimentacoes-estoque/', views.gerar_relatorio_estoque_movimentacoes, name='gerar_relatorio_estoque_movimentacoes'),
    path('patrimonio/', views.gerar_relatorio_patrimonio, name='gerar_relatorio_patrimonio'),
    path('frota/', views.gerar_relatorio_viaturas, name='gerar_relatorio_viaturas'),
    path('manutencoes/', views.gerar_relatorio_manutencoes, name='gerar_relatorio_manutencoes'),
    path('viatura/<int:viatura_id>/', views.gerar_relatorio_individual_viatura, name='gerar_relatorio_individual_viatura'),
]