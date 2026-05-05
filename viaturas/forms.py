from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div, Field, HTML
from .models import MarcaViatura, ModeloViatura, Viatura, DespachoViatura, Abastecimento, Manutencao, Oficina, ChecklistViatura, SolicitacaoBaixaViatura, PecaViatura, RetiradaPeca, RetiradaPecaItem
from django.forms import inlineformset_factory
from policiais.models import Policial

class ViaturaForm(forms.ModelForm):
    class Meta:
        model = Viatura
        fields = ['prefixo', 'placa', 'chassi', 'renavam', 'modelo',
                  'ano_fabricacao', 'cor', 'tipo_combustivel', 'capacidade_tanque',
                  'odometro_atual', 'status', 'localizacao', 'observacoes']
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
                    Column('tipo_combustivel', css_class='col-md-3'),
                    Column('capacidade_tanque', css_class='col-md-3'),
                    Column('odometro_atual', css_class='col-md-3'),
                    Column('localizacao', css_class='col-md-3'),
                ),
                Row(
                    Column('observacoes', css_class='col-12'),
                ),
            )
        )


class OficinaForm(forms.ModelForm):
    class Meta:
        model = Oficina
        fields = ['nome', 'cnpj', 'endereco', 'cidade', 'telefone', 
                  'contato_responsavel', 'especialidade', 'ativo']
        widgets = {
            'endereco': forms.TextInput(attrs={'placeholder': 'Rua, número, bairro...'}),
            'cnpj': forms.TextInput(attrs={'placeholder': '00.000.000/0000-00'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('nome', css_class='col-md-8'),
                Column('cnpj', css_class='col-md-4'),
            ),
            Row(
                Column('endereco', css_class='col-md-8'),
                Column('cidade', css_class='col-md-4'),
            ),
            Row(
                Column('telefone', css_class='col-md-4'),
                Column('contato_responsavel', css_class='col-md-4'),
                Column('especialidade', css_class='col-md-4'),
            ),
            Row(
                Column('ativo', css_class='col-md-3 mt-3'),
            ),
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
        self.fields['encarregado'].label = "Comandante de Equipe"
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
    localizacao_fisica = forms.ChoiceField(
        choices=Viatura.LOCALIZACAO_CHOICES,
        label="Onde a viatura ficará estacionada?",
        help_text="Fisicamente, onde o veículo permanecerá durante a manutenção.",
        required=False
    )

    class Meta:
        model = Manutencao
        fields = ['viatura', 'tipo', 'status', 'data_inicio', 'data_conclusao',
                  'odometro', 'descricao', 'oficina_fk',
                  'custo_pecas', 'custo_mao_obra', 'ordem_servico',
                  'servicos_executados_corretamente', 'detalhamento_servicos',
                  'detalhamento_pecas_garantia', 'nota_fiscal', 'termo_garantia',
                  'data_validade_garantia', 'km_validade_garantia']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'data_conclusao': forms.DateInput(attrs={'type': 'date'}),
            'data_validade_garantia': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Qual era o problema/motivo da manutenção?'}),
            'detalhamento_servicos': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descreva detalhadamente os serviços executados pela oficina...'}),
            'detalhamento_pecas_garantia': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Quais peças foram trocadas? Informe detalhes e tempo/km de garantia.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.viatura:
            self.fields['localizacao_fisica'].initial = self.instance.viatura.localizacao
        else:
            self.fields['localizacao_fisica'].initial = 'OFICINA'
            
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            HTML('<h5 class="mb-3 text-primary"><i class="fas fa-wrench me-2"></i>Dados Gerais da Manutenção</h5>'),
            Row(
                Column('viatura', css_class='col-md-3'),
                Column('tipo', css_class='col-md-3'),
                Column('status', css_class='col-md-3'),
                Column('localizacao_fisica', css_class='col-md-3'),
            ),
            Row(
                Column('ordem_servico', css_class='col-md-3'),
                Column('data_inicio', css_class='col-md-3'),
                Column('data_conclusao', css_class='col-md-3'),
                Column('odometro', css_class='col-md-3'),
            ),
            Row(
                Column('oficina_fk', css_class='col-md-4'),
            ),
            Row(
                Column('descricao', css_class='col-12'),
            ),
            HTML('<hr class="my-4"><h5 class="mb-3 text-success"><i class="fas fa-check-circle me-2"></i>Controle, Custos e Garantia</h5>'),
            Row(
                Column('servicos_executados_corretamente', css_class='col-md-12 mb-3 fw-bold'),
            ),
            Row(
                Column('detalhamento_servicos', css_class='col-md-6'),
                Column('detalhamento_pecas_garantia', css_class='col-md-6'),
            ),
            Row(
                Column('custo_pecas', css_class='col-md-3'),
                Column('custo_mao_obra', css_class='col-md-3'),
                Column('data_validade_garantia', css_class='col-md-3'),
                Column('km_validade_garantia', css_class='col-md-3'),
            ),
            HTML('<hr class="my-4"><h5 class="mb-3 text-info"><i class="fas fa-paperclip me-2"></i>Anexos</h5>'),
            Row(
                Column('nota_fiscal', css_class='col-md-6'),
                Column('termo_garantia', css_class='col-md-6'),
            ),
        )
        
class AgendamentoManutencaoForm(forms.ModelForm):
    class Meta:
        model = Manutencao
        fields = ['viatura', 'tipo', 'data_inicio', 'oficina_fk', 'descricao']
        labels = {
            'data_inicio': 'Data Agendada',
            'descricao': 'Motivo / Serviço Previsto',
        }
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Qual é o motivo do agendamento?'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            HTML('<h5 class="mb-3 text-primary"><i class="fas fa-calendar-alt me-2"></i>Agendar Manutenção</h5>'),
            Row(
                Column('viatura', css_class='col-md-6'),
                Column('tipo', css_class='col-md-6'),
            ),
            Row(
                Column('data_inicio', css_class='col-md-6'),
                Column('oficina_fk', css_class='col-md-6'),
            ),
            Row(
                Column('descricao', css_class='col-12'),
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


class ImportarFrotaForm(forms.Form):
    arquivo = forms.FileField(
        label='Arquivo (XML ou XLSX)',
        help_text='Selecione o arquivo exportado do sistema SILP ou planilha de controle.'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'import-form'
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('arquivo', css_class='form-control'),
            Submit('submit', 'Iniciar Importação', css_class='btn btn-primary w-100 mt-3')
        )


class ChecklistViaturaForm(forms.ModelForm):
    class Meta:
        model = ChecklistViatura
        fields = [
            'viatura', 'policial', 'tipo', 'odometro',
            'limpeza_interna', 'limpeza_externa', 'conservacao_estofados',
            'niveis_fluidos', 'pneus_condicoes', 'pneu_estepe', 'freio_estacionamento',
            'farois_lanternas', 'setas_emergencia', 'giroflex_sirene', 'painel_instrumentos',
            'extintor_incendio', 'triangulo_macaco_chave', 'cones_sinalizacao', 
            'documentacao_crlv', 'kit_primeiros_socorros',
            'avarias_lataria', 'observacoes_gerais'
        ]
        widgets = {
            'avarias_lataria': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descreva detalhadamente quaisquer danos...'}),
            'observacoes_gerais': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Row(
                    Column('viatura', css_class='col-md-4'),
                    Column('policial', css_class='col-md-4'),
                    Column('tipo', css_class='col-md-2'),
                    Column('odometro', css_class='col-md-2'),
                ),
                css_class='section-header mb-4 p-3 bg-light rounded shadow-sm'
            ),
            
            Row(
                Column(
                    Div(
                        HTML('<h6 class="fw-bold text-primary mb-3"><i class="fas fa-broom me-2"></i>Conservação e Limpeza</h6>'),
                        'limpeza_interna', 'limpeza_externa', 'conservacao_estofados',
                        css_class='card p-3 mb-3 border-start border-primary border-4 shadow-sm'
                    ),
                    css_class='col-md-6'
                ),
                Column(
                    Div(
                        HTML('<h6 class="fw-bold text-success mb-3"><i class="fas fa-cogs me-2"></i>Mecânica e Rodagem</h6>'),
                        'niveis_fluidos', 'pneus_condicoes', 'pneu_estepe', 'freio_estacionamento',
                        css_class='card p-3 mb-3 border-start border-success border-4 shadow-sm'
                    ),
                    css_class='col-md-6'
                ),
            ),
            
            Row(
                Column(
                    Div(
                        HTML('<h6 class="fw-bold text-warning mb-3"><i class="fas fa-bolt me-2"></i>Elétrica e Sinalização</h6>'),
                        'farois_lanternas', 'setas_emergencia', 'giroflex_sirene', 'painel_instrumentos',
                        css_class='card p-3 mb-3 border-start border-warning border-4 shadow-sm'
                    ),
                    css_class='col-md-6'
                ),
                Column(
                    Div(
                        HTML('<h6 class="fw-bold text-info mb-3"><i class="fas fa-toolbox me-2"></i>Equipamentos e Docs</h6>'),
                        'extintor_incendio', 'triangulo_macaco_chave', 'cones_sinalizacao', 'documentacao_crlv', 'kit_primeiros_socorros',
                        css_class='card p-3 mb-3 border-start border-info border-4 shadow-sm'
                    ),
                    css_class='col-md-6'
                ),
            ),

            Row(
                Column('avarias_lataria', css_class='col-md-6'),
                Column('observacoes_gerais', css_class='col-md-6'),
            ),
        )

class SolicitacaoBaixaViaturaForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoBaixaViatura
        fields = ['viatura', 'categoria_motivo', 'quilometragem_baixa', 'motorista', 'requisitante', 'motivo']
        widgets = {
            'motivo': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Detalhe o motivo técnico ou operacional para a baixa definitiva desta viatura.'}),
            'viatura': forms.Select(attrs={'class': 'select2'}),
            'motorista': forms.Select(attrs={'class': 'select2'}),
            'requisitante': forms.Select(attrs={'class': 'select2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['viatura'].queryset = Viatura.objects.exclude(status='BAIXADA').order_by('prefixo')
        self.fields['motorista'].queryset = Policial.objects.all().order_by('nome')
        self.fields['requisitante'].queryset = Policial.objects.all().order_by('nome')
        
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('viatura', css_class='col-md-6 mb-3'),
                Column('categoria_motivo', css_class='col-md-6 mb-3'),
            ),
            Row(
                Column('motorista', css_class='col-md-4 mb-3'),
                Column('requisitante', css_class='col-md-4 mb-3'),
                Column('quilometragem_baixa', css_class='col-md-4 mb-3'),
            ),
            Row(
                Column('motivo', css_class='col-md-12 mb-3'),
            ),
        )

class AnaliseBaixaViaturaForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoBaixaViatura
        fields = ['status', 'observacoes_admin']
        widgets = {
            'observacoes_admin': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Parecer do administrador sobre a baixa.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('status', css_class='col-md-12'),
            ),
            Row(
                Column('observacoes_admin', css_class='col-md-12'),
            ),
        )

class PecaViaturaForm(forms.ModelForm):
    class Meta:
        model = PecaViatura
        fields = ['nome', 'codigo', 'categoria', 'marca_fabricante', 'aplicacao', 
                  'quantidade_estoque', 'limite_minimo', 'localizacao_estoque', 
                  'valor_unitario', 'observacoes', 'ativo']
        widgets = {
            'aplicacao': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ex: Hilux 2020+, Trailblazer 2022'}),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            HTML('<h6 class="mb-3 text-primary"><i class="fas fa-info-circle me-2"></i>Dados Principais</h6>'),
            Row(
                Column('nome', css_class='col-md-6'),
                Column('categoria', css_class='col-md-3'),
                Column('codigo', css_class='col-md-3'),
            ),
            Row(
                Column('marca_fabricante', css_class='col-md-6'),
                Column('aplicacao', css_class='col-md-6'),
            ),
            HTML('<hr class="my-4"><h6 class="mb-3 text-success"><i class="fas fa-boxes me-2"></i>Estoque e Custos</h6>'),
            Row(
                Column('quantidade_estoque', css_class='col-md-3'),
                Column('limite_minimo', css_class='col-md-3'),
                Column('localizacao_estoque', css_class='col-md-3'),
                Column('valor_unitario', css_class='col-md-3'),
            ),
            Row(
                Column('observacoes', css_class='col-md-9'),
                Column('ativo', css_class='col-md-3 d-flex align-items-center mt-4'),
            ),
        )

class RetiradaPecaForm(forms.ModelForm):
    class Meta:
        model = RetiradaPeca
        fields = ['viatura', 'policial', 'observacoes', 'assinado_eletronicamente']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Justificativa ou observações gerais sobre a retirada'}),
            'viatura': forms.Select(attrs={'class': 'select2'}),
            'policial': forms.Select(attrs={'class': 'select2'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['viatura'].queryset = Viatura.objects.filter(status__in=['DISPONIVEL', 'EM_USO', 'MANUTENCAO']).order_by('prefixo')
        self.fields['policial'].queryset = Policial.objects.all().order_by('nome')
        
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('viatura', css_class='col-md-6'),
                Column('policial', css_class='col-md-6'),
            ),
            Row(
                Column('observacoes', css_class='col-md-12'),
            ),
            Row(
                Column('assinado_eletronicamente', css_class='col-md-12 fw-bold text-success'),
            ),
        )

class AnexarReciboRetiradaForm(forms.ModelForm):
    class Meta:
        model = RetiradaPeca
        fields = ['arquivo_recibo']
        labels = {
            'arquivo_recibo': 'Anexar PDF Assinado'
        }
        help_texts = {
            'arquivo_recibo': 'Selecione o arquivo PDF ou imagem do recibo escaneado.'
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('arquivo_recibo', css_class='col-12'),
            ),
        )

class RetiradaPecaItemForm(forms.ModelForm):
    class Meta:
        model = RetiradaPecaItem
        fields = ['peca', 'quantidade']
        widgets = {
            'peca': forms.Select(attrs={'class': 'select2 peca-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'quantidade-input', 'min': 1}),
        }

    def clean(self):
        cleaned_data = super().clean()
        peca = cleaned_data.get('peca')
        quantidade = cleaned_data.get('quantidade')
        
        if peca and quantidade:
            if not self.instance.pk: # apenas nova retirada valida estoque assim
                if peca.quantidade_estoque < quantidade:
                    self.add_error('quantidade', f'Estoque insuficiente. Disponível: {peca.quantidade_estoque}')
            # Se for edição, a validação é mais complexa e por simplicidade vamos deixar como está
        return cleaned_data

RetiradaPecaItemFormSet = inlineformset_factory(
    RetiradaPeca, 
    RetiradaPecaItem, 
    form=RetiradaPecaItemForm, 
    extra=1, 
    can_delete=True
)

