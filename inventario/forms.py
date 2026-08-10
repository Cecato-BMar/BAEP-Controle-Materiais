from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from .models import CicloInventario, ItemInventario, ContaContabil


class ImportarInventarioForm(forms.Form):
    arquivo = forms.FileField(
        label=_('Arquivo do Inventário (.xlsx)'),
        help_text=_('Selecione o arquivo Excel oficial (ex: INVENTÁRIO - 2ºBAEP - EM - 2025..xlsx)'),
        widget=forms.FileInput(attrs={'accept': '.xlsx, .xls', 'class': 'form-control'})
    )
    titulo = forms.CharField(
        label=_('Título do Inventário'),
        initial='Inventário Físico e Contábil de Material Permanente',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    termo_numero = forms.CharField(
        label=_('Número do Termo'),
        required=False,
        help_text=_('Se deixado em branco, será extraído automaticamente do arquivo'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 2BAEP - 001/40/2026'})
    )
    ano = forms.IntegerField(
        label=_('Ano de Exercício'),
        initial=2026,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    semestre = forms.ChoiceField(
        label=_('Semestre'),
        choices=[(1, '1º Semestre'), (2, '2º Semestre')],
        initial=1,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    detentor_executivo = forms.CharField(
        label=_('Detentor Executivo (Responsável)'),
        required=False,
        help_text=_('Ex: Cap PM Felipe Torres Vieira'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'arquivo',
            Row(
                Column('titulo', css_class='form-group col-md-8 mb-3'),
                Column('termo_numero', css_class='form-group col-md-4 mb-3'),
            ),
            Row(
                Column('ano', css_class='form-group col-md-4 mb-3'),
                Column('semestre', css_class='form-group col-md-4 mb-3'),
                Column('detentor_executivo', css_class='form-group col-md-4 mb-3'),
            ),
            Submit('submit', _('Importar Inventário'), css_class='btn btn-success fw-bold px-4')
        )

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo')
        if arquivo:
            if not arquivo.name.endswith(('.xlsx', '.xls')):
                raise forms.ValidationError(_('Por favor, envie um arquivo Excel válido (.xlsx ou .xls).'))
        return arquivo


class CicloInventarioForm(forms.ModelForm):
    class Meta:
        model = CicloInventario
        fields = ['titulo', 'termo_numero', 'ano', 'semestre', 'data_referencia', 'detentor_executivo', 'opm_codigos', 'status', 'observacoes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_referencia'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('titulo', css_class='form-group col-md-8 mb-3'),
                Column('termo_numero', css_class='form-group col-md-4 mb-3'),
            ),
            Row(
                Column('ano', css_class='form-group col-md-3 mb-3'),
                Column('semestre', css_class='form-group col-md-3 mb-3'),
                Column('data_referencia', css_class='form-group col-md-3 mb-3'),
                Column('status', css_class='form-group col-md-3 mb-3'),
            ),
            Row(
                Column('detentor_executivo', css_class='form-group col-md-6 mb-3'),
                Column('opm_codigos', css_class='form-group col-md-6 mb-3'),
            ),
            'observacoes',
            Submit('submit', _('Salvar Inventário'), css_class='btn btn-primary fw-bold px-4')
        )


class ConferenciaItemForm(forms.ModelForm):
    class Meta:
        model = ItemInventario
        fields = ['conferido', 'situacao_fisica_conferida', 'observacoes_conferencia']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'conferido',
            'situacao_fisica_conferida',
            'observacoes_conferencia',
            Submit('submit', _('Salvar Conferência'), css_class='btn btn-success fw-bold')
        )


class FiltroInventarioForm(forms.Form):
    busca = forms.CharField(
        label=_('Buscar por Patrimônio, Série ou Material'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digite tombo, série ou nome...'})
    )
    conta = forms.ModelChoiceField(
        label=_('Conta Contábil'),
        queryset=ContaContabil.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    secao = forms.CharField(
        label=_('Seção / Subunidade'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: P/4, EM...'})
    )
    conferido = forms.ChoiceField(
        label=_('Status Conferência'),
        choices=[('', 'Todos'), ('SIM', 'Conferidos'), ('NAO', 'Pendentes de Conferência')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    situacao = forms.CharField(
        label=_('Situação do Material'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: EXCLUSÃO, EM USO...'})
    )
