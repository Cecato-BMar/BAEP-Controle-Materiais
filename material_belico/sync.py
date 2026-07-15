from django.db.models.signals import post_save
from django.dispatch import receiver
from materiais.models import Material
from material_belico.models import (
    Fuzil, EspingardaCal12, PistolaGlock, PistolaTaurus, 
    ColeteBalistico, EscudoBalistico, CapaceteBalistico, 
    TASER, RadioHT, AM640
)

def sync_material(numero_serie, nome, tipo, categoria, status_str, observacoes=""):
    """
    Sincroniza um item do material bélico para o módulo de materiais (Reserva de Armas).
    """
    if not numero_serie:
        return

    # Mapeamento de Status Genérico
    # 'ok', 'OK', 'DISPONIVEL' -> 'DISPONIVEL'
    # 'BAIXADO', 'BXA' -> 'BAIXADO'
    # 'SINDICANCIA', 'MANUTENCAO' -> 'MANUTENCAO'
    # 'APREENDIDA' -> 'APREENDIDO'
    
    status_map = {
        'ok': 'DISPONIVEL',
        'op': 'DISPONIVEL',
        'disponivel': 'DISPONIVEL',
        'reserva': 'DISPONIVEL',
        'baixado': 'BAIXADO',
        'bxa': 'BAIXADO',
        'descarga': 'BAIXADO',
        'sindicancia': 'MANUTENCAO',
        'manutencao': 'MANUTENCAO',
        'apreendida': 'APREENDIDO',
        'apreendido': 'APREENDIDO',
    }
    
    status_limpo = str(status_str).lower().strip()
    status_final = status_map.get(status_limpo, 'DISPONIVEL')

    # Garantir que limite de string seja respeitado
    numero = str(numero_serie)[:50]
    nome_final = str(nome)[:100]

    try:
        material = Material.objects.get(numero=numero)
        # Atualiza
        changed = False
        if material.nome != nome_final:
            material.nome = nome_final
            changed = True
        if material.tipo != tipo:
            material.tipo = tipo
            changed = True
        if material.categoria != categoria:
            material.categoria = categoria
            changed = True
        
        # Apenas atualiza o status se for diferente e se nao estiver EM_USO (pois a reserva quem controla o uso real).
        if material.status != 'EM_USO':
            if material.status != status_final:
                material.status = status_final
                changed = True

        if material.observacoes != observacoes:
            material.observacoes = observacoes
            changed = True

        if changed:
            material.save()
            
    except Material.DoesNotExist:
        # Cria novo
        Material.objects.create(
            numero=numero,
            nome=nome_final,
            tipo=tipo,
            categoria=categoria,
            quantidade=1,
            quantidade_disponivel=1,
            quantidade_em_uso=0,
            estado='BOM', # default
            status=status_final,
            observacoes=observacoes
        )

# -- Handlers de Fuzis --
@receiver(post_save, sender=Fuzil)
def sync_fuzil(sender, instance, **kwargs):
    nome = f"{instance.get_tipo_display()}"
    sync_material(
        numero_serie=instance.patrimonio,
        nome=nome,
        tipo='ARMA',
        categoria='FUZIL',
        status_str=instance.status,
        observacoes=instance.observacoes
    )

@receiver(post_save, sender=EspingardaCal12)
def sync_espingarda(sender, instance, **kwargs):
    sync_material(
        numero_serie=instance.numero_espingarda,
        nome="Espingarda Cal.12",
        tipo='ARMA',
        categoria='CAL_12',
        status_str=instance.status,
        observacoes=instance.observacoes
    )

@receiver(post_save, sender=PistolaGlock)
def sync_glock(sender, instance, **kwargs):
    sync_material(
        numero_serie=instance.numero_serie,
        nome=instance.modelo,
        tipo='ARMA',
        categoria='PISTOLA',
        status_str=instance.situacao_reserva,
        observacoes=instance.observacoes
    )

@receiver(post_save, sender=PistolaTaurus)
def sync_taurus(sender, instance, **kwargs):
    sync_material(
        numero_serie=instance.numero_serie,
        nome=instance.get_modelo_display(),
        tipo='ARMA',
        categoria='PISTOLA',
        status_str='OK',  # PistolaTaurus não possui field situacao ativo
        observacoes=instance.observacoes
    )

# -- Equipamentos Não-Letais e Comunicação --
@receiver(post_save, sender=TASER)
def sync_taser(sender, instance, **kwargs):
    sync_material(
        numero_serie=instance.serie,
        nome="TASER",
        tipo='ARMA',
        categoria='CHOQUE',
        status_str=instance.situacao,
        observacoes=instance.observacoes
    )

@receiver(post_save, sender=RadioHT)
def sync_radio(sender, instance, **kwargs):
    sync_material(
        numero_serie=instance.serie,
        nome="Rádio HT APX 2000",
        tipo='RADIO',
        categoria='OUTROS',
        status_str=instance.situacao,
        observacoes=instance.observacoes
    )

@receiver(post_save, sender=AM640)
def sync_am640(sender, instance, **kwargs):
    sync_material(
        numero_serie=instance.serie,
        nome="AM-640",
        tipo='ARMA',
        categoria='LANCADOR',
        status_str=instance.situacao,
        observacoes=""
    )

# -- Coletes e Escudos --
@receiver(post_save, sender=ColeteBalistico)
def sync_colete(sender, instance, **kwargs):
    sync_material(
        numero_serie=instance.numero_serie,
        nome=f"Colete Balístico {instance.get_marca_display()} Tam {instance.tamanho}",
        tipo='COLETE',
        categoria='OUTROS',
        status_str=instance.situacao,
        observacoes=instance.obs
    )

@receiver(post_save, sender=EscudoBalistico)
def sync_escudo(sender, instance, **kwargs):
    sync_material(
        numero_serie=str(instance.numero),
        nome=instance.material,
        tipo='OUTROS',
        categoria='OUTROS',
        status_str=instance.situacao,
        observacoes=instance.numero_serie or ""
    )

@receiver(post_save, sender=CapaceteBalistico)
def sync_capacete(sender, instance, **kwargs):
    sync_material(
        numero_serie=str(instance.numero),
        nome=instance.get_material_display(),
        tipo='OUTROS',
        categoria='OUTROS',
        status_str=instance.condicao,
        observacoes=instance.numero_serie or ""
    )
