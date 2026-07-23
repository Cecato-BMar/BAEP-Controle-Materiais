"""
Sincronização Reversa: Reserva de Armas (materiais.Material) → Material Bélico.

Quando o status de um Material é atualizado (por retirada, devolução, etc.),
este módulo propaga a mudança para o modelo correspondente no material_belico.

Prevenção de loop: usa threading.local() para evitar que o signal do
material_belico dispare o signal do materiais, e vice-versa.
"""
import logging
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger('django')

# ============================================================================
# PREVENÇÃO DE LOOPS — compartilhado entre os dois módulos
# ============================================================================
_sync_lock = threading.local()


def is_syncing():
    """Retorna True se já estamos dentro de uma operação de sync."""
    return getattr(_sync_lock, 'active', False)


def set_syncing(value):
    """Ativa/desativa o flag de sync na thread atual."""
    _sync_lock.active = value


# ============================================================================
# MAPEAMENTO DE STATUS:  materiais.Material → material_belico
# ============================================================================

# Mapa por (tipo, categoria) → (modelo_belico, campo_lookup, campo_status, mapa_status)
# Cada entrada define como encontrar e atualizar o item correspondente.

def _get_model_config():
    """Retorna o mapeamento lazy para evitar imports circulares."""
    from material_belico.models import (
        Fuzil, EspingardaCal12, PistolaGlock, PistolaTaurus,
        RadioHT, AM640, TASER,
        ColeteBalistico, EscudoBalistico, CapaceteBalistico,
    )

    # Mapas de status reverso: Material.status → valor do campo no material_belico
    STATUS_ARMA = {
        'DISPONIVEL': 'OK',
        'EM_USO': 'EM_USO',
        'MANUTENCAO': 'MANUTENCAO',
        'BAIXADO': 'BAIXADO',
        'APREENDIDO': 'SINDICANCIA',
    }

    STATUS_ESPINGARDA = {
        'DISPONIVEL': 'OK',
        'EM_USO': 'EM_USO',
        'MANUTENCAO': 'MANUTENCAO',
        'BAIXADO': 'BAIXADO',
        'APREENDIDO': 'BAIXADO',
    }

    STATUS_GLOCK = {
        'DISPONIVEL': 'ok',
        'EM_USO': 'EM_USO',
        'MANUTENCAO': 'ok',
        'BAIXADO': 'ok',
        'APREENDIDO': 'APREENDIDA',
    }

    STATUS_RADIO = {
        'DISPONIVEL': 'OP',
        'EM_USO': 'EM_USO',
        'MANUTENCAO': 'MANUTENCAO',
        'BAIXADO': 'MANUTENCAO',
        'APREENDIDO': 'MANUTENCAO',
    }

    STATUS_AM640 = {
        'DISPONIVEL': 'RESERVA',
        'EM_USO': 'EM_USO',
        'MANUTENCAO': 'RESERVA',
        'BAIXADO': 'BAIXADO',
        'APREENDIDO': 'BAIXADO',
    }

    STATUS_TASER = {
        'DISPONIVEL': 'RESERVA',
        'EM_USO': 'EM USO',
        'MANUTENCAO': 'MANUTENCAO',
        'BAIXADO': 'BAIXADO',
        'APREENDIDO': 'BAIXADO',
    }

    STATUS_COLETE = {
        'DISPONIVEL': 'DISPONIVEL',
        'EM_USO': 'EM_USO',
        'MANUTENCAO': 'SINDICANCIA',
        'BAIXADO': 'SINDICANCIA',
        'APREENDIDO': 'SINDICANCIA',
    }

    STATUS_ESCUDO = {
        'DISPONIVEL': 'OP',
        'EM_USO': 'EM_USO',
        'MANUTENCAO': 'BXA',
        'BAIXADO': 'BXA',
        'APREENDIDO': 'BXA',
    }

    STATUS_CAPACETE = {
        'DISPONIVEL': 'OPERANDO',
        'EM_USO': 'EM_USO',
        'MANUTENCAO': 'DANIFICADO',
        'BAIXADO': 'DANIFICADO',
        'APREENDIDO': 'DANIFICADO',
    }

    return [
        # (modelo, campo_lookup, campo_status, mapa_status, tipo_material, categoria_material)
        (Fuzil, 'patrimonio', 'status', STATUS_ARMA, 'ARMA', 'FUZIL'),
        (EspingardaCal12, 'numero_espingarda', 'status', STATUS_ESPINGARDA, 'ARMA', 'CAL_12'),
        (PistolaGlock, 'numero_serie', 'situacao_reserva', STATUS_GLOCK, 'ARMA', 'PISTOLA'),
        (PistolaTaurus, 'numero_serie', None, None, 'ARMA', 'PISTOLA'),  # Sem campo status
        (TASER, 'serie', 'situacao', STATUS_TASER, 'ARMA', 'CHOQUE'),
        (AM640, 'serie', 'situacao', STATUS_AM640, 'ARMA', 'LANCADOR'),
        (RadioHT, 'serie', 'situacao', STATUS_RADIO, 'RADIO', None),
        (ColeteBalistico, 'numero_serie', 'situacao', STATUS_COLETE, 'COLETE', None),
        (EscudoBalistico, 'numero', 'situacao', STATUS_ESCUDO, 'OUTROS', 'OUTROS'),
        (CapaceteBalistico, 'numero', 'condicao', STATUS_CAPACETE, 'OUTROS', 'OUTROS'),
    ]


def _buscar_item_belico(material):
    """
    Dado um objeto Material, encontra o item correspondente no material_belico.
    Retorna (instancia, campo_status, mapa_status) ou (None, None, None).
    """
    configs = _get_model_config()

    for modelo, campo_lookup, campo_status, mapa_status, tipo_esperado, cat_esperada in configs:
        # Filtro rápido por tipo/categoria
        if tipo_esperado and material.tipo != tipo_esperado:
            continue
        if cat_esperada and material.categoria != cat_esperada:
            continue
        # Sem campo de status: nada a sincronizar
        if campo_status is None:
            continue

        # Monta o filtro de lookup
        lookup = {campo_lookup: material.numero}
        # EscudoBalistico e CapaceteBalistico usam IntegerField → converter
        if campo_lookup == 'numero':
            try:
                lookup[campo_lookup] = int(material.numero)
            except (ValueError, TypeError):
                continue

        try:
            item = modelo.objects.get(**lookup)
            return item, campo_status, mapa_status
        except modelo.DoesNotExist:
            continue
        except modelo.MultipleObjectsReturned:
            item = modelo.objects.filter(**lookup).first()
            if item:
                return item, campo_status, mapa_status

    return None, None, None


def sync_material_to_belico(material):
    """
    Sincroniza o status de um Material para o item correspondente no material_belico.
    Chamado via signal post_save ou diretamente após uma operação de retirada/devolução.
    """
    if is_syncing():
        return

    item, campo_status, mapa_status = _buscar_item_belico(material)
    if item is None:
        return

    novo_status = mapa_status.get(material.status)
    if novo_status is None:
        return

    status_atual = getattr(item, campo_status)
    if status_atual == novo_status:
        return  # Já está correto, nada a fazer

    try:
        set_syncing(True)
        setattr(item, campo_status, novo_status)
        item.save(update_fields=[campo_status, 'data_atualizacao'])
        logger.info(
            f"[SYNC REVERSA] {item.__class__.__name__} "
            f"({material.numero}): {campo_status} {status_atual} → {novo_status}"
        )
    except Exception as exc:
        logger.error(f"[SYNC REVERSA] Erro ao sincronizar {material.numero}: {exc}")
    finally:
        set_syncing(False)


# ============================================================================
# SIGNAL: post_save de Material → sync reversa para material_belico
# ============================================================================

@receiver(post_save, sender='materiais.Material')
def on_material_save(sender, instance, **kwargs):
    """Quando Material é salvo, propaga status para material_belico."""
    sync_material_to_belico(instance)
