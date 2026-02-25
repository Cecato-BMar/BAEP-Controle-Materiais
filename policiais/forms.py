from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div
from .models import Policial

class PolicialForm(forms.ModelForm):
    class Meta:
        model = Policial
        fields = ['re', 'nome', 'posto', 'situacao', 'observacoes', 'foto']
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
                Column('re', css_class='form-group col-md-6 mb-0'),
                Column('nome', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('posto', css_class='form-group col-md-6 mb-0'),
                Column('situacao', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'observacoes',
            'foto',
            Div(
                Submit('submit', _('Salvar'), css_class='btn btn-primary'),
                css_class='text-center'
            )
        )

class PolicialSearchForm(forms.Form):
    termo_busca = forms.CharField(
        label=_('Buscar'),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Nome, RE...')})
    )
    posto = forms.ChoiceField(
        label=_('Posto'),
        required=False,
        choices=[(None, _('Todos'))] + Policial.POSTO_CHOICES
    )
    situacao = forms.ChoiceField(
        label=_('Situação'),
        required=False,
        choices=[(None, _('Todos'))] + Policial.SITUACAO_CHOICES
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'form-inline'
        self.helper.layout = Layout(
            'termo_busca',
            'posto',
            'situacao',
            Submit('submit', _('Buscar'), css_class='btn btn-primary ml-2')
        )