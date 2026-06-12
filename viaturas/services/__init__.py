"""
viaturas/services — Camada de serviços do módulo Frota.

Regras de negócio centralizadas aqui, não em views.py ou models.py.
As views devem importar e chamar estes services.

Submódulos:
    manutencao_historico  — Auditoria append-only (eventos imutáveis).
    manutencao_service    — Ciclo de vida de manutenções (criar/concluir/cancelar).
    indicadores_service   — KPIs, alertas e dados do dashboard.
    previsao_service      — Análise preventiva e previsão por viatura.
    abastecimento_service — Abastecimento e retirada de peças.
    alertas_service       — Sistema de alertas automáticas da frota.
"""

# Re-export dos serviços mais usados para acesso conveniente:
# from viaturas.services import criar_manutencao, obter_contexto_dashboard, ...

from viaturas.services.manutencao_service import (  # noqa: F401
    criar_manutencao,
    agendar_manutencao,
    converter_agendamento,
    atualizar_manutencao,
    concluir_manutencao,
    cancelar_manutencao,
    listar_por_status,
    pode_reabrir_viatura,
)

from viaturas.services.indicadores_service import (  # noqa: F401
    obter_contexto_dashboard,
    obter_status_counts,
    obter_kpis_frota,
    obter_indicadores_viatura,
    obter_alertas_preventivas,
)

from viaturas.services.previsao_service import (  # noqa: F401
    analisar_previsao_viatura,
    calcular_taxa_km,
    calcular_confianca,
    prever_manutencoes_especificas,
    prever_frota,
    obter_pecas_viatura,
    total_pecas_trocadas,
)

from viaturas.services.abastecimento_service import (  # noqa: F401
    registrar_abastecimento,
    criar_retirada,
    obter_consumo_viatura,
    obter_pecas_estoque_critico,
)

from viaturas.services.alertas_service import (  # noqa: F401
    gerar_todos_alertas,
    alertas_manutencao_vencida,
    alertas_garantia_vencendo,
    alertas_pneu_proximo_limite,
    alertas_veiculo_parado,
    alertas_documentos,
)