from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch

from .models import ModuloTutorial, SecaoTutorial


@login_required
def index(request):
    """Página inicial do tutorial: cards de todos os módulos publicados."""
    modulos = []

    def modulo_total_publicado(m):
        return m.secoes.filter(publicado=True).count()

    for m in ModuloTutorial.objects.filter(publicado=True):
        modulos.append({
            'obj': m,
            'total_secoes': modulo_total_publicado(m),
            'permitido': _usuario_pode_ver(request.user, m.grupo),
        })
    modulos.sort(key=lambda x: (x['obj'].ordem, x['obj'].nome))

    context = {
        'modulos': modulos,
        'total_modulos': len(modulos),
        'total_secoes': SecaoTutorial.objects.filter(publicado=True).count(),
    }
    return render(request, 'tutorial/index.html', context)


@login_required
def detalhe_modulo(request, slug):
    """Detalhe de um módulo do tutorial com navegação lateral por seções."""
    modulo = get_object_or_404(ModuloTutorial, slug=slug, publicado=True)

    secoes = (modulo.secoes.filter(publicado=True)
              .order_by('ordem', 'id'))

    # Módulos publicados para navegação anterior/próximo
    modulos_lista = list(ModuloTutorial.objects
                         .filter(publicado=True).order_by('ordem', 'nome'))
    idx = next((i for i, m in enumerate(modulos_lista) if m.pk == modulo.pk), None)
    modulo_anterior = modulos_lista[idx - 1] if idx and idx > 0 else None
    modulo_proximo = modulos_lista[idx + 1] if idx is not None and idx < len(modulos_lista) - 1 else None

    context = {
        'modulo': modulo,
        'secoes': secoes,
        'modulo_anterior': modulo_anterior,
        'modulo_proximo': modulo_proximo,
        'total_modulos': len(modulos_lista),
        'idx_modulo': (idx + 1) if idx is not None else 0,
    }
    return render(request, 'tutorial/modulo.html', context)


def _usuario_pode_ver(user, grupo):
    """Indica se o usuário logado normalmente tem acesso ao módulo do sistema.
    Não bloqueia a leitura do tutorial, apenas orienta na apresentação."""
    if not grupo:
        return True
    if user.is_superuser:
        return True
    return user.groups.filter(name=grupo).exists()