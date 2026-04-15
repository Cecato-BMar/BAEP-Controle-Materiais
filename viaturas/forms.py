from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div, Field
from .models import MarcaViatura, ModeloViatura, Viatura, DespachoViatura, Abastecimento, Manutencao


class ViaturaForm(forms.ModelForm):
    class Meta:
        model = Viatura
        fields = ['prefixo', 'placa', 'chassi', 'renavam', 'modelo',
                  'ano_fabricacao', 'cor', 'tipo_combustivel', 'capacidade_tanque',
                  'odometro_atual', 'status', 'observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
            'prefixo': forms.TextInput(attrs={'placeholder': 'Ex: E-10201'}),
            'placa': forms.TextInput(attrs={'placeholder': 'Ex: ABC-1234'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Row(
                    Column('prefixo', css_class='col-md-3'),
                    Column('placa', css_class='col-md-3'),
                    Column('modelo', css_class='col-md-4'),
                    Column('status', css_class='col-md-2'),
                ),
                Row(
                    Column('chassi', css_class='col-md-4'),
                    Column('renavam', css_class='col-md-3'),
                    Column('ano_fabricacao', css_class='col-md-2'),
                    Column('cor', css_class='col-md-3'),
                ),
                Row(
                    Column('tipo_combustivel', css_class='col-md-4'),
                    Column('capacidade_tanque', css_class='col-md-4'),
                    Column('odometro_atual', css_class='col-md-4'),
                ),
                Row(
                    Column('observacoes', css_class='col-12'),
                ),
            )
        )


class DespachoSaidaForm(forms.ModelForm):
    class Meta:
        model = DespachoViatura
        fields = ['viatura', 'motorista', 'encarregado', 'km_saida', 'observacoes_saida']
        widgets = {
            'observacoes_saida': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Registrar avarias ou observações pré-saída...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apenas viaturas disponíveis
        self.fields['viatura'].queryset = Viatura.objects.filter(status='DISPONIVEL')
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('viatura', css_class='col-md-4'),
                Column('motorista', css_class='col-md-4'),
                Column('encarregado', css_class='col-md-4'),
            ),
            Row(
                Column('km_saida', css_class='col-md-3'),
                Column('observacoes_saida', css_class='col-md-9'),
            ),
        )


class DespachoRetornoForm(forms.ModelForm):
    class Meta:
        model = DespachoViatura
        fields = ['km_retorno', 'observacoes_retorno']
        widgets = {
            'observacoes_retorno': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Registrar avarias constatadas no retorno...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('km_retorno', css_class='col-md-4'),
                Column('observacoes_retorno', css_class='col-md-8'),
            ),
        )


class AbastecimentoForm(forms.ModelForm):
    class Meta:
        model = Abastecimento
        fields = ['viatura', 'motorista', 'data_abastecimento', 'odometro',
                  'combustivel', 'quantidade_litros', 'valor_total',
                  'cupom_fiscal', 'posto_fornecedor']
        widgets = {
            'data_abastecimento': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('viatura', css_class='col-md-4'),
                Column('motorista', css_class='col-md-4'),
                Column('data_abastecimento', css_class='col-md-4'),
            ),
            Row(
                Column('combustivel', css_class='col-md-3'),
                Column('odometro', css_class='col-md-3'),
                Column('quantidade_litros', css_class='col-md-3'),
                Column('valor_total', css_class='col-md-3'),
            ),
            Row(
                Column('cupom_fiscal', css_class='col-md-4'),
                Column('posto_fornecedor', css_class='col-md-8'),
            ),
        )


class ManutencaoForm(forms.ModelForm):
    class Meta:
        model = Manutencao
        fields = ['viatura', 'tipo', 'data_inicio', 'data_conclusao',
                  'odometro', 'descricao', 'oficina',
                  'custo_pecas', 'custo_mao_obra', 'ordem_servico']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'data_conclusao': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descreva os serviços realizados e peças trocadas...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('viatura', css_class='col-md-5'),
                Column('tipo', css_class='col-md-3'),
                Column('ordem_servico', css_class='col-md-4'),
            ),
            Row(
                Column('data_inicio', css_class='col-md-3'),
                Column('data_conclusao', css_class='col-md-3'),
                Column('odometro', css_class='col-md-3'),
                Column('oficina', css_class='col-md-3'),
            ),
            Row(
                Column('descricao', css_class='col-12'),
            ),
            Row(
                Column('custo_pecas', css_class='col-md-4'),
                Column('custo_mao_obra', css_class='col-md-4'),
            ),
        )


class ModeloViaturaForm(forms.ModelForm):
    class Meta:
        model = ModeloViatura
        fields = ['marca', 'nome', 'tipo', 'ativo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('marca', css_class='col-md-6'),
                Column('nome', css_class='col-md-6'),
            ),
            Row(
                Column('tipo', css_class='col-md-8'),
                Column('ativo', css_class='col-md-4 d-flex align-items-center mt-3'),
            ),
        )


class MarcaViaturaForm(forms.ModelForm):
    class Meta:
        model = MarcaViatura
        fields = ['nome', 'ativo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('nome', css_class='col-md-8'),
                Column('ativo', css_class='col-md-4 d-flex align-items-center mt-3'),
            ),
        )
