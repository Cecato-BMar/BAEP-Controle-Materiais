from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from django.contrib.auth.models import User
from materiais.models import Material
from policiais.models import Policial
from .models import LoteMunicao, RetiradaMunicao, DevolucaoMunicao, DevolucaoCPI


class LoteMunicaoForm(forms.ModelForm):
    class Meta:
        model = LoteMunicao
        fields = ['material', 'calibre', 'marca', 'numero_lote', 'tipo_municao', 'data_fabricacao', 'data_validade', 'quantidade_inicial', 'quantidade_atual', 'ativo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['material'].queryset = Material.objects.filter(tipo='MUNICAO')
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'material',
            'calibre',
            'marca',
            'numero_lote',
            'tipo_municao',
            'data_fabricacao',
            'data_validade',
            'quantidade_inicial',
            'quantidade_atual',
            'ativo',
            Submit('submit', _('Salvar lote'))
        )


class RetiradaMunicaoForm(forms.ModelForm):
    class Meta:
        model = RetiradaMunicao
        fields = ['policial', 'material', 'lote', 'quantidade', 'finalidade', 'local_uso', 'observacoes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['material'].queryset = Material.objects.filter(tipo='MUNICAO')
        self.fields['policial'].queryset = Policial.objects.filter(situacao='ATIVO')
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'policial',
            'material',
            'lote',
            'quantidade',
            'finalidade',
            'local_uso',
            'observacoes',
            Submit('submit', _('Registrar retirada'))
        )


class DevolucaoMunicaoForm(forms.ModelForm):
    class Meta:
        model = DevolucaoMunicao
        fields = ['retirada', 'quantidade', 'estado_devolucao', 'observacoes']

    disparos = forms.IntegerField(label=_('Disparos'), min_value=0, required=False, initial=0)
    estojos = forms.IntegerField(label=_('Estojos Vazios Devolvidos'), min_value=0, required=False, initial=0)
    extravios = forms.IntegerField(label=_('Extravios'), min_value=0, required=False, initial=0)
    justificativa = forms.CharField(label=_('Justificativa'), required=False, widget=forms.Textarea(attrs={'rows': 3}))
    sindicancia = forms.CharField(
        label=_('Sindicância / Apuração'),
        required=False,
        max_length=120,
        help_text=_('Preencha quando houver perda/extravio. Ex.: Sindicância 012/2026.')
    )
    boletim_ocorrencia = forms.CharField(label=_('B.O. / Relatório'), required=False, max_length=100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['retirada'].queryset = RetiradaMunicao.objects.filter().order_by('-data_hora')
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'retirada',
            'quantidade',
            'estado_devolucao',
            'disparos',
            'estojos',
            'extravios',
            'justificativa',
            'sindicancia',
            'boletim_ocorrencia',
            'observacoes',
            Submit('submit', _('Registrar devolução'))
        )


class DevolucaoCPIForm(forms.ModelForm):
    class Meta:
        model = DevolucaoCPI
        fields = ['lote', 'tipo_item', 'quantidade', 'documento_referencia', 'observacoes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lote'].queryset = LoteMunicao.objects.filter(ativo=True).order_by('material__nome', 'numero_lote')
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'lote',
            'tipo_item',
            'quantidade',
            'documento_referencia',
            'observacoes',
            Submit('submit', _('Registrar devolução ao CPI'))
        )


class RelatorioMunicoesForm(forms.Form):
    data_inicio = forms.DateField(label='Data inicial', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    data_fim = forms.DateField(label='Data final', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    material = forms.ModelChoiceField(
        label='Material',
        queryset=Material.objects.filter(tipo='MUNICAO').order_by('nome'),
        required=False
    )
    lote = forms.ModelChoiceField(
        label='Lote',
        queryset=LoteMunicao.objects.filter(ativo=True).order_by('material__nome', 'numero_lote'),
        required=False
    )
    policial = forms.ModelChoiceField(
        label='Policial',
        queryset=Policial.objects.filter(situacao='ATIVO').order_by('nome'),
        required=False
    )
    tipo_item_cpi = forms.ChoiceField(
        label='Tipo de devolução CPI',
        required=False,
        choices=[('', 'Todos'), ('CARTUCHO', 'Cartucho intacto'), ('ESTOJO', 'Estojo vazio')]
    )
    somente_com_extravio = forms.BooleanField(label='Somente com extravio', required=False)
    somente_pendentes = forms.BooleanField(label='Somente retiradas pendentes', required=False)
