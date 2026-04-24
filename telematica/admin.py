from django.contrib import admin
from .models import (CategoriaEquipamento, Equipamento, ConfiguracaoRadio, 
                     LinhaMovel, ServicoTI, ManutencaoTI)

@admin.register(CategoriaEquipamento)
class CategoriaEquipamentoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'icone']

@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ['hostname', 'categoria', 'marca', 'modelo', 'numero_serie', 'status', 'setor', 'endereco_ip']
    list_filter = ['categoria', 'status', 'setor']
    search_fields = ['hostname', 'numero_serie', 'patrimonio', 'marca', 'modelo', 'endereco_ip']
    date_hierarchy = 'data_cadastro'

@admin.register(ConfiguracaoRadio)
class ConfiguracaoRadioAdmin(admin.ModelAdmin):
    list_display = ['equipamento', 'issi', 'tei', 'grupo_principal', 'criptografia_ativa']
    search_fields = ['issi', 'tei', 'equipamento__numero_serie']

@admin.register(LinhaMovel)
class LinhaMovelAdmin(admin.ModelAdmin):
    list_display = ['numero', 'operadora', 'iccid', 'equipamento_vinculado', 'ativo']
    list_filter = ['operadora', 'ativo']
    search_fields = ['numero', 'iccid', 'imei_1']

@admin.register(ServicoTI)
class ServicoTIAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'fornecedor', 'status', 'vencimento']
    list_filter = ['tipo', 'status']

@admin.register(ManutencaoTI)
class ManutencaoTIAdmin(admin.ModelAdmin):
    list_display = ['equipamento', 'tipo', 'data_inicio', 'tecnico_responsavel', 'concluida']
    list_filter = ['tipo', 'concluida']
    date_hierarchy = 'data_inicio'
