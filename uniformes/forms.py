from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from .models import TipoUniforme, EntregaUniforme



class TipoUniformeForm(forms.ModelForm):
    class Meta:
        model = TipoUniforme
        fields = ['nome', 'prazo_meses', 'dias_alerta', 'ativo', 'descricao']
        widgets = {
            'descricao': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Descrição detalhada do item ou especificações técnicas (opcional)...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('nome', css_class='col-md-6'),
                Column('prazo_meses', css_class='col-md-3'),
                Column('dias_alerta', css_class='col-md-3'),
            ),
            Row(
                Column('ativo', css_class='col-md-12 mb-2'),
            ),
            'descricao',
            Submit('submit', 'Salvar Tipo de Uniforme', css_class='btn btn-primary px-4 mt-3'),
        )


class EntregaUniformeForm(forms.ModelForm):
    data_entrega = forms.DateField(
        label="Data da Entrega",
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
        initial=timezone.localdate,
    )

    class Meta:
        model = EntregaUniforme
        fields = ['policial', 'tipo_uniforme', 'quantidade', 'data_entrega', 'observacoes', 'ativa']
        widgets = {
            'observacoes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Observações complementares sobre a entrega (opcional)...'
            }),
            'policial': forms.Select(attrs={'class': 'form-select select2-policial'}),
            'tipo_uniforme': forms.Select(attrs={'class': 'form-select select2-tipo'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Na criação, sugere apenas tipos de uniforme ativos
        if not self.instance.pk:
            self.fields['tipo_uniforme'].queryset = TipoUniforme.objects.filter(ativo=True)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('policial', css_class='col-md-6'),
                Column('tipo_uniforme', css_class='col-md-6'),
            ),
            Row(
                Column('quantidade', css_class='col-md-4'),
                Column('data_entrega', css_class='col-md-4'),
                Column('ativa', css_class='col-md-4 d-flex align-items-center pt-3'),
            ),
            'observacoes',
            Submit('submit', 'Salvar Entrega', css_class='btn btn-primary px-4 mt-3'),
        )
