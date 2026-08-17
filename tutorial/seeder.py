"""Sincroniza o conteúdo padrão do tutorial no banco de dados.

Roda automaticamente ao final do `migrate` (via app.ready -> post_migrate)
ou manualmente com:  python manage.py seed_tutorial

O processo é idempotente: usa get_or_create e NUNCA sobrescreve edições
feitas pelo administrador no Django Admin.
"""
import logging

from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import ModuloTutorial, SecaoTutorial
from . import content_data

logger = logging.getLogger(__name__)


def seed_tutorial():
    criados_m = novos_s = 0
    for dado_mod in content_data.MODULOS:
        modulo, created = ModuloTutorial.objects.get_or_create(
            slug=dado_mod['slug'],
            defaults={
                'icone': dado_mod.get('icone', 'fa-solid fa-book-open'),
                'nome': dado_mod['nome'],
                'descricao': dado_mod.get('descricao', ''),
                'grupo': dado_mod.get('grupo', ''),
                'ordem': dado_mod.get('ordem', 0),
            },
        )
        if created:
            criados_m += 1
        for i, sec in enumerate(dado_mod.get('secoes', [])):
            _, created_s = SecaoTutorial.objects.get_or_create(
                modulo=modulo,
                titulo=sec['titulo'],
                defaults={
                    'conteudo': sec.get('conteudo', ''),
                    'tipo': sec.get('tipo', 'TEXTO'),
                    'ordem': sec.get('ordem', i),
                },
            )
            if created_s:
                novos_s += 1

    logger.info('Tutorial sincronizado: %d módulos, %d seções novas.',
                criados_m, novos_s)
    return criados_m, novos_s


@receiver(post_migrate)
def _post_migrate_seed(sender, **kwargs):
    """Executa o seed ao final de cada migração do app tutorial."""
    if getattr(sender, 'name', None) != 'tutorial':
        return
    seed_tutorial()