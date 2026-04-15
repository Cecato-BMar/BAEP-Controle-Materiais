from django import forms
from .models import CategoriaPatrimonio, BemPatrimonial, ItemPatrimonial, MovimentacaoPatrimonio
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit

class BemPatrimonialForm(forms.ModelForm):
    class Meta:
        model = BemPatrimonial
        fields = ['nome', 'categoria', 'marca', 'modelo_referencia', 'valor_unitario_estimado', 'descricao', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('nome', css_class='col-md-8'),
                Column('categoria', css_class='col-md-4'),
            ),
            Row(
                Column('marca', css_class='col-md-4'),
                Column('modelo_referencia', css_class='col-md-4'),
                Column('valor_unitario_estimado', css_class='col-md-4'),
            ),
            Row(
                Column('descricao', css_class='col-md-12'),
            ),
            Row(
                Column('ativo', css_class='col-md-12'),
            )
        )

class ItemPatrimonialForm(forms.ModelForm):
    class Meta:
        model = ItemPatrimonial
        fields = ['bem', 'numero_patrimonio', 'numero_serie', 'estado_conservacao', 'status', 'localizacao', 'data_aquisicao', 'nota_fiscal', 'observacoes']
        widgets = {
            'data_aquisicao': forms.DateInput(attrs={'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('bem', css_class='col-md-12'),
            ),
            Row(
                Column('numero_patrimonio', css_class='col-md-6'),
                Column('numero_serie', css_class='col-md-6'),
            ),
            Row(
                Column('estado_conservacao', css_class='col-md-4'),
                Column('status', css_class='col-md-4'),
                Column('localizacao', css_class='col-md-4'),
            ),
            Row(
                Column('data_aquisicao', css_class='col-md-4'),
                Column('nota_fiscal', css_class='col-md-8'),
            ),
            Row(
                Column('observacoes', css_class='col-md-12'),
            )
        )

class MovimentacaoPatrimonioForm(forms.ModelForm):
    class Meta:
        model = MovimentacaoPatrimonio
        fields = ['item', 'tipo', 'policial', 'local_destino', 'observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('item', css_class='col-md-12'),
            ),
            Row(
                Column('tipo', css_class='col-md-6'),
                Column('policial', css_class='col-md-6'),
            ),
            Row(
                Column('local_destino', css_class='col-md-12'),
            ),
            Row(
                Column('observacoes', css_class='col-md-12'),
            )
        )
