"""Forms do módulo Material Bélico."""
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    Fuzil, EspingardaCal12, PistolaGlock, PistolaTaurus, ArmaTransferenciaPendente,
    RedDot, Magnificador, Supressor, VinculacaoAcessorioFuzil,
    KitOperacional, RadioHT, AM640, AM600, MosquetaoFederal,
    TASER, Algemas, MunicaoQuimica,
    MunicaoConvencional, DistribuicaoMunicaoKit,
    ColeteBalistico, EscudoBalistico, CapaceteBalistico,
)


# =============================================================================
# ARMAS DE FOGO
# =============================================================================

class FuzilForm(forms.ModelForm):
    class Meta:
        model = Fuzil
        fields = ['tipo', 'patrimonio', 'localizacao', 'numero_recibo', 'status', 'observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }


class EspingardaCal12Form(forms.ModelForm):
    class Meta:
        model = EspingardaCal12
        fields = ['numero_espingarda', 'patrimonio', 'kit_vinculado', 'status', 'observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }


class PistolaGlockForm(forms.ModelForm):
    class Meta:
        model = PistolaGlock
        fields = [
            'patrimonio', 'numero_serie', 'modelo', 'cod_opm', 'unidade',
            'situacao_reserva', 'numero_bopm', 'numero_bopc', 'observacoes',
        ]
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }


class PistolaTaurusForm(forms.ModelForm):
    class Meta:
        model = PistolaTaurus
        fields = ['patrimonio', 'numero_serie', 'modelo', 'unidade', 'observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }


class ArmaTransferenciaPendenteForm(forms.ModelForm):
    class Meta:
        model = ArmaTransferenciaPendente
        fields = [
            'especie', 'marca', 'modelo', 'calibre', 'numero_serie',
            'nome_policial', 'tipo_vinculo', 're_policial', 'situacao', 'status',
            'intencao_venda_nome', 'intencao_venda_re', 'observacoes',
        ]
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }


# =============================================================================
# ACESSÓRIOS
# =============================================================================

class RedDotForm(forms.ModelForm):
    class Meta:
        model = RedDot
        fields = ['patrimonio', 'localizacao', 'status']


class MagnificadorForm(forms.ModelForm):
    class Meta:
        model = Magnificador
        fields = ['patrimonio', 'localizacao', 'status']


class SupressorForm(forms.ModelForm):
    class Meta:
        model = Supressor
        fields = ['patrimonio', 'localizacao', 'status']


class VinculacaoAcessorioFuzilForm(forms.ModelForm):
    class Meta:
        model = VinculacaoAcessorioFuzil
        fields = ['fuzil', 'red_dot', 'magnificador', 'supressor', 'numero_recibo_transferencia']


# =============================================================================
# KITS OPERACIONAIS
# =============================================================================

class KitOperacionalForm(forms.ModelForm):
    class Meta:
        model = KitOperacional
        fields = [
            'numero_kit', 'fuzil_556_1', 'fuzil_556_2', 'fuzil_762',
            'espingarda', 'radio_ht', 'am640', 'escudo', 'observacoes',
        ]
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
            'fuzil_556_1': forms.Select(attrs={'class': 'form-select'}),
            'fuzil_556_2': forms.Select(attrs={'class': 'form-select'}),
            'fuzil_762': forms.Select(attrs={'class': 'form-select'}),
            'espingarda': forms.Select(attrs={'class': 'form-select'}),
            'radio_ht': forms.Select(attrs={'class': 'form-select'}),
            'am640': forms.Select(attrs={'class': 'form-select'}),
            'escudo': forms.Select(attrs={'class': 'form-select'}),
        }


# =============================================================================
# COMUNICAÇÃO
# =============================================================================

class RadioHTForm(forms.ModelForm):
    class Meta:
        model = RadioHT
        fields = [
            'patrimonio', 'serie', 'kit_vinculado', 'situacao',
            'chamado_dtic', 'data_chamado_dtic',
            'controle_bateria_numero', 'controle_bateria_localizacao', 'observacoes',
        ]
        widgets = {
            'data_chamado_dtic': forms.DateInput(attrs={'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }


class AM640Form(forms.ModelForm):
    class Meta:
        model = AM640
        fields = ['serie', 'situacao']


class AM600Form(forms.ModelForm):
    class Meta:
        model = AM600
        fields = ['serie']


class MosquetaoFederalForm(forms.ModelForm):
    class Meta:
        model = MosquetaoFederal
        fields = ['serie']


# =============================================================================
# NÃO LETAIS
# =============================================================================

class TASERForm(forms.ModelForm):
    class Meta:
        model = TASER
        fields = ['serie', 'situacao', 'carga_bateria_percent', 'observacoes']
        widgets = {
            'carga_bateria_percent': forms.NumberInput(attrs={
                'min': 0, 'max': 100, 'class': 'form-control',
            }),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_carga_bateria_percent(self):
        """RN-07: Validação de bateria."""
        carga = self.cleaned_data.get('carga_bateria_percent')
        if carga == 0:
            self.add_error('carga_bateria_percent',
                           _('Bateria em 0% — TASER bloqueado para operação (RN-07).'))
        return carga


class AlgemasForm(forms.ModelForm):
    class Meta:
        model = Algemas
        fields = ['numero', 'observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }


class MunicaoQuimicaForm(forms.ModelForm):
    class Meta:
        model = MunicaoQuimica
        fields = [
            'tipo_municao', 'qtd_armario', 'qtd_kto', 'qtd_bornal',
            'qtd_vencidas', 'validade_prazo', 'observacoes',
        ]
        widgets = {
            'validade_prazo': forms.DateInput(attrs={'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }


# =============================================================================
# MUNIÇÕES
# =============================================================================

class MunicaoConvencionalForm(forms.ModelForm):
    class Meta:
        model = MunicaoConvencional
        fields = [
            'calibre', 'subtipo', 'secao', 'em_uso', 'estoque',
            'manuseadas', 'capsulas', 'danificado', 'observacoes',
        ]
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }


class DistribuicaoMunicaoKitForm(forms.ModelForm):
    class Meta:
        model = DistribuicaoMunicaoKit
        fields = ['kit', 'calibre', 'subtipo', 'quantidade_cota']


# =============================================================================
# PROTEÇÃO BALÍSTICA
# =============================================================================

class ColeteBalisticoForm(forms.ModelForm):
    class Meta:
        model = ColeteBalistico
        fields = [
            'marca', 'tamanho', 'patrimonio', 'numero_serie', 'situacao',
            'obs', 'validade_descricao', 'ano_fabricacao', 'anos_validade',
            'tem_capa', 'obs_adicional',
        ]
        widgets = {
            'obs': forms.Textarea(attrs={'rows': 2}),
            'obs_adicional': forms.Textarea(attrs={'rows': 2}),
        }


class EscudoBalisticoForm(forms.ModelForm):
    class Meta:
        model = EscudoBalistico
        fields = [
            'numero', 'material', 'numero_serie', 'fabricacao', 'validade',
            'patrimonio', 'localizacao', 'lote_companhia', 'situacao',
        ]
        widgets = {
            'fabricacao': forms.DateInput(attrs={'type': 'date'}),
            'validade': forms.DateInput(attrs={'type': 'date'}),
        }


class CapaceteBalisticoForm(forms.ModelForm):
    class Meta:
        model = CapaceteBalistico
        fields = [
            'numero', 'material', 'numero_serie', 'patrimonio', 'fabricacao',
            'validade', 'localizacao', 'condicao', 'lote_companhia',
        ]
        widgets = {
            'fabricacao': forms.DateInput(attrs={'type': 'date'}),
        }
