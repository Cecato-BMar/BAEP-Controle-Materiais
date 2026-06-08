"""Admin do módulo Material Bélico."""
from django.contrib import admin
from .models import (
    Fuzil, EspingardaCal12, PistolaGlock, PistolaTaurus, ArmaTransferenciaPendente,
    RedDot, Magnificador, Supressor, VinculacaoAcessorioFuzil,
    KitOperacional, RadioHT, AM640, AM600, MosquetaoFederal,
    TASER, Algemas, MunicaoQuimica,
    MunicaoConvencional, DistribuicaoMunicaoKit,
    ColeteBalistico, EscudoBalistico, CapaceteBalistico,
    AuditoriaMaterialBelico,
)


# =============================================================================
# ARMAS DE FOGO
# =============================================================================

@admin.register(Fuzil)
class FuzilAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'patrimonio', 'localizacao', 'status', 'data_cadastro']
    list_filter = ['tipo', 'status', 'localizacao']
    search_fields = ['patrimonio', 'observacoes']


@admin.register(EspingardaCal12)
class EspingardaCal12Admin(admin.ModelAdmin):
    list_display = ['numero_espingarda', 'patrimonio', 'kit_vinculado', 'status']
    list_filter = ['status', 'kit_vinculado']
    search_fields = ['numero_espingarda', 'patrimonio']


@admin.register(PistolaGlock)
class PistolaGlockAdmin(admin.ModelAdmin):
    list_display = ['numero_serie', 'patrimonio', 'situacao_reserva', 'unidade', 'data_cadastro']
    list_filter = ['situacao_reserva', 'unidade']
    search_fields = ['numero_serie', 'patrimonio', 'numero_bopm']


@admin.register(PistolaTaurus)
class PistolaTaurusAdmin(admin.ModelAdmin):
    list_display = ['numero_serie', 'modelo', 'patrimonio', 'unidade']
    list_filter = ['modelo', 'unidade']
    search_fields = ['numero_serie', 'patrimonio']


@admin.register(ArmaTransferenciaPendente)
class ArmaTransferenciaPendenteAdmin(admin.ModelAdmin):
    list_display = ['especie', 'marca', 'modelo', 'nome_policial', 'situacao', 'status']
    list_filter = ['especie', 'situacao', 'status']
    search_fields = ['nome_policial', 'numero_serie', 're_policial']


# =============================================================================
# ACESSÓRIOS
# =============================================================================

@admin.register(RedDot)
class RedDotAdmin(admin.ModelAdmin):
    list_display = ['patrimonio', 'localizacao', 'status']
    list_filter = ['localizacao', 'status']
    search_fields = ['patrimonio']


@admin.register(Magnificador)
class MagnificadorAdmin(admin.ModelAdmin):
    list_display = ['patrimonio', 'localizacao', 'status']
    list_filter = ['localizacao', 'status']
    search_fields = ['patrimonio']


@admin.register(Supressor)
class SupressorAdmin(admin.ModelAdmin):
    list_display = ['patrimonio', 'localizacao', 'status']
    list_filter = ['localizacao']
    search_fields = ['patrimonio']


@admin.register(VinculacaoAcessorioFuzil)
class VinculacaoAcessorioFuzilAdmin(admin.ModelAdmin):
    list_display = ['fuzil', 'red_dot', 'magnificador', 'supressor']
    search_fields = ['fuzil__patrimonio']


# =============================================================================
# KITS OPERACIONAIS
# =============================================================================

@admin.register(KitOperacional)
class KitOperacionalAdmin(admin.ModelAdmin):
    list_display = ['numero_kit', 'fuzil_556_1', 'fuzil_762', 'espingarda', 'radio_ht', 'am640', 'escudo']
    list_filter = ['numero_kit']
    search_fields = ['numero_kit']


# =============================================================================
# COMUNICAÇÃO
# =============================================================================

@admin.register(RadioHT)
class RadioHTAdmin(admin.ModelAdmin):
    list_display = ['patrimonio', 'serie', 'kit_vinculado', 'situacao']
    list_filter = ['situacao']
    search_fields = ['patrimonio', 'serie']


@admin.register(AM640)
class AM640Admin(admin.ModelAdmin):
    list_display = ['serie', 'situacao']
    list_filter = ['situacao']
    search_fields = ['serie']


@admin.register(AM600)
class AM600Admin(admin.ModelAdmin):
    list_display = ['serie', 'situacao']
    search_fields = ['serie']


@admin.register(MosquetaoFederal)
class MosquetaoFederalAdmin(admin.ModelAdmin):
    list_display = ['serie', 'situacao']
    search_fields = ['serie']


# =============================================================================
# NÃO LETAIS
# =============================================================================

@admin.register(TASER)
class TASERAdmin(admin.ModelAdmin):
    list_display = ['serie', 'situacao', 'carga_bateria_percent']
    list_filter = ['situacao']
    search_fields = ['serie']


@admin.register(Algemas)
class AlgemasAdmin(admin.ModelAdmin):
    list_display = ['numero', 'embalagem']
    search_fields = ['numero']


@admin.register(MunicaoQuimica)
class MunicaoQuimicaAdmin(admin.ModelAdmin):
    list_display = ['tipo_municao', 'qtd_armario', 'qtd_kto', 'qtd_bornal', 'qtd_vencidas', 'validade_prazo']
    list_filter = ['tipo_municao']


# =============================================================================
# MUNIÇÕES
# =============================================================================

@admin.register(MunicaoConvencional)
class MunicaoConvencionalAdmin(admin.ModelAdmin):
    list_display = ['calibre', 'subtipo', 'secao', 'em_uso', 'estoque', 'manuseadas', 'danificado']
    list_filter = ['calibre', 'secao', 'subtipo']


class DistribuicaoMunicaoKitInline(admin.TabularInline):
    model = DistribuicaoMunicaoKit
    extra = 1


# =============================================================================
# PROTEÇÃO
# =============================================================================

@admin.register(ColeteBalistico)
class ColeteBalisticoAdmin(admin.ModelAdmin):
    list_display = ['marca', 'tamanho', 'numero_serie', 'situacao', 'tem_capa']
    list_filter = ['marca', 'situacao', 'tamanho']
    search_fields = ['numero_serie', 'patrimonio']


@admin.register(EscudoBalistico)
class EscudoBalisticoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'material', 'situacao', 'lote_companhia', 'validade']
    list_filter = ['situacao', 'lote_companhia']
    search_fields = ['numero_serie', 'patrimonio']


@admin.register(CapaceteBalistico)
class CapaceteBalisticoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'material', 'condicao', 'validade', 'lote_companhia']
    list_filter = ['condicao', 'material', 'lote_companhia']
    search_fields = ['numero_serie', 'patrimonio']


# =============================================================================
# AUDITORIA
# =============================================================================

@admin.register(AuditoriaMaterialBelico)
class AuditoriaMaterialBelicoAdmin(admin.ModelAdmin):
    list_display = ['data_hora', 'usuario', 'entidade', 'objeto_id', 'campo_alterado']
    list_filter = ['entidade', 'usuario']
    search_fields = ['campo_alterado', 're_usuario']
    readonly_fields = ['usuario', 're_usuario', 'entidade', 'objeto_id',
                        'campo_alterado', 'valor_anterior', 'valor_novo', 'data_hora']
