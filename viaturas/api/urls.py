"""
viaturas/api/urls.py
Routers da API REST do módulo Frota.

Todos os endpoints ficam em /api/frota/*
"""
from rest_framework.routers import DefaultRouter

from viaturas.api.viewsets import (
    MarcaViaturaViewSet,
    ModeloViaturaViewSet,
    OficinaViewSet,
    ViaturaViewSet,
    DespachoViaturaViewSet,
    AbastecimentoViewSet,
    ManutencaoViewSet,
    ServicoManutencaoViewSet,
    EvidenciaManutencaoViewSet,
    RegistroHistoricoViewSet,
    ChecklistViaturaViewSet,
    SolicitacaoBaixaViewSet,
    PecaViaturaViewSet,
    RetiradaPecaViewSet,
    PlanoManutencaoPreventivaViewSet,
    DocumentoViaturaViewSet,
    DashboardViewSet,
)

router = DefaultRouter()

# Dashboard agregado
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

# Cadastros auxiliares
router.register(r'marcas', MarcaViaturaViewSet)
router.register(r'modelos', ModeloViaturaViewSet)
router.register(r'oficinas', OficinaViewSet)

# Cadastro principal
router.register(r'viaturas', ViaturaViewSet)
router.register(r'documentos', DocumentoViaturaViewSet)

# Operação
router.register(r'despachos', DespachoViaturaViewSet)
router.register(r'abastecimentos', AbastecimentoViewSet)

# Manutenção
router.register(r'manutencoes', ManutencaoViewSet)
router.register(r'servicos', ServicoManutencaoViewSet)
router.register(r'evidencias', EvidenciaManutencaoViewSet)
router.register(r'historico', RegistroHistoricoViewSet)

# Inspeção
router.register(r'checklists', ChecklistViaturaViewSet)

# Baixa
router.register(r'baixas', SolicitacaoBaixaViewSet)

# Peças
router.register(r'pecas', PecaViaturaViewSet)
router.register(r'retiradas', RetiradaPecaViewSet)

# Preventiva
router.register(r'planos', PlanoManutencaoPreventivaViewSet)

urlpatterns = router.urls
