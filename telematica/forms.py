from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Field, HTML, Div
from .models import (Equipamento, CategoriaEquipamento, ConfiguracaoRadio, 
                     LinhaMovel, ServicoTI, ManutencaoTI)

class CategoriaEquipamentoForm(forms.ModelForm):
    class Meta:
        model = CategoriaEquipamento
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('nome', css_class='col-md-6'), Column('icone', css_class='col-md-6')),
            'descricao',
            Submit('submit', 'Salvar Categoria', css_class='btn btn-primary mt-2'),
        )

class EquipamentoForm(forms.ModelForm):
    class Meta:
        model = Equipamento
        exclude = ['registrado_por', 'data_cadastro', 'data_atualizacao']
        widgets = {
            'data_aquisicao': forms.DateInput(attrs={'type': 'date'}),
            'vencimento_garantia': forms.DateInput(attrs={'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h5 class="text-primary mb-3">Informações Gerais</h5>'),
            Row(Column('categoria', css_class='col-md-4'), Column('marca', css_class='col-md-4'), Column('modelo', css_class='col-md-4')),
            Row(Column('numero_serie', css_class='col-md-6'), Column('patrimonio', css_class='col-md-6')),
            
            HTML('<h5 class="text-primary mt-4 mb-3">Especificações de Hardware & SO</h5>'),
            Row(Column('processador', css_class='col-md-6'), Column('memoria_ram', css_class='col-md-3'), Column('armazenamento', css_class='col-md-3')),
            Row(Column('sistema_operacional', css_class='col-md-12')),
            
            HTML('<h5 class="text-primary mt-4 mb-3">Rede e Localização</h5>'),
            Row(Column('hostname', css_class='col-md-4'), Column('endereco_ip', css_class='col-md-4'), Column('endereco_mac', css_class='col-md-4')),
            Row(Column('vlan', css_class='col-md-3'), Column('porta_switch', css_class='col-md-3'), Column('setor', css_class='col-md-3'), Column('usuario_responsavel', css_class='col-md-3')),
            
            HTML('<h5 class="text-primary mt-4 mb-3">Status e Datas</h5>'),
            Row(Column('status', css_class='col-md-4'), Column('data_aquisicao', css_class='col-md-4'), Column('vencimento_garantia', css_class='col-md-4')),
            'observacoes',
            Submit('submit', 'Salvar Equipamento', css_class='btn btn-primary btn-lg mt-3'),
        )

class ConfiguracaoRadioForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoRadio
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'equipamento',
            Row(Column('issi', css_class='col-md-6'), Column('tei', css_class='col-md-6')),
            'grupo_principal',
            Row(Column('criptografia_ativa', css_class='col-md-6 pt-4'), Column('versao_firmware', css_class='col-md-6')),
            Submit('submit', 'Salvar Configuração', css_class='btn btn-success mt-2'),
        )

class LinhaMovelForm(forms.ModelForm):
    class Meta:
        model = LinhaMovel
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('numero', css_class='col-md-6'), Column('operadora', css_class='col-md-6')),
            Row(Column('iccid', css_class='col-md-12')),
            Row(Column('imei_1', css_class='col-md-6'), Column('imei_2', css_class='col-md-6')),
            Row(Column('plano_dados', css_class='col-md-6'), Column('ativo', css_class='col-md-6 pt-4')),
            Row(Column('equipamento_vinculado', css_class='col-md-6'), Column('policial_responsavel', css_class='col-md-6')),
            Submit('submit', 'Salvar Linha', css_class='btn btn-info mt-2'),
        )

class ServicoTIForm(forms.ModelForm):
    class Meta:
        model = ServicoTI
        fields = '__all__'
        widgets = {
            'vencimento': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(Column('nome', css_class='col-md-8'), Column('tipo', css_class='col-md-4')),
            'fornecedor',
            'descricao',
            Row(Column('numero_contrato', css_class='col-md-6'), Column('vencimento', css_class='col-md-6')),
            Row(Column('ip_publico', css_class='col-md-6'), Column('velocidade', css_class='col-md-4'), Column('status', css_class='col-md-2 pt-4')),
            Submit('submit', 'Salvar Serviço', css_class='btn btn-primary mt-2'),
        )

class ManutencaoTIForm(forms.ModelForm):
    class Meta:
        model = ManutencaoTI
        exclude = ['registrado_por']
        widgets = {
            'data_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'data_fim': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descricao_problema': forms.Textarea(attrs={'rows': 3}),
            'solucao_tecnica': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'equipamento',
            Row(Column('tipo', css_class='col-md-6'), Column('tecnico_responsavel', css_class='col-md-6')),
            Row(Column('data_inicio', css_class='col-md-6'), Column('data_fim', css_class='col-md-6')),
            'descricao_problema',
            'solucao_tecnica',
            Row(Column('custo', css_class='col-md-6'), Column('concluida', css_class='col-md-6 pt-4')),
            Submit('submit', 'Registrar Manutenção', css_class='btn btn-warning mt-2'),
        )
