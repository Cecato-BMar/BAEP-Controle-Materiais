"""
viaturas/api/filters.py
FilterSets para busca avançada nos endpoints da API Frota.

Usa django-filter (DjangoFilterBackend do DRF).
"""
from django_filters import rest_framework as filters

from viaturas.models import (
    Viatura, DespachoViatura, Abastecimento, Manutencao,
    ChecklistViatura, SolicitacaoBaixaViatura, PecaViatura,
    RetiradaPeca, DocumentoViatura, PlanoManutencaoPreventiva,
    ServicoManutencao, Oficina, ModeloViatura,
)


class ViaturaFilter(filters.FilterSet):
    """Filtros para listagem de viaturas."""
    tipo = filters.CharFilter(field_name='modelo__tipo', lookup_expr='exact')
    marca = filters.NumberFilter(field_name='modelo__marca_id')
    status = filters.CharFilter(field_name='status', lookup_expr='exact')
    localizacao = filters.CharFilter(field_name='localizacao', lookup_expr='exact')
    prefixo = filters.CharFilter(field_name='prefixo', lookup_expr='icontains')
    placa = filters.CharFilter(field_name='placa', lookup_expr='icontains')
    ano_min = filters.NumberFilter(field_name='ano_fabricacao', lookup_expr='gte')
    ano_max = filters.NumberFilter(field_name='ano_fabricacao', lookup_expr='lte')
    combustivel = filters.CharFilter(field_name='tipo_combustivel', lookup_expr='exact')

    class Meta:
        model = Viatura
        fields = ['status', 'localizacao', 'tipo', 'marca', 'combustivel']


class ModeloViaturaFilter(filters.FilterSet):
    marca = filters.NumberFilter(field_name='marca_id')
    tipo = filters.CharFilter(field_name='tipo', lookup_expr='exact')
    ativo = filters.BooleanFilter()

    class Meta:
        model = ModeloViatura
        fields = ['marca', 'tipo', 'ativo']


class OficinaFilter(filters.FilterSet):
    cidade = filters.CharFilter(lookup_expr='icontains')
    especialidade = filters.CharFilter(lookup_expr='icontains')
    ativo = filters.BooleanFilter()

    class Meta:
        model = Oficina
        fields = ['cidade', 'ativo', 'especialidade']


class DespachoFilter(filters.FilterSet):
    viatura = filters.NumberFilter(field_name='viatura_id')
    motorista = filters.NumberFilter(field_name='motorista_id')
    ativo = filters.BooleanFilter(method='filter_ativo')
    data_saida_min = filters.DateFilter(field_name='data_saida', lookup_expr='date__gte')
    data_saida_max = filters.DateFilter(field_name='data_saida', lookup_expr='date__lte')

    class Meta:
        model = DespachoViatura
        fields = ['viatura', 'motorista']

    def filter_ativo(self, queryset, name, value):
        if value:
            return queryset.filter(data_retorno__isnull=True)
        elif value is False:
            return queryset.filter(data_retorno__isnull=False)
        return queryset


class AbastecimentoFilter(filters.FilterSet):
    viatura = filters.NumberFilter(field_name='viatura_id')
    combustivel = filters.CharFilter(lookup_expr='exact')
    data_min = filters.DateFilter(field_name='data_abastecimento', lookup_expr='date__gte')
    data_max = filters.DateFilter(field_name='data_abastecimento', lookup_expr='date__lte')

    class Meta:
        model = Abastecimento
        fields = ['viatura', 'combustivel']


class ManutencaoFilter(filters.FilterSet):
    viatura = filters.NumberFilter(field_name='viatura_id')
    tipo = filters.CharFilter(lookup_expr='exact')
    status = filters.CharFilter(lookup_expr='exact')
    oficina = filters.NumberFilter(field_name='oficina_fk_id')
    data_inicio_min = filters.DateFilter(field_name='data_inicio', lookup_expr='gte')
    data_inicio_max = filters.DateFilter(field_name='data_inicio', lookup_expr='lte')
    data_conclusao_min = filters.DateFilter(field_name='data_conclusao', lookup_expr='gte')
    data_conclusao_max = filters.DateFilter(field_name='data_conclusao', lookup_expr='lte')

    class Meta:
        model = Manutencao
        fields = ['viatura', 'tipo', 'status', 'oficina']


class ChecklistFilter(filters.FilterSet):
    viatura = filters.NumberFilter(field_name='viatura_id')
    tipo = filters.CharFilter(lookup_expr='exact')
    data_min = filters.DateTimeFilter(field_name='data_hora', lookup_expr='gte')
    data_max = filters.DateTimeFilter(field_name='data_hora', lookup_expr='lte')

    class Meta:
        model = ChecklistViatura
        fields = ['viatura', 'tipo']


class SolicitacaoBaixaFilter(filters.FilterSet):
    viatura = filters.NumberFilter(field_name='viatura_id')
    status = filters.CharFilter(lookup_expr='exact')
    categoria_motivo = filters.CharFilter(lookup_expr='exact')

    class Meta:
        model = SolicitacaoBaixaViatura
        fields = ['viatura', 'status', 'categoria_motivo']


class PecaFilter(filters.FilterSet):
    categoria = filters.CharFilter(lookup_expr='exact')
    ativo = filters.BooleanFilter()
    estoque_baixo = filters.BooleanFilter(method='filter_estoque_baixo')

    class Meta:
        model = PecaViatura
        fields = ['categoria', 'ativo']

    def filter_estoque_baixo(self, queryset, name, value):
        if value:
            from django.db.models import F
            return queryset.filter(quantidade_estoque__lte=F('limite_minimo'), ativo=True)
        return queryset


class RetiradaPecaFilter(filters.FilterSet):
    viatura = filters.NumberFilter(field_name='viatura_id')
    policial = filters.NumberFilter(field_name='policial_id')
    data_min = filters.DateFilter(field_name='data_retirada', lookup_expr='date__gte')
    data_max = filters.DateFilter(field_name='data_retirada', lookup_expr='date__lte')

    class Meta:
        model = RetiradaPeca
        fields = ['viatura', 'policial']


class DocumentoFilter(filters.FilterSet):
    viatura = filters.NumberFilter(field_name='viatura_id')
    tipo = filters.CharFilter(lookup_expr='exact')
    ativo = filters.BooleanFilter()
    vencendo = filters.BooleanFilter(method='filter_vencendo')

    class Meta:
        model = DocumentoViatura
        fields = ['viatura', 'tipo', 'ativo']

    def filter_vencendo(self, queryset, name, value):
        if value:
            from django.utils import timezone
            from datetime import timedelta
            hoje = timezone.now().date()
            limite = hoje + timedelta(days=30)
            return queryset.filter(
                data_vencimento__isnull=False,
                data_vencimento__lte=limite,
                data_vencimento__gte=hoje,
                ativo=True,
            )
        return queryset


class PlanoPreventivoFilter(filters.FilterSet):
    modelo = filters.NumberFilter(field_name='modelo_id')
    marca = filters.NumberFilter(field_name='modelo__marca_id')
    ativo = filters.BooleanFilter()

    class Meta:
        model = PlanoManutencaoPreventiva
        fields = ['modelo', 'marca', 'ativo']


class ServicoManutencaoFilter(filters.FilterSet):
    manutencao = filters.NumberFilter(field_name='manutencao_id')
    viatura = filters.NumberFilter(field_name='manutencao__viatura_id')
    data_min = filters.DateTimeFilter(field_name='data_registro', lookup_expr='gte')
    data_max = filters.DateTimeFilter(field_name='data_registro', lookup_expr='lte')

    class Meta:
        model = ServicoManutencao
        fields = ['manutencao', 'viatura']
