from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, Div, HTML
from crispy_forms.bootstrap import FormActions
from .models import (
    Categoria, UnidadeMedida, UnidadeFornecimento, Cor, ContaPatrimonial,
    OrgaoRequisitante, LocalizacaoFisica, MilitarRequisitante,
    Fornecedor, Produto, Lote, NumeroSerie,
    MovimentacaoEstoque, Inventario, ItemInventario, AjusteEstoque
)


# =============================================================================
# CADASTROS MESTRES
# =============================================================================

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


class UnidadeFornecimentoForm(forms.ModelForm):
    class Meta:
        model = UnidadeFornecimento
        fields = ['nome', 'descricao', 'padrao', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 2}),
            'padrao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('nome', css_class='form-group col-md-6 mb-0'),
                Column('padrao', css_class='form-group col-md-3 mb-0'),
                Column('ativo', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            'descricao',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_unidades_fornecimento" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class CorForm(forms.ModelForm):
    class Meta:
        model = Cor
        fields = ['nome', 'ativo']
        widgets = {'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('nome', css_class='form-group col-md-8 mb-0'),
                Column('ativo', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_cores" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class ContaPatrimonialForm(forms.ModelForm):
    class Meta:
        model = ContaPatrimonial
        fields = ['codigo', 'descricao', 'ativo']
        widgets = {'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('codigo', css_class='form-group col-md-4 mb-0'),
                Column('descricao', css_class='form-group col-md-5 mb-0'),
                Column('ativo', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_contas_patrimoniais" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class OrgaoRequisitanteForm(forms.ModelForm):
    class Meta:
        model = OrgaoRequisitante
        fields = ['sigla', 'nome', 'ativo']
        widgets = {'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'})}

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
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_orgaos_requisitantes" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class LocalizacaoFisicaForm(forms.ModelForm):
    class Meta:
        model = LocalizacaoFisica
        fields = ['nome', 'descricao', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 2}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('nome', css_class='form-group col-md-8 mb-0'),
                Column('ativo', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'descricao',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_localizacoes" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


class MilitarRequisitanteForm(forms.ModelForm):
    class Meta:
        model = MilitarRequisitante
        fields = ['re', 'qra', 'nome_completo', 'orgao', 'ativo']
        widgets = {
            'orgao': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('re', css_class='form-group col-md-3 mb-0'),
                Column('qra', css_class='form-group col-md-3 mb-0'),
                Column('nome_completo', css_class='form-group col-md-4 mb-0'),
                Column('ativo', css_class='form-group col-md-2 mb-0'),
                css_class='form-row'
            ),
            'orgao',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_militares_requisitantes" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
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


# =============================================================================
# MATERIAL DE CONSUMO (PAP §1)
# =============================================================================

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            'codigo', 'codigo_barras', 'nome', 'descricao',
            'categoria', 'codigo_siafisico', 'codigo_cat_mat',
            'preco_medio', 'data_cotacao', 'data_inicio_projeto',
            'tempo_reposicao', 'termo_referencia', 'processo_sei',
            'historico_subcategoria',
            'unidade_medida', 'unidade_fornecimento',
            'estoque_minimo', 'estoque_maximo', 'valor_unitario',
            'fornecedor_padrao', 'localizacao_fisica', 'conta_patrimonial',
            'controla_validade', 'prazo_validade_meses', 'controla_numero_serie',
            'status', 'imagem',
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'historico_subcategoria': forms.Textarea(attrs={'rows': 3}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'unidade_fornecimento': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor_padrao': forms.Select(attrs={'class': 'form-select'}),
            'localizacao_fisica': forms.Select(attrs={'class': 'form-select'}),
            'conta_patrimonial': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_cotacao': forms.DateInput(attrs={'type': 'date'}),
            'data_inicio_projeto': forms.DateInput(attrs={'type': 'date'}),
            'controla_validade': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'controla_numero_serie': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['codigo_barras'].label = _('Código de Barras / Empenho')
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h6 class="text-muted border-bottom pb-2 mb-3"><i class="fas fa-tag me-2"></i>Identificação</h6>'),
            Row(
                Column('codigo', css_class='form-group col-md-3 mb-0'),
                Column('codigo_barras', css_class='form-group col-md-3 mb-0'),
                Column('status', css_class='form-group col-md-3 mb-0'),
                Column('categoria', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('nome', css_class='form-group col-md-8 mb-0'),
                Column('unidade_medida', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'descricao',
            HTML('<h6 class="text-muted border-bottom pb-2 mt-3 mb-3"><i class="fas fa-file-contract me-2"></i>Licitação / Aquisição (PAP)</h6>'),
            Row(
                Column('codigo_siafisico', css_class='form-group col-md-3 mb-0'),
                Column('codigo_cat_mat', css_class='form-group col-md-3 mb-0'),
                Column('termo_referencia', css_class='form-group col-md-3 mb-0'),
                Column('processo_sei', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('preco_medio', css_class='form-group col-md-3 mb-0'),
                Column('data_cotacao', css_class='form-group col-md-3 mb-0'),
                Column('data_inicio_projeto', css_class='form-group col-md-3 mb-0'),
                Column('tempo_reposicao', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            'historico_subcategoria',
            HTML('<h6 class="text-muted border-bottom pb-2 mt-3 mb-3"><i class="fas fa-boxes me-2"></i>Estoque e Vínculos</h6>'),
            Row(
                Column('estoque_minimo', css_class='form-group col-md-3 mb-0'),
                Column('estoque_maximo', css_class='form-group col-md-3 mb-0'),
                Column('valor_unitario', css_class='form-group col-md-3 mb-0'),
                Column('unidade_fornecimento', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('fornecedor_padrao', css_class='form-group col-md-4 mb-0'),
                Column('localizacao_fisica', css_class='form-group col-md-4 mb-0'),
                Column('conta_patrimonial', css_class='form-group col-md-4 mb-0'),
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
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar Material</button>'),
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
            raise forms.ValidationError(
                _('Prazo de validade é obrigatório quando controla validade está marcado.'))
        return cleaned_data


# =============================================================================
# ENTRADA DE MATERIAIS (PAP §2)
# =============================================================================

class EntradaMaterialForm(forms.ModelForm):
    """Formulário de Entrada conforme PAP §2"""

    class Meta:
        model = MovimentacaoEstoque
        fields = [
            'produto', 'subtipo', 'data_movimentacao',
            'cor', 'unidade_medida', 'unidade_fornecimento',
            'quantidade', 'conta_patrimonial', 'localizacao_fisica',
            'fornecedor', 'valor_unitario',
            'lote', 'nota_fiscal', 'observacoes',
        ]
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select', 'id': 'id_produto_entrada'}),
            'subtipo': forms.Select(attrs={'class': 'form-select'}),
            'data_movimentacao': forms.DateInput(
                attrs={'type': 'date', 'max': timezone.now().date().isoformat()}),
            'cor': forms.Select(attrs={'class': 'form-select'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'unidade_fornecimento': forms.Select(attrs={'class': 'form-select'}),
            'conta_patrimonial': forms.Select(attrs={'class': 'form-select'}),
            'localizacao_fisica': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limitar subtipos apenas para entradas
        self.fields['subtipo'].choices = [
            ('COMPRA_NOVA', 'Compra Nova'),
            ('DEVOLUCAO_ENTRADA', 'Devolução'),
        ]
        self.fields['unidade_fornecimento'].initial = UnidadeFornecimento.get_padrao()
        self.fields['data_movimentacao'].initial = timezone.now().date()
        # Data não pode ser retroativa por padrão
        self.fields['data_movimentacao'].widget.attrs['max'] = timezone.now().date().isoformat()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h6 class="text-muted border-bottom pb-2 mb-3"><i class="fas fa-arrow-down text-success me-2"></i>Dados da Entrada (PAP §2)</h6>'),
            Row(
                Column('produto', css_class='form-group col-md-5 mb-0'),
                Column('subtipo', css_class='form-group col-md-3 mb-0'),
                Column('data_movimentacao', css_class='form-group col-md-2 mb-0'),
                Column('cor', css_class='form-group col-md-2 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('unidade_medida', css_class='form-group col-md-3 mb-0'),
                Column('unidade_fornecimento', css_class='form-group col-md-3 mb-0'),
                Column('quantidade', css_class='form-group col-md-2 mb-0'),
                Column('valor_unitario', css_class='form-group col-md-2 mb-0'),
                Column(
                    HTML('<label class="form-label">Valor Total</label>'
                         '<div id="valor-total-entrada" class="form-control bg-light fw-bold">R$ 0,00</div>'),
                    css_class='form-group col-md-2 mb-0'
                ),
                css_class='form-row'
            ),
            Row(
                Column('conta_patrimonial', css_class='form-group col-md-4 mb-0'),
                Column('localizacao_fisica', css_class='form-group col-md-4 mb-0'),
                Column('fornecedor', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('lote', css_class='form-group col-md-4 mb-0'),
                Column('nota_fiscal', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'observacoes',
            FormActions(
                HTML('<button type="submit" class="btn btn-success"><i class="fas fa-arrow-down me-1"></i> Registrar Entrada</button>'),
                HTML('<a href="{% url "estoque:lista_movimentacoes" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


# =============================================================================
# SAÍDA DE MATERIAIS (PAP §3)
# =============================================================================

class SaidaMaterialForm(forms.ModelForm):
    """Formulário de Saída conforme PAP §3"""

    re_busca = forms.CharField(
        label=_('Buscar por RE'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o RE e pressione Enter',
            'id': 'id_re_busca',
            'autocomplete': 'off',
        }),
        help_text=_('O QRA será preenchido automaticamente.')
    )

    class Meta:
        model = MovimentacaoEstoque
        fields = [
            'produto', 'subtipo', 'data_movimentacao',
            'orgao_requisitante', 'militar_requisitante',
            'quantidade', 'observacoes',
        ]
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select', 'id': 'id_produto_saida'}),
            'subtipo': forms.Select(attrs={'class': 'form-select'}),
            'data_movimentacao': forms.DateInput(
                attrs={'type': 'date', 'max': timezone.now().date().isoformat()}),
            'orgao_requisitante': forms.Select(attrs={'class': 'form-select'}),
            'militar_requisitante': forms.Select(attrs={'class': 'form-select', 'id': 'id_militar_select'}),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subtipo'].choices = [
            ('REQUISICAO', 'Requisição'),
            ('DESCARTE', 'Descarte'),
        ]
        self.fields['data_movimentacao'].initial = timezone.now().date()
        self.fields['data_movimentacao'].widget.attrs['max'] = timezone.now().date().isoformat()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h6 class="text-muted border-bottom pb-2 mb-3"><i class="fas fa-arrow-up text-danger me-2"></i>Dados da Saída (PAP §3)</h6>'),
            Row(
                Column('produto', css_class='form-group col-md-5 mb-0'),
                Column('subtipo', css_class='form-group col-md-3 mb-0'),
                Column('data_movimentacao', css_class='form-group col-md-2 mb-0'),
                Column('quantidade', css_class='form-group col-md-2 mb-0'),
                css_class='form-row'
            ),
            HTML('<div id="saldo-disponivel-box" class="alert alert-info py-2 mb-3" style="display:none">'
                 '<i class="fas fa-info-circle me-1"></i> Saldo disponível: <strong id="saldo-valor">—</strong>'
                 '</div>'),
            HTML('<h6 class="text-muted border-bottom pb-2 mb-3 mt-2"><i class="fas fa-user-shield me-2"></i>Requisitante</h6>'),
            Row(
                Column('orgao_requisitante', css_class='form-group col-md-4 mb-0'),
                Column('re_busca', css_class='form-group col-md-3 mb-0'),
                Column('militar_requisitante', css_class='form-group col-md-5 mb-0'),
                css_class='form-row'
            ),
            'observacoes',
            FormActions(
                HTML('<button type="submit" class="btn btn-danger"><i class="fas fa-arrow-up me-1"></i> Registrar Saída</button>'),
                HTML('<a href="{% url "estoque:lista_movimentacoes" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get('produto')
        quantidade = cleaned_data.get('quantidade')
        subtipo = cleaned_data.get('subtipo')

        if produto and quantidade and subtipo in ['REQUISICAO', 'DESCARTE']:
            saldo = produto.saldo_calculado
            if quantidade > saldo:
                raise forms.ValidationError(
                    _(f'Quantidade ({quantidade}) maior que o saldo disponível ({saldo}). '
                      f'Operação bloqueada conforme PAP.')
                )
        return cleaned_data


# =============================================================================
# PAINEL DE CONTROLE — FILTRO DE PERÍODO (PAP §4)
# =============================================================================

class PainelEstoqueFilterForm(forms.Form):
    """Filtros do painel de controle de estoque (PAP §4)"""
    material = forms.ModelChoiceField(
        queryset=Produto.objects.filter(status='ATIVO'),
        required=False,
        label=_('Material (Subcategoria)'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_painel_material'})
    )
    data_inicio = forms.DateField(
        required=False,
        label=_('Data Início'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    data_fim = forms.DateField(
        required=False,
        label=_('Data Fim'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Row(
                Column('material', css_class='form-group col-md-5 mb-0'),
                Column('data_inicio', css_class='form-group col-md-3 mb-0'),
                Column('data_fim', css_class='form-group col-md-3 mb-0'),
                Column(
                    HTML('<label class="form-label">&nbsp;</label>'
                         '<div><button type="submit" class="btn btn-primary w-100">'
                         '<i class="fas fa-search me-1"></i> Calcular</button></div>'),
                    css_class='form-group col-md-1 mb-0'
                ),
                css_class='form-row align-items-end'
            )
        )


# =============================================================================
# LOTE
# =============================================================================

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
                HTML('<a href="javascript:history.back()" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        data_fabricacao = cleaned_data.get('data_fabricacao')
        data_validade = cleaned_data.get('data_validade')
        if data_fabricacao and data_validade and data_fabricacao >= data_validade:
            raise forms.ValidationError(
                _('Data de fabricação deve ser anterior à data de validade.'))
        return cleaned_data


# =============================================================================
# INVENTÁRIO
# =============================================================================

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
                 'quantidade_contada', 'justificativa_divergencia', 'observacoes']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'numero_serie': forms.Select(attrs={'class': 'form-select'}),
            'justificativa_divergencia': forms.Textarea(attrs={'rows': 2}),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
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
                css_class='form-row'
            ),
            'justificativa_divergencia',
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
                HTML('<a href="javascript:history.back()" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


# =============================================================================
# FORMULÁRIO LEGADO (compatibilidade)
# =============================================================================

class MovimentacaoEstoqueForm(forms.ModelForm):
    """Formulário genérico de movimentação (legado — use EntradaMaterialForm ou SaidaMaterialForm)"""
    class Meta:
        model = MovimentacaoEstoque
        fields = ['produto', 'lote', 'numero_serie', 'subtipo',
                 'quantidade', 'valor_unitario', 'documento_referencia',
                 'fornecedor', 'orgao_requisitante', 'militar_requisitante',
                 'observacoes']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'numero_serie': forms.Select(attrs={'class': 'form-select'}),
            'subtipo': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'orgao_requisitante': forms.Select(attrs={'class': 'form-select'}),
            'militar_requisitante': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('produto', css_class='form-group col-md-4 mb-0'),
                Column('subtipo', css_class='form-group col-md-4 mb-0'),
                Column('quantidade', css_class='form-group col-md-2 mb-0'),
                Column('valor_unitario', css_class='form-group col-md-2 mb-0'),
                css_class='form-row'
            ),
            'observacoes',
            FormActions(
                HTML('<button type="submit" class="btn btn-primary"><i class="fas fa-save"></i> Salvar</button>'),
                HTML('<a href="{% url "estoque:lista_movimentacoes" %}" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )


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
                HTML('<a href="javascript:history.back()" class="btn btn-secondary"><i class="fas fa-times"></i> Cancelar</a>')
            )
        )
