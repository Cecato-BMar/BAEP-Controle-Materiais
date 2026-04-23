"""
Views for config (root URLconf)
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


def home(request):
    """Home page - redirect based on auth status"""
    if request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect('dashboard')
    return render(request, 'pages/home.html')


@login_required
def dashboard(request):
    """Main dashboard"""
    return render(request, 'pages/dashboard.html')


# Error handlers
def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    return render(request, 'errors/500.html', status=500)


def handler403(request, exception):
    return render(request, 'errors/403.html', status=403)


def handler400(request, exception):
    return render(request, 'errors/400.html', status=400)