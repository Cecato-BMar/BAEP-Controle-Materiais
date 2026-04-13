from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div
from .models import Material
from estoque.models import LocalizacaoFisica

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['tipo', 'categoria', 'nome', 'numero', 'quantidade', 'estado', 'status', 'localizacao_fisica', 'observacoes', 'imagem']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            Row(
                Column('tipo', css_class='form-group col-md-4 mb-0'),
                Column('categoria', css_class='form-group col-md-4 mb-0'),
                Column('nome', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('numero', css_class='form-group col-md-6 mb-0'),
                Column('quantidade', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('estado', css_class='form-group col-md-4 mb-0'),
                Column('status', css_class='form-group col-md-4 mb-0'),
                Column('localizacao_fisica', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'observacoes',
            'imagem',
            Div(
                Submit('submit', _('Salvar'), css_class='btn btn-primary'),
                css_class='text-center'
            )
        )

class MaterialSearchForm(forms.Form):
    termo_busca = forms.CharField(
        label=_('Buscar Material'),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Nome, número, tipo...')})
    )
    tipo = forms.ChoiceField(
        label=_('Tipo'),
        required=False,
        choices=[(None, _('Todos'))] + Material.TIPO_CHOICES
    )
    categoria = forms.ChoiceField(
        label=_('Categoria'),
        required=False,
        choices=[('', _('Todos'))] + Material.CATEGORIA_CHOICES
    )
    status = forms.ChoiceField(
        label=_('Status'),
        required=False,
        choices=[('', _('Todos'))] + Material.STATUS_CHOICES
    )
    estado = forms.ChoiceField(
        label=_('Estado'),
        required=False,
        choices=[('', _('Todos'))] + Material.ESTADO_CHOICES
    )
    localizacao = forms.ModelChoiceField(
        label=_('Localização / CIA'),
        queryset=LocalizacaoFisica.objects.all(),
        required=False,
        empty_label=_('Todas')
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'form-inline'
        self.helper.layout = Layout(
            'termo_busca',
            'tipo',
            'categoria',
            'status',
            Submit('submit', _('Buscar'), css_class='btn btn-primary ml-2')
        )