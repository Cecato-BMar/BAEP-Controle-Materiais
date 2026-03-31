from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from reserva_baep.decorators import require_module_permission, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Perfil
from .forms import (
    CustomAuthenticationForm, UserRegistrationForm, PerfilForm,
    UserUpdateForm, CustomPasswordChangeForm
)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Atualiza a data do último acesso
                try:
                    perfil = user.perfil
                    perfil.data_ultimo_acesso = timezone.now()
                    perfil.save()
                except Perfil.DoesNotExist:
                    pass
                
                # Redireciona para a página solicitada ou para o dashboard
                next_page = request.GET.get('next')
                return redirect('home')
        else:
            messages.error(request, _('Nome de usuário ou senha inválidos.'))
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'usuarios/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, _('Você saiu do sistema com sucesso.'))
    return redirect('usuarios:login')

# Verifica se o usuário é administrador
def is_admin(user):
    return user.is_superuser or (hasattr(user, 'perfil') and user.perfil.nivel_acesso == 'ADMIN')

@login_required
@require_module_permission('administracao')
def registro_usuario(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        perfil_form = PerfilForm(request.POST)
        
        if form.is_valid() and perfil_form.is_valid():
            # Cria o usuário
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.save()
            
            # Adiciona os módulos (grupos) selecionados
            modulos = form.cleaned_data.get('modulos')
            if modulos:
                user.groups.set(modulos)
            
            # Atualiza o perfil
            perfil = user.perfil  # O perfil é criado automaticamente pelo sinal post_save
            perfil.nivel_acesso = perfil_form.cleaned_data['nivel_acesso']
            perfil.telefone = perfil_form.cleaned_data['telefone']
            perfil.policial = perfil_form.cleaned_data['policial']
            perfil.save()
            
            messages.success(request, _('Usuário criado com sucesso!'))
            return redirect('usuarios:lista_usuarios')
    else:
        form = UserRegistrationForm()
        perfil_form = PerfilForm()
    
    return render(request, 'usuarios/registro.html', {
        'form': form,
        'perfil_form': perfil_form
    })

@login_required
@require_module_permission('administracao')
def lista_usuarios(request):
    usuarios = User.objects.all().order_by('username')
    
    # Filtragem
    termo_busca = request.GET.get('q')
    if termo_busca:
        usuarios = usuarios.filter(
            Q(username__icontains=termo_busca) | 
            Q(first_name__icontains=termo_busca) | 
            Q(last_name__icontains=termo_busca) | 
            Q(email__icontains=termo_busca)
        )
    
    # Paginação
    paginator = Paginator(usuarios, 20)  # 20 itens por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'usuarios/lista_usuarios.html', {
        'page_obj': page_obj,
        'total_usuarios': usuarios.count(),
    })

@login_required
@require_module_permission('administracao')
def detalhe_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    
    return render(request, 'usuarios/detalhe_usuario.html', {
        'usuario': usuario,
    })

@login_required
@require_module_permission('administracao')
def editar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=usuario)
        perfil_form = PerfilForm(request.POST, instance=usuario.perfil)
        
        if user_form.is_valid() and perfil_form.is_valid():
            user = user_form.save()
            perfil_form.save()
            
            # Atualiza os módulos
            modulos = user_form.cleaned_data.get('modulos')
            if modulos is not None:
                user.groups.set(modulos)
                
            messages.success(request, _('Usuário atualizado com sucesso!'))
            return redirect('usuarios:detalhe_usuario', pk=usuario.pk)
    else:
        user_form = UserUpdateForm(instance=usuario, initial={'modulos': usuario.groups.all()})
        perfil_form = PerfilForm(instance=usuario.perfil)
    
    return render(request, 'usuarios/editar_usuario.html', {
        'user_form': user_form,
        'perfil_form': perfil_form,
        'usuario': usuario
    })

@login_required
def alterar_senha(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Mantém o usuário logado
            messages.success(request, _('Sua senha foi alterada com sucesso!'))
            return redirect('dashboard')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'usuarios/alterar_senha.html', {'form': form})

@login_required
def perfil_usuario(request):
    usuario = request.user
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=usuario)
        perfil_form = PerfilForm(request.POST, instance=usuario.perfil)
        
        if user_form.is_valid() and perfil_form.is_valid():
            user_form.save()
            perfil_form.save()
            messages.success(request, _('Seu perfil foi atualizado com sucesso!'))
            return redirect('usuarios:perfil')
    else:
        user_form = UserUpdateForm(instance=usuario)
        perfil_form = PerfilForm(instance=usuario.perfil)
    
    return render(request, 'usuarios/perfil.html', {
        'form': user_form,
        'perfil_form': perfil_form
    })

@login_required
@require_module_permission('administracao')
def excluir_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    
    # Não permitir que um usuário exclua a si mesmo
    if usuario == request.user:
        messages.error(request, _('Você não pode excluir seu próprio usuário!'))
        return redirect('usuarios:lista_usuarios')
    
    if request.method == 'POST':
        username = usuario.username
        usuario.delete()
        messages.success(request, _(f'Usuário {username} excluído com sucesso!'))
    
    return redirect('usuarios:lista_usuarios')
