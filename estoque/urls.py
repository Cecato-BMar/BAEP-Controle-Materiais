from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    # =========================================================================
    # Dashboard e Painel de Controle (PAP §4)
    # =========================================================================
    path('', views.dashboard_estoque, name='dashboard'),
    path('painel/', views.painel_controle_estoque, name='painel_controle'),

    # =========================================================================
    # Entrada de Materiais (PAP §2)
    # =========================================================================
    path('entrada/', views.criar_entrada_material, name='criar_entrada_material'),

    # =========================================================================
    # Saída de Materiais (PAP §3)
    # =========================================================================
    path('saida/', views.criar_saida_material, name='criar_saida_material'),
    path('saida/confirmacao/', views.confirmacao_saida_material, name='confirmacao_saida_material'),
    path('saida/recibo/', views.exportar_recibo_saida_pdf, name='exportar_recibo_saida_pdf'),

    # =========================================================================
    # Categorias
    # =========================================================================
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/nova/', views.criar_categoria, name='criar_categoria'),
    path('categorias/<int:pk>/editar/', views.editar_categoria, name='editar_categoria'),

    # =========================================================================
    # Subcategorias
    # =========================================================================
    path('subcategorias/nova/', views.criar_subcategoria, name='criar_subcategoria'),

    # =========================================================================
    # Unidades de Medida (PAP §1)
    # =========================================================================
    path('unidades-medida/', views.lista_unidades_medida, name='lista_unidades_medida'),
    path('unidades-medida/nova/', views.criar_unidade_medida, name='criar_unidade_medida'),

    # =========================================================================
    # Unidades de Fornecimento (PAP §1 — Admin)
    # =========================================================================
    path('unidades-fornecimento/', views.lista_unidades_fornecimento, name='lista_unidades_fornecimento'),
    path('unidades-fornecimento/nova/', views.criar_unidade_fornecimento, name='criar_unidade_fornecimento'),

    # =========================================================================
    # Cores (PAP §1)
    # =========================================================================
    path('cores/', views.lista_cores, name='lista_cores'),
    path('cores/nova/', views.criar_cor, name='criar_cor'),

    # =========================================================================
    # Conta Patrimonial (PAP §1)
    # =========================================================================
    path('contas-patrimoniais/', views.lista_contas_patrimoniais, name='lista_contas_patrimoniais'),
    path('contas-patrimoniais/nova/', views.criar_conta_patrimonial, name='criar_conta_patrimonial'),
    path('contas-patrimoniais/<int:pk>/editar/', views.editar_conta_patrimonial, name='editar_conta_patrimonial'),

    # =========================================================================
    # Órgão Requisitante (PAP §1)
    # =========================================================================
    path('orgaos-requisitantes/', views.lista_orgaos_requisitantes, name='lista_orgaos_requisitantes'),
    path('orgaos-requisitantes/novo/', views.criar_orgao_requisitante, name='criar_orgao_requisitante'),
    path('orgaos-requisitantes/<int:pk>/editar/', views.editar_orgao_requisitante, name='editar_orgao_requisitante'),

    # =========================================================================
    # Localização Física (PAP §1)
    # =========================================================================
    path('localizacoes/', views.lista_localizacoes, name='lista_localizacoes'),
    path('localizacoes/nova/', views.criar_localizacao, name='criar_localizacao'),

    # =========================================================================
    # Militar Requisitante (PAP §1)
    # =========================================================================
    path('militares-requisitantes/', views.lista_militares_requisitantes, name='lista_militares_requisitantes'),
    path('militares-requisitantes/novo/', views.criar_militar_requisitante, name='criar_militar_requisitante'),
    path('militares-requisitantes/<int:pk>/editar/', views.editar_militar_requisitante, name='editar_militar_requisitante'),

    # =========================================================================
    # Fornecedores
    # =========================================================================
    path('fornecedores/', views.lista_fornecedores, name='lista_fornecedores'),
    path('fornecedores/novo/', views.criar_fornecedor, name='criar_fornecedor'),
    path('fornecedores/<int:pk>/', views.detalhe_fornecedor, name='detalhe_fornecedor'),

    # =========================================================================
    # Materiais de Consumo / Produtos (PAP §1)
    # =========================================================================
    path('materiais/', views.lista_produtos, name='lista_produtos'),
    path('materiais/novo/', views.criar_produto, name='criar_produto'),
    path('materiais/<int:pk>/', views.detalhe_produto, name='detalhe_produto'),
    path('materiais/<int:pk>/editar/', views.editar_produto, name='editar_produto'),

    # =========================================================================
    # Movimentações (histórico completo)
    # =========================================================================
    path('movimentacoes/', views.lista_movimentacoes, name='lista_movimentacoes'),
    path('movimentacoes/nova/', views.criar_movimentacao, name='criar_movimentacao'),

    # =========================================================================
    # Inventários (PAP §1.5)
    # =========================================================================
    path('inventarios/', views.lista_inventarios, name='lista_inventarios'),
    path('inventarios/novo/', views.criar_inventario, name='criar_inventario'),
    path('inventarios/<int:pk>/', views.detalhe_inventario, name='detalhe_inventario'),
    path('inventarios/<int:pk>/iniciar/', views.iniciar_inventario, name='iniciar_inventario'),
    path('inventarios/itens/<int:pk>/contar/', views.contar_item_inventario, name='contar_item_inventario'),

    # =========================================================================
    # Relatórios (PAP §5)
    # =========================================================================
    path('relatorios/estoque/', views.relatorio_estoque_materiais, name='relatorio_estoque_materiais'),
    path('relatorios/estoque-baixo/', views.relatorio_estoque_baixo, name='relatorio_estoque_baixo'),
    path('relatorios/situacao/', views.relatorio_situacao_estoque, name='relatorio_situacao_estoque'),
    path('relatorios/movimentacoes/', views.relatorio_movimentacoes_periodo, name='relatorio_movimentacoes_periodo'),
    path('relatorios/inventarios/', views.relatorio_inventarios, name='relatorio_inventarios'),
    path('relatorios/baixas/', views.relatorio_baixas_materiais, name='relatorio_baixas'),
    # Legado
    path('relatorios/materiais-manutencao/', views.relatorio_materiais_manutencao, name='relatorio_manutencao'),

    # =========================================================================
    # Exportação
    # =========================================================================
    path('exportar/materiais-csv/', views.exportar_produtos_csv, name='exportar_produtos_csv'),
    path('exportar/movimentacoes-pdf/', views.exportar_movimentacoes_pdf, name='exportar_movimentacoes_pdf'),

    # =========================================================================
    # AJAX
    # =========================================================================
    path('ajax/buscar-materiais/', views.buscar_produtos_ajax, name='buscar_produtos_ajax'),
    path('ajax/buscar-produto-por-qr/', views.buscar_produto_por_qr_ajax, name='buscar_produto_por_qr_ajax'),
    path('ajax/buscar-lotes/', views.buscar_lotes_ajax, name='buscar_lotes_ajax'),
    path('ajax/buscar-militar/', views.buscar_militar_por_re_ajax, name='buscar_militar_por_re_ajax'),
    path('ajax/saldo-produto/', views.buscar_saldo_produto_ajax, name='buscar_saldo_produto_ajax'),
]
