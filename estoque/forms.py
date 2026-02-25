from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, Div, HTML
from crispy_forms.bootstrap import FormActions, AppendedText, PrependedText
from .models import (
    Categoria, UnidadeMedida, Fornecedor, Produto, Lote, NumeroSerie,
    MovimentacaoEstoque, Inventario, ItemInventario, AjusteEstoque
)


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'descricao', 'codigo', 'categoria_pai', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('codigo', css_class='form-group col-md-3 mb-0'),
                Column('nome', css_class='form-group col-md-6 mb-0'),
                Column('ativo', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            'categoria_pai',
            'descricao',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_categorias" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class UnidadeMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadeMedida
        fields = ['sigla', 'nome', 'descricao', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('sigla', css_class='form-group col-md-3 mb-0'),
                Column('nome', css_class='form-group col-md-6 mb-0'),
                Column('ativo', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            'descricao',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_unidades_medida" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = ['nome', 'tipo_pessoa', 'documento', 'inscricao_estadual', 
                 'telefone', 'email', 'endereco', 'cidade', 'estado', 'cep', 'ativo']
        widgets = {
            'tipo_pessoa': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.TextInput(attrs={'maxlength': 2, 'placeholder': 'UF'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('nome', css_class='form-group col-md-8 mb-0'),
                Column('tipo_pessoa', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('documento', css_class='form-group col-md-4 mb-0'),
                Column('inscricao_estadual', css_class='form-group col-md-4 mb-0'),
                Column('ativo', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('telefone', css_class='form-group col-md-4 mb-0'),
                Column('email', css_class='form-group col-md-8 mb-0'),
                css_class='form-row'
            ),
            'endereco',
            Row(
                Column('cidade', css_class='form-group col-md-6 mb-0'),
                Column('estado', css_class='form-group col-md-2 mb-0'),
                Column('cep', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_fornecedores" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['codigo', 'codigo_barras', 'nome', 'descricao', 'categoria', 
                 'unidade_medida', 'tipo_produto', 'status', 'estoque_minimo', 
                 'estoque_maximo', 'valor_unitario', 'controla_validade', 
                 'prazo_validade_meses', 'controla_numero_serie', 'fornecedor_padrao', 'imagem']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'tipo_produto': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor_padrao': forms.Select(attrs={'class': 'form-select'}),
            'controla_validade': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'controla_numero_serie': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'codigo_barras' in self.fields:
            self.fields['codigo_barras'].label = _('Número do empenho')

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('codigo', css_class='form-group col-md-3 mb-0'),
                Column('codigo_barras', css_class='form-group col-md-3 mb-0'),
                Column('tipo_produto', css_class='form-group col-md-3 mb-0'),
                Column('status', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            'nome',
            'descricao',
            Row(
                Column(
                    Div(
                        Field('categoria'),
                        HTML('<div class="mt-1"><a href="{% url "estoque:criar_categoria" %}" class="btn btn-sm btn-outline-secondary"><i class="fas fa-plus"></i> Adicionar categoria</a></div>'),
                    ),
                    css_class='form-group col-md-6 mb-0'
                ),
                Column(
                    Div(
                        Field('unidade_medida'),
                        HTML('<div class="mt-1"><a href="{% url "estoque:criar_unidade_medida" %}" class="btn btn-sm btn-outline-secondary"><i class="fas fa-plus"></i> Adicionar unidade</a></div>'),
                    ),
                    css_class='form-group col-md-6 mb-0'
                ),
                css_class='form-row'
            ),
            Row(
                Column('estoque_minimo', css_class='form-group col-md-3 mb-0'),
                Column('estoque_maximo', css_class='form-group col-md-3 mb-0'),
                Column('valor_unitario', css_class='form-group col-md-3 mb-0'),
                Column('fornecedor_padrao', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('controla_validade', css_class='form-group col-md-4 mb-0'),
                Column('prazo_validade_meses', css_class='form-group col-md-4 mb-0'),
                Column('controla_numero_serie', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'imagem',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_produtos" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        estoque_minimo = cleaned_data.get('estoque_minimo')
        estoque_maximo = cleaned_data.get('estoque_maximo')
        controla_validade = cleaned_data.get('controla_validade')
        prazo_validade = cleaned_data.get('prazo_validade_meses')

        if estoque_minimo and estoque_maximo and estoque_minimo >= estoque_maximo:
            raise forms.ValidationError(_('Estoque mínimo deve ser menor que o estoque máximo.'))

        if controla_validade and not prazo_validade:
            raise forms.ValidationError(_('Prazo de validade é obrigatório quando controla validade está marcado.'))

        return cleaned_data


class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = ['produto', 'numero_lote', 'data_fabricacao', 'data_validade', 
                 'quantidade_inicial', 'fornecedor', 'nota_fiscal', 'observacoes', 'ativo']
        widgets = {
            'data_fabricacao': forms.DateInput(attrs={'type': 'date'}),
            'data_validade': forms.DateInput(attrs={'type': 'date'}),
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('produto', css_class='form-group col-md-6 mb-0'),
                Column('numero_lote', css_class='form-group col-md-3 mb-0'),
                Column('nota_fiscal', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('data_fabricacao', css_class='form-group col-md-3 mb-0'),
                Column('data_validade', css_class='form-group col-md-3 mb-0'),
                Column('fornecedor', css_class='form-group col-md-4 mb-0'),
                Column('ativo', css_class='form-group col-md-2 mb-0'),
                css_class='form-row'
            ),
            'quantidade_inicial',
            'observacoes',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_lotes" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        data_fabricacao = cleaned_data.get('data_fabricacao')
        data_validade = cleaned_data.get('data_validade')

        if data_fabricacao and data_validade and data_fabricacao >= data_validade:
            raise forms.ValidationError(_('Data de fabricação deve ser anterior à data de validade.'))

        return cleaned_data


class NumeroSerieForm(forms.ModelForm):
    class Meta:
        model = NumeroSerie
        fields = ['produto', 'numero_serie', 'patrimonio', 'status', 'localizacao', 'responsavel', 'observacoes']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('produto', css_class='form-group col-md-6 mb-0'),
                Column('numero_serie', css_class='form-group col-md-3 mb-0'),
                Column('patrimonio', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('status', css_class='form-group col-md-4 mb-0'),
                Column('localizacao', css_class='form-group col-md-4 mb-0'),
                Column('responsavel', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'observacoes',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_numeros_serie" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class MovimentacaoEstoqueForm(forms.ModelForm):
    qr_code = forms.CharField(
        label=_('QR Code'),
        required=False,
        help_text=_('Cole aqui o token do QR Code para localizar o produto automaticamente.'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
    )

    class Meta:
        model = MovimentacaoEstoque
        fields = ['produto', 'lote', 'numero_serie', 'tipo_movimentacao', 'motivo', 
                 'quantidade', 'valor_unitario', 'documento_referencia', 'fornecedor', 
                 'solicitante', 'destino_origem', 'observacoes']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'numero_serie': forms.Select(attrs={'class': 'form-select'}),
            'tipo_movimentacao': forms.Select(attrs={'class': 'form-select'}),
            'motivo': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'solicitante': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('qr_code', css_class='form-group col-md-3 mb-0'),
                Column('produto', css_class='form-group col-md-3 mb-0'),
                Column('tipo_movimentacao', css_class='form-group col-md-3 mb-0'),
                Column('motivo', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('quantidade', css_class='form-group col-md-3 mb-0'),
                Column('valor_unitario', css_class='form-group col-md-3 mb-0'),
                Column('lote', css_class='form-group col-md-3 mb-0'),
                Column('numero_serie', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('documento_referencia', css_class='form-group col-md-4 mb-0'),
                Column('fornecedor', css_class='form-group col-md-4 mb-0'),
                Column('solicitante', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'destino_origem',
            'observacoes',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_movimentacoes" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['numero', 'descricao', 'tipo_inventario', 'data_prevista_fim', 
                 'responsavel', 'observacoes']
        widgets = {
            'tipo_inventario': forms.Select(attrs={'class': 'form-select'}),
            'data_prevista_fim': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('numero', css_class='form-group col-md-3 mb-0'),
                Column('tipo_inventario', css_class='form-group col-md-3 mb-0'),
                Column('data_prevista_fim', css_class='form-group col-md-3 mb-0'),
                Column('responsavel', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            'descricao',
            'observacoes',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_inventarios" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class ItemInventarioForm(forms.ModelForm):
    class Meta:
        model = ItemInventario
        fields = ['produto', 'lote', 'numero_serie', 'quantidade_sistema', 
                 'quantidade_contada', 'observacoes']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'numero_serie': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('produto', css_class='form-group col-md-4 mb-0'),
                Column('lote', css_class='form-group col-md-4 mb-0'),
                Column('numero_serie', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('quantidade_sistema', css_class='form-group col-md-4 mb-0'),
                Column('quantidade_contada', css_class='form-group col-md-4 mb-0'),
                Column('diferenca', css_class='form-group col-md-4 mb-0', readonly=True),
                css_class='form-row'
            ),
            'observacoes',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="javascript:history.back()" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class AjusteEstoqueForm(forms.ModelForm):
    class Meta:
        model = AjusteEstoque
        fields = ['produto', 'lote', 'numero_serie', 'tipo_ajuste', 'motivo', 
                 'quantidade', 'valor_unitario', 'observacoes']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'numero_serie': forms.Select(attrs={'class': 'form-select'}),
            'tipo_ajuste': forms.Select(attrs={'class': 'form-select'}),
            'motivo': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('produto', css_class='form-group col-md-4 mb-0'),
                Column('tipo_ajuste', css_class='form-group col-md-4 mb-0'),
                Column('motivo', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('quantidade', css_class='form-group col-md-4 mb-0'),
                Column('valor_unitario', css_class='form-group col-md-4 mb-0'),
                Column('lote', css_class='form-group col-md-2 mb-0'),
                Column('numero_serie', css_class='form-group col-md-2 mb-0'),
                css_class='form-row'
            ),
            'observacoes',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_ajustes" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )
