from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from materiais.models import Material
from policiais.models import Policial
from .models import LoteMunicao, RetiradaMunicao, DevolucaoMunicao


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
    extravios = forms.IntegerField(label=_('Extravios'), min_value=0, required=False, initial=0)
    justificativa = forms.CharField(label=_('Justificativa'), required=False, widget=forms.Textarea(attrs={'rows': 3}))
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
            'extravios',
            'justificativa',
            'boletim_ocorrencia',
            'observacoes',
            Submit('submit', _('Registrar devolução'))
        )
