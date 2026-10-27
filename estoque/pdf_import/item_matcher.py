from decimal import Decimal
from typing import Any


def _to_decimal(val: Any) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def match_items(nfe: dict, empenho: dict) -> list[dict]:
    """
    Casa cada item da NFe com seu equivalente no Empenho.
    
    Retorna lista na ordem dos itens da NFe:
    [
        {
            "nfe_item": {...},           # dict original do item NFe
            "empenho_item": {...} | None, # dict original do item Empenho (ou None se não casar)
            "match_method": "qty_value" | "value_only" | "none",
            "confidence": "high" | "medium" | "low",
        },
        ...
    ]
    """
    nfe_itens = nfe.get("itens") or []
    # Cria lista mutável dos candidatos do empenho para evitar que o mesmo item seja casado 2 vezes
    candidatos_empenho = list(empenho.get("itens") or [])

    results = []

    for nfe_item in nfe_itens:
        nfe_qtd = _to_decimal(nfe_item.get("quantidade"))
        nfe_vunit = _to_decimal(nfe_item.get("valor_unitario"))
        nfe_vtot = _to_decimal(nfe_item.get("valor_total"))

        matched_item = None
        match_method = "none"
        confidence = "low"

        # 1. Tentativa por quantidade E valor_unitario (qty_value)
        if nfe_qtd is not None and nfe_vunit is not None:
            matches_qv = []
            for emp_item in candidatos_empenho:
                emp_qtd = _to_decimal(emp_item.get("quantidade"))
                emp_vunit = _to_decimal(emp_item.get("valor_unitario"))
                if emp_qtd is not None and emp_vunit is not None:
                    if abs(nfe_qtd - emp_qtd) <= Decimal("0.01") and abs(nfe_vunit - emp_vunit) <= Decimal("0.01"):
                        matches_qv.append(emp_item)

            if len(matches_qv) == 1:
                matched_item = matches_qv[0]
                match_method = "qty_value"
                confidence = "high"
            elif len(matches_qv) > 1:
                matched_item = matches_qv[0]
                match_method = "qty_value"
                confidence = "medium"

        # 2. Tentativa por valor_unitario E valor_total (value_only) se qty_value falhou
        if not matched_item and nfe_vunit is not None and nfe_vtot is not None:
            matches_vo = []
            for emp_item in candidatos_empenho:
                emp_vunit = _to_decimal(emp_item.get("valor_unitario"))
                emp_vtot = _to_decimal(emp_item.get("preco_total"))
                if emp_vunit is not None and emp_vtot is not None:
                    if abs(nfe_vunit - emp_vunit) <= Decimal("0.01") and abs(nfe_vtot - emp_vtot) <= Decimal("0.01"):
                        matches_vo.append(emp_item)

            if matches_vo:
                matched_item = matches_vo[0]
                match_method = "value_only"
                confidence = "medium"

        # 3. Se casou, remover o candidato do empenho para não ser reusado
        if matched_item:
            candidatos_empenho.remove(matched_item)

        results.append({
            "nfe_item": nfe_item,
            "empenho_item": matched_item,
            "match_method": match_method,
            "confidence": confidence,
        })

    return results
