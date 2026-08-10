from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.http import HttpResponse
import datetime
import logging

from materiais.models import Material
from movimentacoes.models import Movimentacao
from policiais.models import Policial
from relatorios.models import Relatorio
from reserva_baep.decorators import require_module_permission

logger = logging.getLogger(__name__)

@login_required
@require_module_permission('reserva_armas')
def dashboard(request):
    # Estatísticas de materiais
    total_materiais = Material.objects.count()
    materiais_disponiveis = Material.objects.filter(status='DISPONIVEL').count()
    materiais_em_uso = Material.objects.filter(status='EM_USO').count()
    materiais_manutencao = Material.objects.filter(status='MANUTENCAO').count()
    
    # Estatísticas de policiais
    total_policiais = Policial.objects.count()
    policiais_ativos = Policial.objects.filter(situacao='ATIVO').count()
    
    # Estatísticas de movimentações
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)
    
    movimentacoes_hoje = Movimentacao.objects.filter(data_hora__date=hoje).count()
    retiradas_hoje = Movimentacao.objects.filter(data_hora__date=hoje, tipo='RETIRADA').count()
    devolucoes_hoje = Movimentacao.objects.filter(data_hora__date=hoje, tipo='DEVOLUCAO').count()
    
    movimentacoes_mes = Movimentacao.objects.filter(data_hora__date__gte=inicio_mes).count()
    retiradas_mes = Movimentacao.objects.filter(data_hora__date__gte=inicio_mes, tipo='RETIRADA').count()
    devolucoes_mes = Movimentacao.objects.filter(data_hora__date__gte=inicio_mes, tipo='DEVOLUCAO').count()
    
    # Últimas movimentações
    ultimas_movimentacoes = Movimentacao.objects.all().order_by('-data_hora')[:10]
    
    # Materiais mais movimentados no mês
    materiais_mais_movimentados = Material.objects.annotate(
        total_movimentacoes=Count('movimentacoes', filter=Q(movimentacoes__data_hora__date__gte=inicio_mes))
    ).filter(total_movimentacoes__gt=0).order_by('-total_movimentacoes')[:5]
    
    # Policiais com mais retiradas no mês
    policiais_mais_retiradas = Policial.objects.annotate(
        total_retiradas=Count('movimentacoes', filter=Q(
            movimentacoes__tipo='RETIRADA',
            movimentacoes__data_hora__date__gte=inicio_mes
        ))
    ).filter(total_retiradas__gt=0).order_by('-total_retiradas')[:5]
    
    # Últimos relatórios gerados
    ultimos_relatorios = Relatorio.objects.all().order_by('-data_geracao')[:5]
    
    context = {
        'total_materiais': total_materiais,
        'materiais_disponiveis': materiais_disponiveis,
        'materiais_em_uso': materiais_em_uso,
        'materiais_manutencao': materiais_manutencao,
        'total_policiais': total_policiais,
        'policiais_ativos': policiais_ativos,
        'movimentacoes_hoje': movimentacoes_hoje,
        'retiradas_hoje': retiradas_hoje,
        'devolucoes_hoje': devolucoes_hoje,
        'movimentacoes_mes': movimentacoes_mes,
        'retiradas_mes': retiradas_mes,
        'devolucoes_mes': devolucoes_mes,
        'ultimas_movimentacoes': ultimas_movimentacoes,
        'materiais_mais_movimentados': materiais_mais_movimentados,
        'policiais_mais_retiradas': policiais_mais_retiradas,
        'ultimos_relatorios': ultimos_relatorios,
        'hoje': hoje,
        'inicio_mes': inicio_mes,
    }
    
    return render(request, 'dashboard.html', context)

def home(request):
    if request.user.is_authenticated:
        return render(request, 'modulo_dashboard.html')
    return redirect('usuarios:login')

def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    """
    Handler de erro 500 que usa template standalone sem extends base.html.
    Isso garante que a página de erro seja exibida mesmo que o erro tenha
    ocorrido no próprio template base ou em um context_processor.
    """
    logger.error(
        'HTTP 500 — Erro interno não tratado. Path: %s | User: %s',
        getattr(request, 'path', 'unknown'),
        getattr(request, 'user', 'unknown'),
    )
    try:
        return render(request, '500.html', status=500)
    except Exception:
        # Fallback absoluto: retorna HTML puro sem nenhum template engine
        html = (
            '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Erro 500</title></head>'
            '<body style="font-family:sans-serif;text-align:center;padding:60px;background:#0f172a;color:#f1f5f9;">'
            '<h1 style="font-size:4rem;color:#ef4444;">500</h1>'
            '<p>Erro interno do servidor. <a href="/" style="color:#60a5fa;">Voltar ao início</a></p>'
            '</body></html>'
        )
        return HttpResponse(html, status=500, content_type='text/html; charset=utf-8')

def handler403(request, exception):
    return render(request, '403.html', status=403)

def handler400(request, exception):
    return render(request, '400.html', status=400)

def ajuda(request):
    return render(request, 'ajuda.html')

def termos(request):
    return render(request, 'termos.html')

def privacidade(request):
    return render(request, 'privacidade.html')

def sobre(request):
    return render(request, 'sobre.html')

def manutencao(request):
    return render(request, 'manutencao.html')