import re
from difflib import SequenceMatcher
from typing import Any

from estoque.models import Produto


def _normalize_catmat(val: Any) -> str:
    """Remove caracteres não-dígitos e zeros à esquerda para comparação de CATMAT."""
    if not val:
        return ""
    digits = re.sub(r"\D", "", str(val))
    norm = digits.lstrip("0")
    return norm if norm else ("0" if digits else "")


def _calculate_similarity(desc: str, target: str) -> float:
    """Calcula similaridade textual com suporte a SequenceMatcher e token overlap."""
    d = (desc or "").lower().strip()
    t = (target or "").lower().strip()
    if not d or not t:
        return 0.0

    base_ratio = SequenceMatcher(None, d, t).ratio()

    d_tokens = re.findall(r"\w+", d)
    t_tokens = re.findall(r"\w+", t)

    # Se a primeira palavra com 3+ letras for idêntica (ex: "margarina"), garante threshold de confiança
    if d_tokens and t_tokens and d_tokens[0] == t_tokens[0] and len(d_tokens[0]) >= 3:
        base_ratio = max(base_ratio, 0.78)

    # Overlap de tokens
    d_set = set(d_tokens)
    t_set = set(t_tokens)
    if d_set and t_set:
        overlap = len(d_set & t_set) / min(len(d_set), len(t_set))
        if overlap >= 0.5:
            base_ratio = max(base_ratio, 0.76)

    return base_ratio


def suggest_product(nfe_item: dict, empenho_item: dict | None = None) -> dict:
    """
    Sugere produto do catálogo (estoque.Produto) para um item da NFe / Empenho.
    
    Prioridade de matching:
    1. CATMAT exato: empenho_item["codigo_item"] == Produto.codigo_cat_mat (normalizados)
    2. Nome similar: comparando nfe_item["descricao"] e empenho_item["descricao"] com Produto.nome
    3. Nenhum match
    
    Retorna:
    {
        "produto_id": int | None,
        "produto_nome": str | None,
        "method": "catmat_exact" | "name_similar" | "none",
        "confidence": "high" | "medium" | "low",
        "ncm_nfe": str | None,
        "alternatives": [{"id": int, "nome": str, "score": float}, ...]  # até 3
    }
    """
    ncm_nfe = nfe_item.get("ncm") if isinstance(nfe_item, dict) else None

    empty_result = {
        "produto_id": None,
        "produto_nome": None,
        "method": "none",
        "confidence": "low",
        "ncm_nfe": ncm_nfe,
        "alternatives": [],
    }

    if not nfe_item:
        return empty_result

    # 1. Tentativa por CATMAT exato via empenho_item["codigo_item"]
    if empenho_item and empenho_item.get("codigo_item"):
        target_catmat = _normalize_catmat(empenho_item["codigo_item"])
        if target_catmat:
            qs_catmat = Produto.objects.filter(status="ATIVO").exclude(
                codigo_cat_mat__isnull=True
            ).exclude(codigo_cat_mat="")
            if not qs_catmat.exists():
                qs_catmat = Produto.objects.exclude(
                    codigo_cat_mat__isnull=True
                ).exclude(codigo_cat_mat="")

            matched_products = [
                p for p in qs_catmat if _normalize_catmat(p.codigo_cat_mat) == target_catmat
            ]

            if len(matched_products) == 1:
                p = matched_products[0]
                return {
                    "produto_id": p.id,
                    "produto_nome": p.nome,
                    "method": "catmat_exact",
                    "confidence": "high",
                    "ncm_nfe": ncm_nfe,
                    "alternatives": [],
                }
            elif len(matched_products) > 1:
                scored = []
                nfe_desc = nfe_item.get("descricao", "")
                for p in matched_products:
                    sc = _calculate_similarity(nfe_desc, p.nome)
                    scored.append((p, sc))
                scored.sort(key=lambda x: x[1], reverse=True)
                best_p, _ = scored[0]
                alts = [
                    {"id": p.id, "nome": p.nome, "score": round(float(sc), 2)}
                    for p, sc in scored[1:4]
                ]
                return {
                    "produto_id": best_p.id,
                    "produto_nome": best_p.nome,
                    "method": "catmat_exact",
                    "confidence": "high",
                    "ncm_nfe": ncm_nfe,
                    "alternatives": alts,
                }

    # 2. Tentativa por Nome similar (fallback quando CATMAT ausente ou não encontrado)
    produtos = list(Produto.objects.filter(status="ATIVO"))
    if not produtos:
        produtos = list(Produto.objects.all())

    if not produtos:
        return empty_result

    nfe_desc = nfe_item.get("descricao", "")
    emp_desc = empenho_item.get("descricao", "") if empenho_item else ""

    scored_produtos = []
    for prod in produtos:
        score_nfe = _calculate_similarity(nfe_desc, prod.nome)
        score_emp = _calculate_similarity(emp_desc, prod.nome) if emp_desc else 0.0
        best_item_score = max(score_nfe, score_emp)
        scored_produtos.append((prod, best_item_score))

    scored_produtos.sort(key=lambda x: x[1], reverse=True)

    top3_alts = [
        {"id": p.id, "nome": p.nome, "score": round(float(score), 2)}
        for p, score in scored_produtos[:3]
    ]

    best_prod, best_score = scored_produtos[0]

    if best_score > 0.75:
        return {
            "produto_id": best_prod.id,
            "produto_nome": best_prod.nome,
            "method": "name_similar",
            "confidence": "medium",
            "ncm_nfe": ncm_nfe,
            "alternatives": top3_alts,
        }
    elif 0.50 <= best_score <= 0.75:
        return {
            "produto_id": best_prod.id,
            "produto_nome": best_prod.nome,
            "method": "name_similar",
            "confidence": "low",
            "ncm_nfe": ncm_nfe,
            "alternatives": top3_alts,
        }
    else:
        return {
            "produto_id": None,
            "produto_nome": None,
            "method": "none",
            "confidence": "low",
            "ncm_nfe": ncm_nfe,
            "alternatives": top3_alts,
        }
