from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from django.contrib.auth.models import User
from materiais.models import Material
from policiais.models import Policial
from .models import LoteMunicao, RetiradaMunicao, DevolucaoMunicao, DevolucaoCPI


class LoteMunicaoForm(forms.ModelForm):
    class Meta:
        model = LoteMunicao
        fields = ['material', 'calibre', 'marca', 'numero_lote', 'tipo_municao', 'data_fabricacao', 'data_validade', 'quantidade_inicial', 'quantidade_atual', 'ativo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['material'].queryset = Material.objects.filter(tipo='MUNICAO')
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'material',
            'calibre',
            'marca',
            'numero_lote',
            'tipo_municao',
            'data_fabricacao',
            'data_validade',
            'quantidade_inicial',
            'quantidade_atual',
            'ativo',
            Submit('submit', _('Salvar lote'))
        )


class RetiradaMunicaoForm(forms.ModelForm):
    class Meta:
        model = RetiradaMunicao
        fields = ['policial', 'material', 'lote', 'quantidade', 'tipo_uso', 'finalidade', 'local_uso', 'observacoes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['material'].queryset = Material.objects.filter(tipo='MUNICAO')
        # Queryset restrito para validação; o widget usa Select2 AJAX para a busca interativa
        self.fields['policial'].queryset = Policial.objects.filter(situacao='ATIVO')
        self.fields['policial'].widget = forms.Select(attrs={
            'class': 'form-select select2-policial-ajax',
            'data-placeholder': 'Digite o nome ou RE do policial...',
            'data-allow-clear': 'true',
        })
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'policial',
            'material',
            'lote',
            'quantidade',
            'tipo_uso',
            'finalidade',
            'local_uso',
            'observacoes',
            Submit('submit', _('Registrar retirada'))
        )


class DevolucaoMunicaoForm(forms.ModelForm):
    class Meta:
        model = DevolucaoMunicao
        fields = ['retirada', 'quantidade', 'estado_devolucao', 'observacoes']

    disparos = forms.IntegerField(label=_('Disparos'), min_value=0, required=False, initial=0)
    estojos = forms.IntegerField(label=_('Estojos Vazios Devolvidos'), min_value=0, required=False, initial=0)
    estojos_extraviados = forms.IntegerField(label=_('Estojos Extraviados (Treinamento)'), min_value=0, required=False, initial=0)
    extravios = forms.IntegerField(label=_('Cartuchos Intactos Extraviados'), min_value=0, required=False, initial=0)
    justificativa = forms.CharField(label=_('Justificativa'), required=False, widget=forms.Textarea(attrs={'rows': 3}))
    sindicancia = forms.CharField(
        label=_('Sindicância / Apuração'),
        required=False,
        max_length=120,
        help_text=_('Preencha quando houver perda de munições intactas ou perda de estojos em instrução.')
    )
    boletim_ocorrencia = forms.CharField(label=_('B.O. / Relatório de Tiro'), required=False, max_length=100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['retirada'].queryset = RetiradaMunicao.objects.filter().order_by('-data_hora')
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'retirada',
            'quantidade',
            'estado_devolucao',
            'disparos',
            'estojos',
            'estojos_extraviados',
            'extravios',
            'justificativa',
            'sindicancia',
            'boletim_ocorrencia',
            'observacoes',
            Submit('submit', _('Registrar devolução'))
        )

    def clean(self):
        cleaned_data = super().clean()
        retirada = cleaned_data.get('retirada')
        quantidade = cleaned_data.get('quantidade')
        disparos = cleaned_data.get('disparos') or 0
        extravios = cleaned_data.get('extravios') or 0
        estojos = cleaned_data.get('estojos') or 0
        estojos_extraviados = cleaned_data.get('estojos_extraviados') or 0
        justificativa = cleaned_data.get('justificativa', '').strip()
        sindicancia = cleaned_data.get('sindicancia', '').strip()
        boletim_ocorrencia = cleaned_data.get('boletim_ocorrencia', '').strip()

        if retirada and quantidade is not None:
            if quantidade > retirada.quantidade_pendente:
                self.add_error('quantidade', _('A quantidade não pode exceder o pendente da retirada selecionada.'))
            
            if disparos + extravios > quantidade:
                self.add_error('quantidade', _('A soma de disparos e cartuchos extraviados não pode passar da quantidade total devolvida.'))
            
            if estojos > disparos:
                self.add_error('estojos', _('Estojos devolvidos não podem ser maiores que a quantidade disparada.'))

            if retirada.tipo_uso == 'INSTRUCAO':
                # Em instrução, todo disparo deve ser convertido em estojo devolvido ou estojo perdido (extraviado)
                if disparos != (estojos + estojos_extraviados):
                    self.add_error('estojos_extraviados', _('Para Instrução, a soma de Estojos Devolvidos e Estojos Extraviados deve ser exatamente igual à Quantidade Disparada.'))
                
                if estojos_extraviados > 0 and not justificativa:
                    self.add_error('justificativa', _('Informe uma justificativa detalhando a perda/danificação de estojos em instrução.'))
            else:  # OPERACIONAL
                if estojos_extraviados > 0:
                    self.add_error('estojos_extraviados', _('Uso Operacional não gera controle de estojos extraviados.'))

            if extravios > 0:
                if not justificativa:
                    self.add_error('justificativa', _('Informe uma justificativa detalhada para o extravio de munições intactas.'))
                if not sindicancia:
                    self.add_error('sindicancia', _('Para extravio de munição intacta, informe o número da sindicância/procedimento de apuração.'))

            if (disparos > 0 or extravios > 0 or estojos_extraviados > 0) and not justificativa:
                self.add_error('justificativa', _('Informe justificativa detalhada sempre que houver disparos, perdas de cartuchos ou estojos.'))

            if disparos > 0 and not boletim_ocorrencia:
                self.add_error('boletim_ocorrencia', _('Informe o B.O. ou Relatório de Disparo/Instrução.'))

        return cleaned_data


class DevolucaoCPIForm(forms.ModelForm):
    class Meta:
        model = DevolucaoCPI
        fields = ['lote', 'tipo_item', 'quantidade', 'documento_referencia', 'observacoes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lote'].queryset = LoteMunicao.objects.filter(ativo=True).order_by('material__nome', 'numero_lote')
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'lote',
            'tipo_item',
            'quantidade',
            'documento_referencia',
            'observacoes',
            Submit('submit', _('Registrar devolução ao CPI'))
        )


class RelatorioMunicoesForm(forms.Form):
    data_inicio = forms.DateField(label='Data inicial', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    data_fim = forms.DateField(label='Data final', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    material = forms.ModelChoiceField(
        label='Material',
        queryset=Material.objects.filter(tipo='MUNICAO').order_by('nome'),
        required=False
    )
    lote = forms.ModelChoiceField(
        label='Lote',
        queryset=LoteMunicao.objects.filter(ativo=True).order_by('material__nome', 'numero_lote'),
        required=False
    )
    policial = forms.ModelChoiceField(
        label='Policial',
        queryset=Policial.objects.filter(situacao='ATIVO').order_by('nome'),
        required=False
    )
    tipo_item_cpi = forms.ChoiceField(
        label='Tipo de devolução CPI',
        required=False,
        choices=[('', 'Todos'), ('CARTUCHO', 'Cartucho intacto'), ('ESTOJO', 'Estojo vazio')]
    )
    somente_com_extravio = forms.BooleanField(label='Somente com extravio', required=False)
    somente_pendentes = forms.BooleanField(label='Somente retiradas pendentes', required=False)
