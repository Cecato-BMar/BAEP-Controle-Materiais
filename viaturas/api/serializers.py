"""
viaturas/api/serializers.py
Serializers para a API REST do módulo Frota.

Organização:
  - Serializers de leitura (aninhados, com _display fields)
  - Serializers de escrita (validação de negócio)
  - Serializer de histórico (append-only, read-only)
"""
from rest_framework import serializers
from django.utils import timezone

from viaturas.models import (
    MarcaViatura, ModeloViatura, Viatura, DespachoViatura,
    Abastecimento, Manutencao, Oficina, ChecklistViatura,
    SolicitacaoBaixaViatura, PecaViatura, RetiradaPeca, RetiradaPecaItem,
    EvidenciaManutencao, PlanoManutencaoPreventiva, DocumentoViatura,
    ServicoManutencao, RegistroHistoricoManutencao,
)


# ============================================================================
# AUXILIARES — cadastros simples
# ============================================================================
class MarcaViaturaSerializer(serializers.ModelSerializer):
    total_modelos = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = MarcaViatura
        fields = ['id', 'nome', 'ativo', 'total_modelos']


class ModeloViaturaSerializer(serializers.ModelSerializer):
    marca_nome = serializers.CharField(source='marca.nome', read_only=True)
    tipo_display = serializers.CharField(read_only=True)
    total_viaturas = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ModeloViatura
        fields = [
            'id', 'marca', 'marca_nome', 'nome', 'tipo', 'tipo_display',
            'ativo', 'total_viaturas',
        ]


class OficinaSerializer(serializers.ModelSerializer):
    total_manutencoes = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Oficina
        fields = [
            'id', 'nome', 'cnpj', 'endereco', 'cidade', 'telefone',
            'contato_responsavel', 'especialidade', 'ativo',
            'data_cadastro', 'total_manutencoes',
        ]
        read_only_fields = ['data_cadastro']


# ============================================================================
# VIATURA
# ============================================================================
class ViaturaListSerializer(serializers.ModelSerializer):
    """Serializer otimizado para listas (select_related já feito no viewset)."""
    modelo_nome = serializers.SerializerMethodField()
    tipo = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    localizacao_display = serializers.CharField(read_only=True)

    class Meta:
        model = Viatura
        fields = [
            'id', 'prefixo', 'placa', 'modelo', 'modelo_nome', 'tipo',
            'status', 'status_display', 'localizacao', 'localizacao_display',
            'odometro_atual', 'ano_fabricacao', 'tipo_combustivel',
        ]

    def get_modelo_nome(self, obj):
        if obj.modelo:
            return f'{obj.modelo.marca.nome} {obj.modelo.nome}'
        return ''


class ViaturaDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalhe (com dados aninhados)."""
    modelo_nome = serializers.SerializerMethodField()
    tipo = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    localizacao_display = serializers.CharField(read_only=True)
    tipo_combustivel_display = serializers.CharField(read_only=True)

    class Meta:
        model = Viatura
        fields = [
            'id', 'prefixo', 'placa', 'chassi', 'renavam', 'numero_patrimonio',
            'modelo', 'modelo_nome', 'ano_fabricacao', 'cor', 'tipo',
            'tipo_combustivel', 'tipo_combustivel_display', 'capacidade_tanque',
            'odometro_atual', 'status', 'status_display',
            'localizacao', 'localizacao_display', 'observacoes',
            'data_cadastro', 'data_atualizacao',
        ]
        read_only_fields = ['data_cadastro', 'data_atualizacao']

    def get_modelo_nome(self, obj):
        if obj.modelo:
            return f'{obj.modelo.marca.nome} {obj.modelo.nome}'
        return ''


# ============================================================================
# DOCUMENTO
# ============================================================================
class DocumentoViaturaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(read_only=True)
    status_vencimento = serializers.CharField(read_only=True)
    viatura_prefixo = serializers.CharField(source='viatura.prefixo', read_only=True)

    class Meta:
        model = DocumentoViatura
        fields = [
            'id', 'viatura', 'viatura_prefixo', 'tipo', 'tipo_display',
            'numero_documento', 'data_emissao', 'data_vencimento',
            'arquivo', 'observacoes', 'ativo', 'status_vencimento',
            'registrado_por', 'data_cadastro', 'data_atualizacao',
        ]
        read_only_fields = ['registrado_por', 'data_cadastro', 'data_atualizacao']

    def create(self, validated_data):
        validated_data['registrado_por'] = self.context['request'].user
        return super().create(validated_data)


# ============================================================================
# DESPACHO
# ============================================================================
class DespachoViaturaSerializer(serializers.ModelSerializer):
    viatura_prefixo = serializers.CharField(source='viatura.prefixo', read_only=True)
    motorista_nome = serializers.CharField(
        source='motorista.nome_guerra', read_only=True, default='',
    )
    encarregado_nome = serializers.CharField(
        source='encarregado.nome_guerra', read_only=True, default='',
    )
    status_despacho = serializers.SerializerMethodField()

    class Meta:
        model = DespachoViatura
        fields = [
            'id', 'viatura', 'viatura_prefixo', 'motorista', 'motorista_nome',
            'encarregado', 'encarregado_nome', 'data_saida', 'km_saida',
            'data_retorno', 'km_retorno', 'observacoes_saida',
            'observacoes_retorno', 'registrado_por', 'status_despacho',
        ]
        read_only_fields = ['data_saida', 'registrado_por']

    def get_status_despacho(self, obj):
        return 'Retornou' if obj.data_retorno else 'Em Despacho'

    def create(self, validated_data):
        validated_data['registrado_por'] = self.context['request'].user
        return super().create(validated_data)


# ============================================================================
# ABASTECIMENTO
# ============================================================================
class AbastecimentoSerializer(serializers.ModelSerializer):
    viatura_prefixo = serializers.CharField(source='viatura.prefixo', read_only=True)
    combustivel_display = serializers.CharField(read_only=True)
    motorista_nome = serializers.CharField(
        source='motorista.nome_guerra', read_only=True, default='',
    )

    class Meta:
        model = Abastecimento
        fields = [
            'id', 'viatura', 'viatura_prefixo', 'motorista', 'motorista_nome',
            'data_abastecimento', 'odometro', 'combustivel', 'combustivel_display',
            'quantidade_litros', 'valor_total', 'cupom_fiscal',
            'posto_fornecedor', 'registrado_por',
        ]
        read_only_fields = ['registrado_por']

    def create(self, validated_data):
        validated_data['registrado_por'] = self.context['request'].user
        return super().create(validated_data)


# ============================================================================
# MANUTENÇÃO
# ============================================================================
class ServicoManutencaoSerializer(serializers.ModelSerializer):
    custo_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )

    class Meta:
        model = ServicoManutencao
        fields = [
            'id', 'manutencao', 'descricao', 'detalhamento', 'pecas_garantia',
            'custo_pecas', 'custo_mao_obra', 'custo_total', 'odometro',
            'status_na_epoca', 'registrado_por', 'data_registro',
        ]
        read_only_fields = ['registrado_por', 'data_registro', 'status_na_epoca']


class EvidenciaManutencaoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(read_only=True)

    class Meta:
        model = EvidenciaManutencao
        fields = [
            'id', 'manutencao', 'tipo', 'tipo_display', 'arquivo',
            'descricao', 'registrado_por', 'data_upload',
        ]
        read_only_fields = ['registrado_por', 'data_upload']


class RegistroHistoricoManutencaoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(read_only=True)

    class Meta:
        model = RegistroHistoricoManutencao
        fields = [
            'id', 'manutencao', 'tipo', 'tipo_display', 'titulo',
            'descricao', 'servico', 'metadados', 'registrado_por',
            'data_registro',
        ]
        read_only_fields = fields  # append-only


class ManutencaoListSerializer(serializers.ModelSerializer):
    viatura_prefixo = serializers.CharField(source='viatura.prefixo', read_only=True)
    oficina_nome = serializers.SerializerMethodField()
    tipo_display = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    custo_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )

    class Meta:
        model = Manutencao
        fields = [
            'id', 'viatura', 'viatura_prefixo', 'tipo', 'tipo_display',
            'status', 'status_display', 'data_inicio', 'data_conclusao',
            'oficina_fk', 'oficina_nome', 'ordem_servico', 'custo_pecas',
            'custo_mao_obra', 'custo_total', 'odometro',
        ]

    def get_oficina_nome(self, obj):
        if obj.oficina_fk:
            return obj.oficina_fk.nome
        return obj.oficina or ''


class ManutencaoDetailSerializer(serializers.ModelSerializer):
    viatura_prefixo = serializers.CharField(source='viatura.prefixo', read_only=True)
    oficina_nome = serializers.SerializerMethodField()
    tipo_display = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    custo_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    servicos = ServicoManutencaoSerializer(many=True, read_only=True)
    evidencias = EvidenciaManutencaoSerializer(many=True, read_only=True)
    registros_historico = RegistroHistoricoManutencaoSerializer(
        many=True, read_only=True,
    )

    class Meta:
        model = Manutencao
        fields = [
            'id', 'viatura', 'viatura_prefixo', 'tipo', 'tipo_display',
            'status', 'status_display', 'data_inicio', 'data_conclusao',
            'odometro', 'descricao', 'oficina_fk', 'oficina', 'oficina_nome',
            'ordem_servico', 'custo_pecas', 'custo_mao_obra', 'custo_total',
            'servicos_executados_corretamente', 'detalhamento_servicos',
            'detalhamento_pecas_garantia', 'nota_fiscal', 'termo_garantia',
            'data_validade_garantia', 'km_validade_garantia',
            'aprovado_por', 'data_aprovacao', 'parecer_aprovacao',
            'cancelado_por', 'data_cancelamento', 'motivo_cancelamento',
            'retirada_pecas', 'registrado_por',
            'data_criacao', 'data_atualizacao',
            'servicos', 'evidencias', 'registros_historico',
        ]
        read_only_fields = [
            'registrado_por', 'data_criacao', 'data_atualizacao',
            'aprovado_por', 'data_aprovacao', 'cancelado_por', 'data_cancelamento',
        ]

    def get_oficina_nome(self, obj):
        if obj.oficina_fk:
            return obj.oficina_fk.nome
        return obj.oficina or ''

    def create(self, validated_data):
        validated_data['registrado_por'] = self.context['request'].user
        return super().create(validated_data)


# ============================================================================
# CHECKLIST
# ============================================================================
class ChecklistViaturaSerializer(serializers.ModelSerializer):
    viatura_prefixo = serializers.CharField(source='viatura.prefixo', read_only=True)
    tipo_display = serializers.CharField(read_only=True)
    resultado = serializers.SerializerMethodField()

    class Meta:
        model = ChecklistViatura
        fields = [
            'id', 'viatura', 'viatura_prefixo', 'policial', 'tipo',
            'tipo_display', 'data_hora', 'odometro',
            # Conservação
            'limpeza_interna', 'limpeza_externa', 'conservacao_estofados',
            # Mecânica
            'niveis_fluidos', 'pneus_condicoes', 'pneu_estepe', 'freio_estacionamento',
            # Elétrica
            'farois_lanternas', 'setas_emergencia', 'giroflex_sirene', 'painel_instrumentos',
            # Equipamentos
            'extintor_incendio', 'triangulo_macaco_chave', 'cones_sinalizacao',
            'documentacao_crlv', 'kit_primeiros_socorros',
            # Danos
            'avarias_lataria', 'observacoes_gerais',
            'registrado_por', 'resultado',
        ]
        read_only_fields = ['data_hora', 'registrado_por']

    def get_resultado(self, obj):
        checks = [
            obj.limpeza_interna, obj.limpeza_externa, obj.conservacao_estofados,
            obj.niveis_fluidos, obj.pneus_condicoes, obj.pneu_estepe,
            obj.freio_estacionamento, obj.farois_lanternas, obj.setas_emergencia,
            obj.giroflex_sirene, obj.painel_instrumentos, obj.extintor_incendio,
            obj.triangulo_macaco_chave, obj.cones_sinalizacao,
            obj.documentacao_crlv, obj.kit_primeiros_socorros,
        ]
        return f'{sum(checks)}/{len(checks)} OK'

    def create(self, validated_data):
        validated_data['registrado_por'] = self.context['request'].user
        return super().create(validated_data)


# ============================================================================
# SOLICITAÇÃO DE BAIXA
# ============================================================================
class SolicitacaoBaixaViaturaSerializer(serializers.ModelSerializer):
    viatura_prefixo = serializers.CharField(source='viatura.prefixo', read_only=True)
    status_display = serializers.CharField(read_only=True)
    categoria_motivo_display = serializers.CharField(read_only=True)

    class Meta:
        model = SolicitacaoBaixaViatura
        fields = [
            'id', 'viatura', 'viatura_prefixo', 'motorista', 'requisitante',
            'categoria_motivo', 'categoria_motivo_display',
            'quilometragem_baixa', 'motivo', 'data_solicitacao',
            'status', 'status_display', 'observacoes_admin',
            'analisado_por', 'data_analise', 'solicitante',
        ]
        read_only_fields = ['solicitante', 'data_solicitacao', 'analisado_por', 'data_analise']

    def create(self, validated_data):
        validated_data['solicitante'] = self.context['request'].user
        return super().create(validated_data)


# ============================================================================
# PEÇAS
# ============================================================================
class PecaViaturaSerializer(serializers.ModelSerializer):
    categoria_display = serializers.CharField(read_only=True)
    estoque_status = serializers.SerializerMethodField()

    class Meta:
        model = PecaViatura
        fields = [
            'id', 'nome', 'codigo', 'categoria', 'categoria_display',
            'marca_fabricante', 'aplicacao', 'quantidade_estoque',
            'limite_minimo', 'localizacao_estoque', 'valor_unitario',
            'observacoes', 'ativo', 'estoque_status',
        ]

    def get_estoque_status(self, obj):
        if obj.quantidade_estoque <= 0:
            return 'Zerado'
        if obj.limite_minimo and obj.quantidade_estoque <= obj.limite_minimo:
            return 'Baixo'
        return 'Normal'


class RetiradaPecaItemSerializer(serializers.ModelSerializer):
    peca_nome = serializers.CharField(source='peca.nome', read_only=True)

    class Meta:
        model = RetiradaPecaItem
        fields = ['id', 'retirada', 'peca', 'peca_nome', 'quantidade']
        read_only_fields = ['retirada']


class RetiradaPecaSerializer(serializers.ModelSerializer):
    viatura_prefixo = serializers.CharField(source='viatura.prefixo', read_only=True)
    policial_nome = serializers.CharField(
        source='policial.nome_guerra', read_only=True, default='',
    )
    itens = RetiradaPecaItemSerializer(many=True, read_only=True)
    total_itens = serializers.SerializerMethodField()

    class Meta:
        model = RetiradaPeca
        fields = [
            'id', 'viatura', 'viatura_prefixo', 'policial', 'policial_nome',
            'data_retirada', 'observacoes', 'assinado_eletronicamente',
            'arquivo_recibo', 'registrado_por', 'itens', 'total_itens',
        ]
        read_only_fields = ['data_retirada', 'registrado_por']

    def get_total_itens(self, obj):
        return obj.itens.count()

    def create(self, validated_data):
        validated_data['registrado_por'] = self.context['request'].user
        return super().create(validated_data)


# ============================================================================
# PLANO PREVENTIVO
# ============================================================================
class PlanoManutencaoPreventivaSerializer(serializers.ModelSerializer):
    modelo_nome = serializers.SerializerMethodField()

    class Meta:
        model = PlanoManutencaoPreventiva
        fields = [
            'id', 'modelo', 'modelo_nome', 'descricao', 'intervalo_km',
            'intervalo_dias', 'ativo', 'data_cadastro',
        ]
        read_only_fields = ['data_cadastro']

    def get_modelo_nome(self, obj):
        return f'{obj.modelo.marca.nome} {obj.modelo.nome}' if obj.modelo else ''


# ============================================================================
# ENDPOINTS ESPECIAIS — agregados
# ============================================================================
class DashboardResumoSerializer(serializers.Serializer):
    """Schema do endpoint /api/frota/dashboard/."""
    total = serializers.IntegerField()
    disponiveis = serializers.IntegerField()
    em_uso = serializers.IntegerField()
    manutencao = serializers.IntegerField()
    baixadas = serializers.IntegerField()
    pecas_estoque_baixo = serializers.IntegerField()
    agendamentos_atrasados = serializers.IntegerField()
    garantias_vencidas = serializers.IntegerField()
    documentos_vencidos = serializers.IntegerField()
    custo_total_frota = serializers.DecimalField(max_digits=14, decimal_places=2)
    custo_medio = serializers.DecimalField(max_digits=12, decimal_places=2)
    tempo_medio_oficina = serializers.FloatField()
    total_manutencoes_concluidas = serializers.IntegerField()


class IndicadoresViaturaSerializer(serializers.Serializer):
    """Schema do endpoint /api/frota/viaturas/{id}/indicadores/."""
    total_km_rodado = serializers.DecimalField(max_digits=12, decimal_places=1)
    total_combustivel = serializers.DecimalField(max_digits=10, decimal_places=2)
    custo_total_manutencao = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_manutencoes = serializers.IntegerField()
    concluidas_count = serializers.IntegerField()
    preventivas_count = serializers.IntegerField()
    corretivas_count = serializers.IntegerField()


class ConfiancaSerializer(serializers.Serializer):
    """Schema do nível de confiança da previsão."""
    nivel = serializers.ChoiceField(choices=['ALTO', 'MÉDIO', 'BAIXO'])
    score = serializers.FloatField()
    fatores = serializers.DictField()


class PrevisaoItemSerializer(serializers.Serializer):
    """Schema de um item do endpoint /api/frota/viaturas/{id}/previsao/."""
    nome = serializers.CharField()
    historico_count = serializers.IntegerField()
    ultima_data = serializers.DateField(allow_null=True)
    ultimo_km = serializers.FloatField(allow_null=True)
    media_dias_duracao = serializers.IntegerField(allow_null=True)
    media_km_duracao = serializers.IntegerField(allow_null=True)
    intervalo_dias_ref = serializers.IntegerField()
    intervalo_km_ref = serializers.IntegerField()
    proxima_data = serializers.DateField()
    proximo_km = serializers.FloatField()
    data_por_km = serializers.DateField(allow_null=True)
    data_prevista = serializers.DateField()
    km_previsto = serializers.FloatField()
    restante_dias = serializers.IntegerField()
    restante_km = serializers.FloatField()
    status_prev = serializers.ChoiceField(choices=['OK', 'ALERTA', 'ATENCAO', 'ATRASADO'])
    confianca = ConfiancaSerializer()
    tipo_previsao = serializers.CharField()
    icone = serializers.CharField(required=False)
    prioridade = serializers.IntegerField(required=False)
