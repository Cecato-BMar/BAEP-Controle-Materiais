"""
Views for core app
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

User = get_user_model()


class AppLoginView(LoginView):
    """Custom login view"""
    template_name = 'core/login.html'
    redirect_authenticated_user = True


class AppLogoutView(LogoutView):
    """Custom logout view"""
    next_page = reverse_lazy('login')


def home(request):
    """Home page"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


@login_required
def dashboard(request):
    """Main dashboard"""
    context = {
        'user': request.user,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def perfil(request):
    """User profile view"""
    return render(request, 'core/perfil.html', {'user': request.user})


@login_required
def perfil_editar(request):
    """Edit user profile"""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.telefone = request.POST.get('telefone', '')
        user.save()
        messages.success(request, 'Perfil atualizado com sucesso!')
        return redirect('core:perfil')
    return render(request, 'core/perfil_form.html')


@login_required
def alterar_senha(request):
    """Change password view - uses Django's built-in"""
    from django.contrib.auth.views import PasswordChangeView
    from django.urls import reverse_lazy
    
    class CustomPasswordChangeView(PasswordChangeView):
        success_url = reverse_lazy('core:perfil')
        template_name = 'core/password_change.html'
    
    return CustomPasswordChangeView.as_view()(request)