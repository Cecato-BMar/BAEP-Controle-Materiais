"""
Script para exclusão dos registros legados do módulo 'municoes'
e sincronização completa com os dados do módulo 'material_belico'
(MunicaoConvencional e MunicaoQuimica).
"""
import os
import sys
import django

sys.path.insert(0, '/home/servidor-sys-baep/BAEP-Controle-Materiais')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserva_baep.settings')
django.setup()

from django.db import transaction
from municoes.models import (
    LoteMunicao, RetiradaMunicao, DevolucaoMunicao,
    RegistroDisparoMunicao, DevolucaoCPI
)
from material_belico.models import MunicaoConvencional, MunicaoQuimica
from materiais.models import Material


@transaction.atomic
def sync_municoes():
    print("==================================================")
    print("1. APAGANDO REGISTROS DO MÓDULO MUNIÇÕES...")
    
    del_disparos, _ = RegistroDisparoMunicao.objects.all().delete()
    del_devs, _ = DevolucaoMunicao.objects.all().delete()
    del_rets, _ = RetiradaMunicao.objects.all().delete()
    del_cpi, _ = DevolucaoCPI.objects.all().delete()
    del_lotes, _ = LoteMunicao.objects.all().delete()
    
    print(f"   - Registros de disparo apagados: {del_disparos}")
    print(f"   - Devoluções apagadas: {del_devs}")
    print(f"   - Retiradas apagadas: {del_rets}")
    print(f"   - Devoluções CPI apagadas: {del_cpi}")
    print(f"   - Lotes de munição apagados: {del_lotes}")

    print("\n2. SINCRONIZANDO COM O MÓDULO MATERIAL BÉLICO...")
    
    # ----------------------------------------------------
    # Munições Convencionais
    # ----------------------------------------------------
    conv_count = 0
    for mc in MunicaoConvencional.objects.all():
        tot = mc.total
        if tot == 0 and mc.estoque == 0 and mc.em_uso == 0:
            # Sincroniza mesmo que 0 para ter a estrutura ou foca em itens ativos
            pass
        
        cal_clean = mc.calibre.replace('.', '').strip()
        sub_clean = mc.subtipo.strip()
        num_mat = f"MUN-{cal_clean}-{sub_clean}-{mc.secao}"
        nome_mat = f"Munição Calibre {mc.calibre} {mc.get_subtipo_display()} ({mc.get_secao_display()})"
        
        material, _ = Material.objects.update_or_create(
            numero=num_mat,
            defaults={
                'tipo': 'MUNICAO',
                'categoria': 'OUTROS',
                'nome': nome_mat,
                'quantidade': tot,
                'quantidade_disponivel': mc.estoque,
                'quantidade_em_uso': mc.em_uso,
                'estado': 'BOM',
                'status': 'DISPONIVEL',
                'observacoes': f"Sincronizado do Material Bélico ({mc.calibre} {mc.subtipo})"
            }
        )
        
        # Tipo de munição no Lote
        tipo_lote = 'REAL'
        if mc.subtipo in ('TREINA', 'SAT'):
            tipo_lote = 'TREINAMENTO'
        elif mc.subtipo == 'FESTIM':
            tipo_lote = 'FESTIM'
            
        LoteMunicao.objects.create(
            material=material,
            calibre=mc.calibre,
            marca='CBC',
            numero_lote=f"LOTE-{cal_clean}-{sub_clean}",
            tipo_municao=tipo_lote,
            quantidade_inicial=tot if tot > 0 else 1,
            quantidade_atual=mc.estoque,
            quantidade_estojos=mc.capsulas,
            ativo=True
        )
        conv_count += 1

    # ----------------------------------------------------
    # Munições Químicas
    # ----------------------------------------------------
    quim_count = 0
    for mq in MunicaoQuimica.objects.all():
        tot = mq.total
        tipo_disp = mq.get_tipo_municao_display()
        num_mat = f"MUN-QUIM-{mq.tipo_municao}"
        nome_mat = f"Munição Química {tipo_disp}"
        
        material, _ = Material.objects.update_or_create(
            numero=num_mat,
            defaults={
                'tipo': 'MUNICAO',
                'categoria': 'CHOQUE',
                'nome': nome_mat,
                'quantidade': tot,
                'quantidade_disponivel': mq.qtd_armario,
                'quantidade_em_uso': mq.qtd_kto + mq.qtd_bornal,
                'estado': 'BOM',
                'status': 'DISPONIVEL',
                'observacoes': mq.observacoes or f"Munição Química Sincronizada ({tipo_disp})"
            }
        )
        
        LoteMunicao.objects.create(
            material=material,
            calibre='QUÍMICA',
            marca='CONDOR',
            numero_lote=f"LOTE-QUIM-{mq.tipo_municao}",
            tipo_municao='REAL',
            data_validade=mq.validade_prazo,
            quantidade_inicial=tot if tot > 0 else 1,
            quantidade_atual=mq.qtd_armario,
            quantidade_estojos=0,
            ativo=True
        )
        quim_count += 1

    print(f"   - Munições convencionais sincronizadas: {conv_count} lotes")
    print(f"   - Munições químicas sincronizadas: {quim_count} lotes")
    print("==================================================")
    print("SINCRONIZAÇÃO FINALIZADA COM SUCESSO!")
    print("==================================================")


if __name__ == '__main__':
    sync_municoes()
