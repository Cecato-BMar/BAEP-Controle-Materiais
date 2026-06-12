"""
viaturas/api/viewsets.py
ViewSets da API REST do módulo Frota.

Cada viewset:
  - Usa `permission_classes = [FrotaModulePermission]`
  - Define `filterset_class`, `search_fields`, `ordering_fields`
  - Sobrescreve `get_queryset()` com select_related/annotate
  - Delega lógica de negócio aos services
  - Expõe `@action` customizados para endpoints especiais
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, F

from viaturas.models import (
    MarcaViatura, ModeloViatura, Viatura, DespachoViatura,
    Abastecimento, Manutencao, Oficina, ChecklistViatura,
    SolicitacaoBaixaViatura, PecaViatura, RetiradaPeca,
    EvidenciaManutencao, PlanoManutencaoPreventiva, DocumentoViatura,
    ServicoManutencao, RegistroHistoricoManutencao,
)

from viaturas.api.permissions import FrotaModulePermission
from viaturas.api.pagination import StandardResultsPagination

from viaturas.api.serializers import (
    MarcaViaturaSerializer, ModeloViaturaSerializer,
    ViaturaListSerializer, ViaturaDetailSerializer,
    DespachoViaturaSerializer, AbastecimentoSerializer,
    ManutencaoListSerializer, ManutencaoDetailSerializer,
    OficinaSerializer, ChecklistViaturaSerializer,
    SolicitacaoBaixaViaturaSerializer, PecaViaturaSerializer,
    RetiradaPecaSerializer, EvidenciaManutencaoSerializer,
    PlanoManutencaoPreventivaSerializer, DocumentoViaturaSerializer,
    ServicoManutencaoSerializer, RegistroHistoricoManutencaoSerializer,
    DashboardResumoSerializer, IndicadoresViaturaSerializer,
    PrevisaoItemSerializer,
)

from viaturas.api.filters import (
    ViaturaFilter, ModeloViaturaFilter, OficinaFilter,
    DespachoFilter, AbastecimentoFilter, ManutencaoFilter,
    ChecklistFilter, SolicitacaoBaixaFilter, PecaFilter,
    RetiradaPecaFilter, DocumentoFilter, PlanoPreventivoFilter,
    ServicoManutencaoFilter,
)


# ============================================================================
# CADASTROS AUXILIARES
# ============================================================================
class MarcaViaturaViewSet(viewsets.ModelViewSet):
    serializer_class = MarcaViaturaSerializer
    permission_classes = [FrotaModulePermission]
    search_fields = ['nome']
    ordering_fields = ['nome', 'ativo']
    ordering = ['nome']

    def get_queryset(self):
        return MarcaViatura.objects.annotate(total_modelos=Count('modelos'))


class ModeloViaturaViewSet(viewsets.ModelViewSet):
    serializer_class = ModeloViaturaSerializer
    permission_classes = [FrotaModulePermission]
    filterset_class = ModeloViaturaFilter
    search_fields = ['nome', 'marca__nome']
    ordering_fields = ['nome', 'marca__nome', 'tipo', 'ativo']
    ordering = ['marca__nome', 'nome']

    def get_queryset(self):
        return (
            ModeloViatura.objects
            .select_related('marca')
            .annotate(total_viaturas=Count('viaturas'))
        )


class OficinaViewSet(viewsets.ModelViewSet):
    serializer_class = OficinaSerializer
    permission_classes = [FrotaModulePermission]
    filterset_class = OficinaFilter
    search_fields = ['nome', 'cnpj', 'cidade', 'especialidade']
    ordering_fields = ['nome', 'cidade', 'ativo']
    ordering = ['nome']

    def get_queryset(self):
        return Oficina.objects.annotate(total_manutencoes=Count('manutencoes'))


# ============================================================================
# VIATURA
# ============================================================================
class ViaturaViewSet(viewsets.ModelViewSet):
    permission_classes = [FrotaModulePermission]
    filterset_class = ViaturaFilter
    search_fields = ['prefixo', 'placa', 'chassi', 'renavam', 'numero_patrimonio', 'modelo__nome']
    ordering_fields = ['prefixo', 'placa', 'status', 'localizacao', 'odometro_atual', 'ano_fabricacao']
    ordering = ['prefixo']

    def get_serializer_class(self):
        if self.action == 'list':
            return ViaturaListSerializer
        return ViaturaDetailSerializer

    def get_queryset(self):
        return (
            Viatura.objects
            .select_related('modelo', 'modelo__marca')
        )

    # ------------------------------------------------------------------
    # Custom actions
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'], url_path='indicadores')
    def indicadores(self, request, pk=None):
        """Indicadores consolidados de uma viatura."""
        from viaturas.services.indicadores_service import obter_indicadores_viatura
        viatura = self.get_object()
        data = obter_indicadores_viatura(viatura)
        serializer = IndicadoresViaturaSerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='previsao')
    def previsao(self, request, pk=None):
        """Análise preventiva da viatura."""
        from viaturas.services.previsao_service import analisar_previsao_viatura
        viatura = self.get_object()
        analise = analisar_previsao_viatura(viatura)
        serializer = PrevisaoItemSerializer(analise, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='mudar-status')
    def mudar_status(self, request, pk=None):
        """
        Altera o status de uma viatura.
        Body: {"status": "DISPONIVEL"}
        """
        viatura = self.get_object()
        novo_status = request.data.get('status')
        if not novo_status:
            return Response(
                {'detail': 'Campo "status" é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from viaturas.models import StatusViatura
        if novo_status not in StatusViatura.values:
            return Response(
                {'detail': f'Status inválido. Opções: {StatusViatura.values}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        viatura.status = novo_status
        viatura.save(update_fields=['status'])
        return Response({'detail': f'Status alterado para {novo_status}.'})


# ============================================================================
# DESPACHO
# ============================================================================
class DespachoViaturaViewSet(viewsets.ModelViewSet):
    serializer_class = DespachoViaturaSerializer
    permission_classes = [FrotaModulePermission]
    filterset_class = DespachoFilter
    search_fields = ['viatura__prefixo', 'viatura__placa', 'motorista__nome_guerra']
    ordering_fields = ['data_saida', 'data_retorno']
    ordering = ['-data_saida']

    def get_queryset(self):
        return (
            DespachoViatura.objects
            .select_related('viatura', 'motorista', 'encarregado', 'registrado_por')
        )

    @action(detail=True, methods=['post'], url_path='registrar-retorno')
    def registrar_retorno(self, request, pk=None):
        """
        Registra o retorno de um despacho.
        Body: {"km_retorno": 45230.5, "observacoes_retorno": "..."}
        """
        from django.utils import timezone as tz
        from decimal import Decimal

        despacho = self.get_object()
        if despacho.data_retorno:
            return Response(
                {'detail': 'Este despacho já possui retorno registrado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        km_retorno = request.data.get('km_retorno')
        if km_retorno is not None:
            km_retorno = Decimal(str(km_retorno))

        despacho.data_retorno = tz.now()
        despacho.km_retorno = km_retorno
        despacho.observacoes_retorno = request.data.get('observacoes_retorno', '')
        despacho.save()
        return Response({'detail': 'Retorno registrado com sucesso.'})


# ============================================================================
# ABASTECIMENTO
# ============================================================================
class AbastecimentoViewSet(viewsets.ModelViewSet):
    serializer_class = AbastecimentoSerializer
    permission_classes = [FrotaModulePermission]
    filterset_class = AbastecimentoFilter
    search_fields = ['viatura__prefixo', 'cupom_fiscal', 'posto_fornecedor']
    ordering_fields = ['data_abastecimento', 'quantidade_litros', 'valor_total']
    ordering = ['-data_abastecimento']

    def get_queryset(self):
        return Abastecimento.objects.select_related('viatura', 'motorista')


# ============================================================================
# MANUTENÇÃO
# ============================================================================
class ManutencaoViewSet(viewsets.ModelViewSet):
    permission_classes = [FrotaModulePermission]
    filterset_class = ManutencaoFilter
    search_fields = [
        'viatura__prefixo', 'oficina', 'ordem_servico', 'descricao',
        'oficina_fk__nome',
    ]
    ordering_fields = ['data_inicio', 'data_conclusao', 'status', 'tipo']
    ordering = ['-data_inicio']

    def get_serializer_class(self):
        if self.action == 'list':
            return ManutencaoListSerializer
        return ManutencaoDetailSerializer

    def get_queryset(self):
        return (
            Manutencao.objects
            .select_related('viatura', 'oficina_fk', 'registrado_por')
            .prefetch_related('servicos', 'evidencias', 'registros_historico')
        )

    @action(detail=True, methods=['post'], url_path='concluir')
    def concluir(self, request, pk=None):
        """Conclui uma manutenção com aprovação."""
        from viaturas.services.manutencao_service import concluir_manutencao
        from django.core.exceptions import ValidationError as DjangoValidationError

        manutencao = self.get_object()
        try:
            concluir_manutencao(
                manutencao,
                request.user,
                dados_conclusao=request.data if request.data else None,
            )
        except DjangoValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ManutencaoDetailSerializer(manutencao)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        """Cancela uma manutenção com justificativa."""
        from viaturas.services.manutencao_service import cancelar_manutencao
        from django.core.exceptions import ValidationError as DjangoValidationError

        manutencao = self.get_object()
        motivo = request.data.get('motivo', '')
        try:
            cancelar_manutencao(manutencao, request.user, motivo=motivo)
        except DjangoValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ManutencaoDetailSerializer(manutencao)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='abertas')
    def abertas(self, request):
        """Lista apenas manutenções em aberto."""
        from viaturas.services.manutencao_service import listar_por_status
        qs = listar_por_status('abertas')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ManutencaoListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ManutencaoListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='agendadas')
    def agendadas(self, request):
        """Lista apenas manutenções agendadas."""
        from viaturas.services.manutencao_service import listar_por_status
        qs = listar_por_status('agendadas')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ManutencaoListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ManutencaoListSerializer(qs, many=True)
        return Response(serializer.data)


# ============================================================================
# SERVIÇO DE MANUTENÇÃO
# ============================================================================
class ServicoManutencaoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServicoManutencaoSerializer
    permission_classes = [FrotaModulePermission]
    filterset_class = ServicoManutencaoFilter
    search_fields = ['descricao', 'detalhamento', 'manutencao__viatura__prefixo']
    ordering = ['-data_registro']

    def get_queryset(self):
        return (
            ServicoManutencao.objects
            .select_related('manutencao', 'manutencao__viatura', 'registrado_por')
        )


# ============================================================================
# EVIDÊNCIA DE MANUTENÇÃO
# ============================================================================
class EvidenciaManutencaoViewSet(viewsets.ModelViewSet):
    serializer_class = EvidenciaManutencaoSerializer
    permission_classes = [FrotaModulePermission]
    search_fields = ['descricao', 'manutencao__viatura__prefixo']
    ordering = ['-data_upload']

    def get_queryset(self):
        return (
            EvidenciaManutencao.objects
            .select_related('manutencao', 'manutencao__viatura', 'registrado_por')
        )


# ============================================================================
# REGISTRO HISTÓRICO (read-only)
# ============================================================================
class RegistroHistoricoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RegistroHistoricoManutencaoSerializer
    permission_classes = [FrotaModulePermission]
    search_fields = ['titulo', 'descricao', 'manutencao__viatura__prefixo']
    ordering = ['-data_registro']

    def get_queryset(self):
        return (
            RegistroHistoricoManutencao.objects
            .select_related('manutencao', 'manutencao__viatura', 'registrado_por')
        )


# ============================================================================
# CHECKLIST
# ============================================================================
class ChecklistViaturaViewSet(viewsets.ModelViewSet):
    serializer_class = ChecklistViaturaSerializer
    permission_classes = [FrotaModulePermission]
    filterset_class = ChecklistFilter
    search_fields = ['viatura__prefixo', 'policial__nome_guerra']
    ordering_fields = ['data_hora', 'tipo']
    ordering = ['-data_hora']

    def get_queryset(self):
        return (
            ChecklistViatura.objects
            .select_related('viatura', 'policial', 'registrado_por')
        )


# ============================================================================
# SOLICITAÇÃO DE BAIXA
# ============================================================================
class SolicitacaoBaixaViewSet(viewsets.ModelViewSet):
    serializer_class = SolicitacaoBaixaViaturaSerializer
    permission_classes = [FrotaModulePermission]
    filterset_class = SolicitacaoBaixaFilter
    search_fields = ['viatura__prefixo', 'motivo']
    ordering = ['-data_solicitacao']

    def get_queryset(self):
        return (
            SolicitacaoBaixaViatura.objects
            .select_related('viatura', 'solicitante', 'motorista', 'requisitante', 'analisado_por')
        )


# ============================================================================
# PEÇAS
# ============================================================================
class PecaViaturaViewSet(viewsets.ModelViewSet):
    serializer_class = PecaViaturaSerializer
    permission_classes = [FrotaModulePermission]
    filterset_class = PecaFilter
    search_fields = ['nome', 'codigo', 'marca_fabricante', 'aplicacao']
    ordering_fields = ['nome', 'quantidade_estoque', 'valor_unitario']
    ordering = ['nome']

    def get_queryset(self):
        return PecaViatura.objects.all()


class RetiradaPecaViewSet(viewsets.ModelViewSet):
    serializer_class = RetiradaPecaSerializer
    permission_classes = [FrotaModulePermission]
    filterset_class = RetiradaPecaFilter
    search_fields = ['viatura__prefixo', 'policial__nome_guerra']
    ordering = ['-data_retirada']

    def get_queryset(self):
        return (
            RetiradaPeca.objects
            .select_related('viatura', 'policial', 'registrado_por')
            .prefetch_related('itens__peca')
        )


# ============================================================================
# PLANO PREVENTIVO
# ============================================================================
class PlanoManutencaoPreventivaViewSet(viewsets.ModelViewSet):
    serializer_class = PlanoManutencaoPreventivaSerializer
    permission_classes = [FrotaModulePermission]
    filterset_class = PlanoPreventivoFilter
    search_fields = ['descricao', 'modelo__nome', 'modelo__marca__nome']
    ordering = ['modelo__marca__nome', 'modelo__nome', 'descricao']

    def get_queryset(self):
        return (
            PlanoManutencaoPreventiva.objects
            .select_related('modelo', 'modelo__marca')
        )


# ============================================================================
# DOCUMENTO
# ============================================================================
class DocumentoViaturaViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentoViaturaSerializer
    permission_classes = [FrotaModulePermission]
    filterset_class = DocumentoFilter
    search_fields = ['viatura__prefixo', 'numero_documento']
    ordering_fields = ['tipo', 'data_vencimento']
    ordering = ['tipo', 'data_vencimento']

    def get_queryset(self):
        return (
            DocumentoViatura.objects
            .select_related('viatura', 'registrado_por')
        )


# ============================================================================
# DASHBOARD (endpoint agregado)
# ============================================================================
class DashboardViewSet(viewsets.ViewSet):
    """
    Endpoint agregado para o dashboard da frota.

    GET /api/frota/dashboard/ — retorna todos os KPIs e alertas.
    GET /api/frota/dashboard/status/ — apenas contagens de status.
    GET /api/frota/dashboard/kpis/ — apenas KPIs de custo.
    """
    permission_classes = [FrotaModulePermission]

    def list(self, request):
        from viaturas.services.indicadores_service import obter_contexto_dashboard
        contexto = obter_contexto_dashboard()
        # Serializar apenas os campos do schema DashboardResumoSerializer
        dados = DashboardResumoSerializer(contexto).data
        return Response(dados)

    @action(detail=False, methods=['get'], url_path='status')
    def status_counts(self, request):
        from viaturas.services.indicadores_service import obter_status_counts
        return Response(obter_status_counts())

    @action(detail=False, methods=['get'], url_path='kpis')
    def kpis(self, request):
        from viaturas.services.indicadores_service import obter_kpis_frota
        return Response(obter_kpis_frota())

    @action(detail=False, methods=['get'], url_path='previsao-frota')
    def previsao_frota(self, request):
        """
        Previsão de manutenção para toda a frota ativa.

        GET /api/frota/dashboard/previsao-frota/
        Retorna: resumo por viatura com próximas manutenções,
        data/km prevista e nível de confiança.
        """
        from viaturas.services.previsao_service import prever_frota
        resultado = prever_frota()
        # Simplificar para serialização JSON
        dados = {
            'alertas_atrasados': resultado['alertas_atrasados'],
            'alertas_urgentes': resultado['alertas_urgentes'],
            'total_previsoes': resultado['total_previsoes'],
            'total_viaturas': resultado['total_viaturas'],
            'viaturas': [],
        }
        for item in resultado['viaturas']:
            proxima = item.get('proxima_manutencao')
            previsoes_simplificadas = []
            for p in item['previsoes']:
                previsoes_simplificadas.append({
                    'nome': p['nome'],
                    'data_prevista': str(p['data_prevista']) if p['data_prevista'] else None,
                    'km_previsto': p['km_previsto'],
                    'restante_dias': p['restante_dias'],
                    'restante_km': p['restante_km'],
                    'status': p['status_prev'],
                    'confianca': p['confianca']['nivel'],
                    'confianca_score': p['confianca']['score'],
                    'historico_count': p['historico_count'],
                })
            dados['viaturas'].append({
                'prefixo': item['prefixo'],
                'modelo': item['modelo'],
                'odometro_atual': item['odometro_atual'],
                'taxa_km_diaria': item['taxa_km']['media_diaria'],
                'taxa_km_mensal': item['taxa_km']['media_mensal'],
                'taxa_km_metodo': item['taxa_km']['metodo'],
                'atrasados': item['atrasados'],
                'urgentes': item['urgentes'],
                'proxima_manutencao': {
                    'nome': proxima['nome'],
                    'data_prevista': str(proxima['data_prevista']) if proxima and proxima['data_prevista'] else None,
                    'km_previsto': proxima['km_previsto'],
                    'restante_dias': proxima['restante_dias'],
                    'status': proxima['status'],
                    'confianca': proxima['confianca'],
                } if proxima else None,
                'previsoes': previsoes_simplificadas,
            })
        return Response(dados)
