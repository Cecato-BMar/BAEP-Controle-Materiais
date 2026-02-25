from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, Field, HTML
from .models import Movimentacao, Retirada, Devolucao
from materiais.models import Material
from policiais.models import Policial

class RetiradaForm(forms.Form):
    policial = forms.ModelChoiceField(
        label=_('Policial'),
        queryset=Policial.objects.filter(situacao='ATIVO'),
        empty_label=_('Selecione um policial'),
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    finalidade = forms.CharField(
        label=_('Finalidade'),
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': _('Finalidade da retirada')})
    )
    
    local_uso = forms.CharField(
        label=_('Local de Uso'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Local onde o material será utilizado')})
    )
    
    data_prevista_devolucao = forms.DateTimeField(
        label=_('Data Prevista para Devolução'),
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    
    observacoes = forms.CharField(
        label=_('Observações'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': _('Observações adicionais')})
    )
    
    # Campos ocultos para armazenar os materiais selecionados
    materiais_selecionados = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'policial',
            'finalidade',
            'local_uso',
            Field('data_prevista_devolucao', css_class='datetimepicker'),
            'observacoes',
            'materiais_selecionados',
            HTML('<div id="materiais-container" class="mt-4"><h4>Materiais Selecionados</h4><div id="materiais-lista"></div></div>'),
            Div(
                Submit('submit', _('Confirmar Retirada'), css_class='btn btn-primary'),
                css_class='text-center mt-4'
            )
        )

class DevolucaoForm(forms.Form):
    policial = forms.ModelChoiceField(
        label=_('Policial'),
        queryset=Policial.objects.filter(situacao='ATIVO'),
        empty_label=_('Selecione um policial'),
        required=False,
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    observacoes = forms.CharField(
        label=_('Observações'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': _('Observações adicionais')})
    )
    
    # Campos ocultos para armazenar os materiais selecionados para devolução
    devolucoes_selecionadas = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'policial',
            'observacoes',
            'devolucoes_selecionadas',
            HTML('<div id="devolucoes-container" class="mt-4"><h4>Materiais para Devolução</h4><div id="devolucoes-lista"></div></div>'),
            Div(
                Submit('submit', _('Confirmar Devolução'), css_class='btn btn-primary'),
                css_class='text-center mt-4'
            )
        )

class MovimentacaoSearchForm(forms.Form):
    tipo = forms.ChoiceField(
        label=_('Tipo'),
        required=False,
        choices=[(None, _('Todos'))] + Movimentacao.TIPO_CHOICES
    )
    
    policial = forms.ModelChoiceField(
        label=_('Policial'),
        queryset=Policial.objects.all(),
        required=False,
        empty_label=_('Todos')
    )
    
    material = forms.ModelChoiceField(
        label=_('Material'),
        queryset=Material.objects.all(),
        required=False,
        empty_label=_('Todos')
    )
    
    data_inicio = forms.DateField(
        label=_('Data Início'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    data_fim = forms.DateField(
        label=_('Data Fim'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'form-inline'
        self.helper.layout = Layout(
            'tipo',
            'policial',
            'material',
            'data_inicio',
            'data_fim',
            Submit('submit', _('Buscar'), css_class='btn btn-primary ml-2')
        )
        
        # Inicializa com a data atual se não for fornecida
        if not self.initial.get('data_fim'):
            self.initial['data_fim'] = timezone.now().date()
        if not self.initial.get('data_inicio'):
            self.initial['data_inicio'] = (timezone.now() - timezone.timedelta(days=30)).date()