from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .license_core import LicenseManager
from .models import LicenseRecord
import datetime

@login_required
def bloqueado(request):
    status_info = LicenseManager.get_current_license_status()
    
    # Se a licença estiver válida ou se for o usuário master, não tem porque estar aqui
    if status_info['status'] in ['VALID', 'GRACE_PERIOD'] or request.user.username == 'master':
        return redirect('home')
        
    return render(request, 'licenciamento/bloqueado.html', {'status_info': status_info})

@login_required
def ativar_licenca(request):
    if not request.user.is_superuser:
        messages.error(request, "Apenas administradores podem ativar licenças.")
        return redirect('home')
        
    if request.method == 'POST':
        token = request.POST.get('token')
        if token:
            is_valid, payload = LicenseManager.verify_token(token)
            
            if is_valid or payload: # Mesmo se expirado, verificamos se a assinatura é válida
                if payload:
                    # Inativa licenças antigas
                    LicenseRecord.objects.all().update(is_active=False)
                    
                    # Cria nova
                    expires_at = datetime.datetime.fromtimestamp(payload['exp'], tz=datetime.timezone.utc)
                    issued_at = datetime.datetime.fromtimestamp(payload['iat'], tz=datetime.timezone.utc)
                    
                    LicenseRecord.objects.create(
                        client_id=payload.get('client_id'),
                        client_name=payload.get('client_name'),
                        token_base64=token,
                        issued_at=issued_at,
                        expires_at=expires_at,
                        is_active=True
                    )
                    
                    if is_valid:
                        messages.success(request, "Licença ativada com sucesso!")
                        return redirect('home')
                    else:
                        messages.warning(request, "Licença ativada, mas já encontra-se no período expirado/tolerância.")
                        return redirect('licenciamento:bloqueado')
            
            messages.error(request, "Token inválido ou corrompido.")
            
    return render(request, 'licenciamento/ativar.html')

@login_required
def panel_master(request):
    # Restrição rígida: apenas o usuário 'master' ou superusuário com nome específico pode entrar
    if request.user.username != 'master' and not request.user.is_superuser:
        messages.error(request, "Acesso restrito ao desenvolvedor Master.")
        return redirect('home')

    generated_token = None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate':
            client_id = request.POST.get('client_id', 'baep-cliente')
            client_name = request.POST.get('client_name', '2º BAEP')
            days = int(request.POST.get('days', 7))
            
            generated_token = LicenseManager.generate_token(client_id, client_name, days)
            messages.success(request, f"Token para {client_name} gerado com sucesso!")
            
        elif action == 'activate':
            token = request.POST.get('token')
            if token:
                is_valid, payload = LicenseManager.verify_token(token)
                if is_valid or payload:
                    LicenseRecord.objects.all().update(is_active=False)
                    expires_at = datetime.datetime.fromtimestamp(payload['exp'], tz=datetime.timezone.utc)
                    issued_at = datetime.datetime.fromtimestamp(payload['iat'], tz=datetime.timezone.utc)
                    
                    LicenseRecord.objects.create(
                        client_id=payload.get('client_id'),
                        client_name=payload.get('client_name'),
                        token_base64=token,
                        issued_at=issued_at,
                        expires_at=expires_at,
                        is_active=True
                    )
                    messages.success(request, "Sistema autenticado e liberado com sucesso!")
                    return redirect('home')
                messages.error(request, "Token inválido.")

    return render(request, 'licenciamento/panel_master.html', {
        'generated_token': generated_token,
        'status_info': LicenseManager.get_current_license_status()
    })
