from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div
from .models import Relatorio
from materiais.models import Material
from policiais.models import Policial


class RelatorioDownloadForm(forms.Form):
    nome_arquivo = forms.CharField(
        label=_('Nome do arquivo'),
        max_length=100,
        initial='relatorio'
    )
    
    formato = forms.ChoiceField(
        label=_('Formato'),
        choices=[('pdf', 'PDF'), ('xlsx', 'Excel')],
        initial='pdf'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'nome_arquivo',
            'formato',
            Div(
                Submit('submit', _('Download'), css_class='btn btn-success'),
                css_class='text-center'
            )
        )

class RelatorioSituacaoAtualForm(forms.Form):
    titulo = forms.CharField(
        label=_('Título do Relatório'),
        initial=_('Situação Atual dos Materiais'),
        max_length=100
    )
    
    observacoes = forms.CharField(
        label=_('Observações'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 3})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'titulo',
            'observacoes',
            Div(
                Submit('submit', _('Gerar Relatório'), css_class='btn btn-primary'),
                css_class='text-center'
            )
        )

class RelatorioMateriaisForm(forms.Form):
    TIPO_RELATORIO_CHOICES = [
        ('MATERIAIS_EM_USO', _('Materiais em Uso')),
        ('MATERIAIS_DISPONIVEIS', _('Materiais Disponíveis')),
    ]
    
    tipo_relatorio = forms.ChoiceField(
        label=_('Tipo de Relatório'),
        choices=TIPO_RELATORIO_CHOICES
    )
    
    titulo = forms.CharField(
        label=_('Título do Relatório'),
        max_length=100
    )
    
    tipo_material = forms.ChoiceField(
        label=_('Tipo de Material'),
        required=False,
        choices=[(None, _('Todos'))] + Material.TIPO_CHOICES
    )
    
    observacoes = forms.CharField(
        label=_('Observações'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 3})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'tipo_relatorio',
            'titulo',
            'tipo_material',
            'observacoes',
            Div(
                Submit('submit', _('Gerar Relatório'), css_class='btn btn-primary'),
                css_class='text-center'
            )
        )

class RelatorioMovimentacoesForm(forms.Form):
    TIPO_RELATORIO_CHOICES = [
        ('MOVIMENTACOES_DIA', _('Movimentações do Dia')),
        ('MOVIMENTACOES_PERIODO', _('Movimentações por Período')),
        ('MOVIMENTACOES_POLICIAL', _('Movimentações por Policial')),
        ('MOVIMENTACOES_MATERIAL', _('Movimentações por Material')),
    ]
    
    tipo_relatorio = forms.ChoiceField(
        label=_('Tipo de Relatório'),
        choices=TIPO_RELATORIO_CHOICES
    )
    
    titulo = forms.CharField(
        label=_('Título do Relatório'),
        max_length=100
    )
    
    data_inicio = forms.DateField(
        label=_('Data Início'),
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    
    data_fim = forms.DateField(
        label=_('Data Fim'),
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    
    policial = forms.ModelChoiceField(
        label=_('Policial'),
        queryset=Policial.objects.all(),
        required=False,
        empty_label=_('Selecione um policial'),
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    material = forms.ModelChoiceField(
        label=_('Material'),
        queryset=Material.objects.all(),
        required=False,
        empty_label=_('Selecione um material'),
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    observacoes = forms.CharField(
        label=_('Observações'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 3})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        
        # Inicializa com a data atual se não for fornecida
        if not self.initial.get('data_fim'):
            self.initial['data_fim'] = timezone.now().date()
        if not self.initial.get('data_inicio'):
            self.initial['data_inicio'] = timezone.now().date()
        
        self.helper.layout = Layout(
            'tipo_relatorio',
            'titulo',
            Row(
                Column('data_inicio', css_class='form-group col-md-6 mb-0'),
                Column('data_fim', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'policial',
            'material',
            'observacoes',
            Div(
                Submit('submit', _('Gerar Relatório'), css_class='btn btn-primary'),
                css_class='text-center'
            )
        )
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_relatorio = cleaned_data.get('tipo_relatorio')
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        policial = cleaned_data.get('policial')
        material = cleaned_data.get('material')
        
        if tipo_relatorio == 'MOVIMENTACOES_PERIODO' and (not data_inicio or not data_fim):
            raise forms.ValidationError(_('Para relatórios por período, as datas de início e fim são obrigatórias.'))
        
        if tipo_relatorio == 'MOVIMENTACOES_POLICIAL' and not policial:
            raise forms.ValidationError(_('Para relatórios por policial, é necessário selecionar um policial.'))
        
        if tipo_relatorio == 'MOVIMENTACOES_MATERIAL' and not material:
            raise forms.ValidationError(_('Para relatórios por material, é necessário selecionar um material.'))
        
        if data_inicio and data_fim and data_inicio > data_fim:
            raise forms.ValidationError(_('A data de início não pode ser posterior à data de fim.'))
        
        return cleaned_data