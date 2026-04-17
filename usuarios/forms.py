from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div
from .models import Perfil
from policiais.models import Policial

class GroupMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        labels = {
            'reserva_armas': 'Reserva de Armas (Tático)',
            'materiais': 'Estoque e Materiais (MATERIAL DE CONSUMO)',
            'administracao': 'Administração do Sistema',
            'frota': 'Gestão de Frota (VTRs)',
            'patrimonio': 'Gestão de Patrimônio'
        }
        return labels.get(obj.name, obj.name.replace('_', ' ').title())

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'username',
            'password',
            Div(
                Submit('submit', _('Entrar'), css_class='btn btn-primary'),
                css_class='text-center'
            )
        )

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(label=_('Nome'), max_length=30, required=True)
    last_name = forms.CharField(label=_('Sobrenome'), max_length=150, required=True)
    modulos = GroupMultipleChoiceField(queryset=Group.objects.all(), widget=forms.CheckboxSelectMultiple, required=False, label=_('Módulos de Acesso'))
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'modulos', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'username',
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-0'),
                Column('last_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'email',
            'modulos',
            'password1',
            'password2',
            Div(
                Submit('submit', _('Registrar'), css_class='btn btn-primary'),
                css_class='text-center'
            )
        )

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ('policial', 'nivel_acesso', 'telefone')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        
        # Filtra apenas policiais ativos que não estão associados a outros perfis
        policiais_disponiveis = Policial.objects.filter(situacao='ATIVO')
        if self.instance and self.instance.policial:
            # Inclui o policial atual do perfil na lista de opções
            policiais_disponiveis = policiais_disponiveis | Policial.objects.filter(pk=self.instance.policial.pk)
        
        self.fields['policial'].queryset = policiais_disponiveis
        self.fields['policial'].required = False
        
        self.helper.layout = Layout(
            'policial',
            'nivel_acesso',
            'telefone',
            Div(
                Submit('submit', _('Salvar'), css_class='btn btn-primary'),
                css_class='text-center'
            )
        )

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    modulos = GroupMultipleChoiceField(queryset=Group.objects.all(), widget=forms.CheckboxSelectMultiple, required=False, label=_('Módulos de Acesso'))
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'modulos')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].disabled = True
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-0'),
                Column('last_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'email',
            'modulos',
            Div(
                Submit('submit', _('Atualizar'), css_class='btn btn-primary'),
                css_class='text-center'
            )
        )

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'old_password',
            'new_password1',
            'new_password2',
            Div(
                Submit('submit', _('Alterar Senha'), css_class='btn btn-primary'),
                css_class='text-center'
            )
        )