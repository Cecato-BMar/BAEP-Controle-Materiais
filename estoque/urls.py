from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_estoque, name='dashboard'),
    
    # Categorias
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/nova/', views.criar_categoria, name='criar_categoria'),
    path('categorias/<int:pk>/editar/', views.editar_categoria, name='editar_categoria'),
    
    # Unidades de Medida
    path('unidades-medida/', views.lista_unidades_medida, name='lista_unidades_medida'),
    path('unidades-medida/nova/', views.criar_unidade_medida, name='criar_unidade_medida'),
    
    # Fornecedores
    path('fornecedores/', views.lista_fornecedores, name='lista_fornecedores'),
    path('fornecedores/novo/', views.criar_fornecedor, name='criar_fornecedor'),
    path('fornecedores/<int:pk>/', views.detalhe_fornecedor, name='detalhe_fornecedor'),
    
    # Produtos
    path('produtos/', views.lista_produtos, name='lista_produtos'),
    path('produtos/novo/', views.criar_produto, name='criar_produto'),
    path('produtos/<int:pk>/', views.detalhe_produto, name='detalhe_produto'),
    path('produtos/<int:pk>/editar/', views.editar_produto, name='editar_produto'),
    
    # Movimentações
    path('movimentacoes/', views.lista_movimentacoes, name='lista_movimentacoes'),
    path('movimentacoes/nova/', views.criar_movimentacao, name='criar_movimentacao'),
    
    # Inventários
    path('inventarios/', views.lista_inventarios, name='lista_inventarios'),
    path('inventarios/novo/', views.criar_inventario, name='criar_inventario'),
    path('inventarios/<int:pk>/', views.detalhe_inventario, name='detalhe_inventario'),
    path('inventarios/<int:pk>/iniciar/', views.iniciar_inventario, name='iniciar_inventario'),
    path('inventarios/itens/<int:pk>/contar/', views.contar_item_inventario, name='contar_item_inventario'),
    
    # Relatórios
    path('relatorios/estoque-baixo/', views.relatorio_estoque_baixo, name='relatorio_estoque_baixo'),
    path('relatorios/movimentacoes-periodo/', views.relatorio_movimentacoes_periodo, name='relatorio_movimentacoes_periodo'),
    path('exportar/produtos-csv/', views.exportar_produtos_csv, name='exportar_produtos_csv'),
    path('exportar/movimentacoes-pdf/', views.exportar_movimentacoes_pdf, name='exportar_movimentacoes_pdf'),
    
    # AJAX
    path('ajax/buscar-produtos/', views.buscar_produtos_ajax, name='buscar_produtos_ajax'),
    path('ajax/buscar-produto-por-qr/', views.buscar_produto_por_qr_ajax, name='buscar_produto_por_qr_ajax'),
    path('ajax/buscar-lotes/', views.buscar_lotes_ajax, name='buscar_lotes_ajax'),
]
