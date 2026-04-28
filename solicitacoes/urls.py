from django.urls import path
from . import views

app_name = 'solicitacoes'

urlpatterns = [
    path('', views.MinhasSolicitacoesView.as_view(), name='minhas_solicitacoes'),
    path('novo/', views.CatalogoMateriaisView.as_view(), name='novo_pedido'),
    path('carrinho/', views.VerCarrinhoView.as_view(), name='ver_carrinho'),
    path('carrinho/add/<int:produto_id>/', views.adicionar_ao_carrinho, name='add_carrinho'),
    path('carrinho/remover/<int:produto_id>/', views.remover_do_carrinho, name='remover_carrinho'),
    path('finalizar/', views.finalizar_solicitacao, name='finalizar'),
    path('<int:pk>/', views.DetalheSolicitacaoView.as_view(), name='detalhe'),
    
    # Gestão (Logística)
    path('gestao/', views.GerenciarSolicitacoesView.as_view(), name='gestao_lista'),
    path('status/<int:pk>/<str:novo_status>/', views.mudar_status_solicitacao, name='mudar_status'),
    path('recibo/<int:pk>/', views.gerar_recibo_pdf, name='gerar_recibo'),
]
