"""Mapeamento e configuração das abas do Google Sheets ↔ models do Django.

Fase 2: Cobre as 6 abas limpas (material_belico).
As 9 abas restantes ficam catalogadas em PENDING_SHEETS para fases futuras.
"""

from __future__ import annotations

from typing import Any, Callable

# ============================================================================
# 3.1 LEGACY_PARSERS — 6 abas da Fase 2 (Planilha Antiga - READ ONLY)
# ============================================================================

LEGACY_PARSERS: dict[str, dict[str, Any]] = {
    "PistolaGlock": {
        "sheet": "PISTOLAS GLOCK",
        "data_start_row": 2,
        "lookup_key": "patrimonio",
        "columns": {
            "B": "patrimonio",
            "C": "numero_serie",
            "D": "modelo",
            "E": "cod_opm",
            "F": "unidade",
            "G": "situacao_reserva",
            "H": "observacoes",
        },
        "stop_on_blank_lookup": True,
    },
    "PistolaTaurus": {
        "sheet": "PISTOLAS TAURUS",
        "data_start_row": 3,
        "lookup_key": "numero_serie",
        "columns": {
            "B": "patrimonio",
            "C": "numero_serie",
            "D": "modelo",
            "E": "unidade",
            "F": "observacoes",
        },
        "stop_on_blank_lookup": True,
    },
    "EspingardaCal12": {
        "sheet": "CAL.12",
        "data_start_row": 3,
        "lookup_key": "numero_espingarda",
        "columns": {
            "C": "numero_espingarda",
            "D": "patrimonio",
            "E": "kit_vinculado",
            "F": "status",
        },
        "stop_on_blank_lookup": True,
    },
    "EscudoBalistico": {
        "sheet": "ESCUDOS BALÍSTICOS",
        "data_start_row": 4,
        "lookup_key": "numero",
        "columns": {
            "B": "material",
            "C": "numero",
            "D": "fabricacao",
            "E": "validade",
            "F": "patrimonio",
            "G": "localizacao",
            "H": "lote_companhia",
            "I": "situacao",
        },
        "stop_on_blank_lookup": True,
        "filter_rows": lambda r: bool(str(r.get("numero", "")).strip()),
    },
    "TASER": {
        "sheet": "TASER",
        "data_start_row": 4,
        "lookup_key": "serie",
        "columns": {
            "D": "serie",
            "E": "situacao",
            "F": "carga_bateria_percent",
        },
        "stop_on_blank_lookup": True,
    },
    "RadioHT": {
        "sheet": "HT 26",
        "data_start_row": 3,
        "lookup_key": "serie",
        "columns": {
            "C": "patrimonio",
            "D": "serie",
            "E": "kit_vinculado",
            "F": "situacao",
            "G": "chamado_dtic",
            "H": "data_chamado_dtic",
        },
        "stop_on_blank_lookup": True,
    },
}

# ============================================================================
# 3.2 NEW_SHEET_MAP — 6 abas 1:1 com os modelos (Planilha Nova - Bidirecional)
# ============================================================================

NEW_SHEET_MAP: dict[str, dict[str, Any]] = {
    "PistolaGlock": {
        "sheet": "Pistolas_Glock",
        "lookup_key": "id",
        "columns": [
            "id",
            "patrimonio",
            "numero_serie",
            "modelo",
            "cod_opm",
            "unidade",
            "situacao_reserva",
            "observacoes",
            "atualizado_em",
        ],
        "read_only_columns": ["atualizado_em"],
        "column_aliases": {"atualizado_em": "data_atualizacao"},
    },
    "PistolaTaurus": {
        "sheet": "Pistolas_Taurus",
        "lookup_key": "id",
        "columns": [
            "id",
            "patrimonio",
            "numero_serie",
            "modelo",
            "unidade",
            "observacoes",
            "atualizado_em",
        ],
        "read_only_columns": ["atualizado_em"],
        "column_aliases": {"atualizado_em": "data_atualizacao"},
    },
    "EspingardaCal12": {
        "sheet": "Espingardas_Cal12",
        "lookup_key": "id",
        "columns": [
            "id",
            "numero_espingarda",
            "patrimonio",
            "kit_vinculado",
            "status",
            "atualizado_em",
        ],
        "read_only_columns": ["atualizado_em"],
        "column_aliases": {"atualizado_em": "data_atualizacao"},
    },
    "EscudoBalistico": {
        "sheet": "Escudos_Balisticos",
        "lookup_key": "id",
        "columns": [
            "id",
            "material",
            "numero",
            "fabricacao",
            "validade",
            "patrimonio",
            "localizacao",
            "lote_companhia",
            "situacao",
            "atualizado_em",
        ],
        "read_only_columns": ["atualizado_em"],
        "column_aliases": {"atualizado_em": "data_atualizacao"},
    },
    "TASER": {
        "sheet": "TASER",
        "lookup_key": "id",
        "columns": [
            "id",
            "serie",
            "situacao",
            "carga_bateria_percent",
            "atualizado_em",
        ],
        "read_only_columns": ["atualizado_em"],
        "column_aliases": {"atualizado_em": "data_atualizacao"},
    },
    "RadioHT": {
        "sheet": "Radios_HT",
        "lookup_key": "id",
        "columns": [
            "id",
            "patrimonio",
            "serie",
            "kit_vinculado",
            "situacao",
            "chamado_dtic",
            "data_chamado_dtic",
            "atualizado_em",
        ],
        "read_only_columns": ["atualizado_em"],
        "column_aliases": {"atualizado_em": "data_atualizacao"},
    },
}

# ============================================================================
# 3.3 PENDING_SHEETS — Abas fora de escopo da Fase 2 e respectivos motivos
# ============================================================================

PENDING_SHEETS: dict[str, str] = {
    "AM 600_640": "3 tabelas lado a lado (AM640, AM600, MosquetaoFederal) - Fase 3",
    "CONTROLE DE COLETES": "2 tabelas empilhadas (ColeteBalistico) - Fase 3",
    "ALGEMAS": "Layout irregular (Algemas) - Fase 3",
    "FUZIS E ACESSÓRIOS": "6 tabelas + fórmulas (Fuzil, RedDot, Magnificador, Supressor, VinculacaoAcessorioFuzil) - Fase 3",
    "KIT OP": "6 kits lado a lado + VLOOKUP (KitOperacional) - Fase 3",
    "PST TRANSF": "2 tabelas empilhadas (ArmaTransferenciaPendente) - Fase 3",
    "QUÍMICAS": "Fora de escopo (MunicaoQuimica) - Fase 3",
    "MUNIÇÕES ATUALIZADAS": "Apenas fórmulas agregadas - Não aplicável",
}

# ============================================================================
# 3.4 SYNC_ORDER — Ordem de sincronização e importação (itens antes de vínculos)
# ============================================================================

SYNC_ORDER: list[str] = [
    "PistolaGlock",
    "PistolaTaurus",
    "EspingardaCal12",
    "EscudoBalistico",
    "TASER",
    "RadioHT",
]


def get_model_class(model_name: str) -> Any:
    """Retorna a classe do modelo Django a partir do nome em string (lazy import)."""
    from material_belico import models as belico_models

    model_cls = getattr(belico_models, model_name, None)
    if not model_cls:
        raise ValueError(f"Modelo '{model_name}' não encontrado em material_belico.models.")
    return model_cls
