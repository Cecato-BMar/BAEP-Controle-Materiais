import logging
from typing import Any

from .detectors import detect_pdf_type, TYPE_NFE, TYPE_EMPENHO, TYPE_UNKNOWN
from .empenho_parser import parse_empenho
from .item_matcher import match_items
from .nfe_parser import parse_nfe
from .product_matcher import suggest_product
from .validators import validate_nfe_vs_empenho

logger = logging.getLogger(__name__)


def process_pdfs(nfe_file: Any, empenho_file: Any = None) -> dict:
    """
    Pipeline completo: detecção -> parse -> validação -> matching -> sugestão de produto.

    empenho_file é opcional. Quando None, a pipeline processa apenas a NFe e pula
    validação cruzada, gerando matches com confidence "medium" e método "nfe_only".

    Retorna:
    {
        "nfe": dict,
        "empenho": dict,
        "validation": dict,
        "matches": [
            {
                "nfe_item": dict,
                "empenho_item": dict | None,
                "match_method": str,
                "match_confidence": str,
                "suggestion": dict,
            },
            ...
        ],
        "header_suggestions": {
            "nota_fiscal": str | None,
            "documento_referencia": str | None,
            "data_movimentacao": str | None,  # ISO "YYYY-MM-DD"
            "fornecedor_nome": str | None,
            "fornecedor_cnpj": str | None,
        },
        "warnings": list[str],
    }
    """
    if not nfe_file:
        raise ValueError("Envie pelo menos a NFe para processamento.")

    # ── 1. Detecção e atribuição dos PDFs ──
    if empenho_file:
        # Fluxo original: 2 PDFs
        type1 = detect_pdf_type(nfe_file)
        type2 = detect_pdf_type(empenho_file)

        if type1 == type2 and type1 in (TYPE_NFE, TYPE_EMPENHO):
            raise ValueError("Envie 1 NFe e 1 Empenho. Recebi 2 do mesmo tipo.")

        actual_nfe = None
        actual_empenho = None

        if type1 == TYPE_NFE and type2 == TYPE_EMPENHO:
            actual_nfe = nfe_file
            actual_empenho = empenho_file
        elif type1 == TYPE_EMPENHO and type2 == TYPE_NFE:
            actual_nfe = empenho_file
            actual_empenho = nfe_file
        else:
            # Se um for unknown, tenta inverter e re-detectar
            re_type2 = detect_pdf_type(empenho_file)
            re_type1 = detect_pdf_type(nfe_file)
            if re_type1 == TYPE_NFE and re_type2 == TYPE_EMPENHO:
                actual_nfe = nfe_file
                actual_empenho = empenho_file
            elif re_type1 == TYPE_EMPENHO and re_type2 == TYPE_NFE:
                actual_nfe = empenho_file
                actual_empenho = nfe_file
            else:
                raise ValueError("Não foi possível identificar o tipo de um dos PDFs. Verifique os arquivos.")
    else:
        # Fluxo novo: apenas NFe
        type1 = detect_pdf_type(nfe_file)
        if type1 == TYPE_EMPENHO:
            raise ValueError("Quando o Empenho é omitido, o único PDF deve ser a NFe.")
        actual_nfe = nfe_file
        actual_empenho = None

    # ── 2. Parse ──
    nfe = parse_nfe(actual_nfe)
    empenho = parse_empenho(actual_empenho) if actual_empenho else {}

    # Verifica se a NFe falhou completamente na extração
    nfe_valida = any([
        nfe.get("chave_acesso"),
        nfe.get("numero_nf"),
        nfe.get("valor_total_nota"),
        nfe.get("itens"),
    ])

    if not nfe_valida:
        raise ValueError("Falha ao extrair dados da NFe. Verifique a qualidade do scan.")

    if actual_empenho:
        empenho_valido = any([
            empenho.get("numero_empenho"),
            empenho.get("valor_empenho"),
            empenho.get("itens"),
        ])
        if not empenho_valido:
            raise ValueError("Falha ao extrair dados do Empenho. Verifique a qualidade do scan.")

    # ── 3. Validação cruzada ──
    if empenho:
        validation = validate_nfe_vs_empenho(nfe, empenho)
    else:
        validation = validate_nfe_vs_empenho(nfe, {})

    # ── 4. Matching de itens ──
    if empenho:
        raw_matches = match_items(nfe, empenho)
    else:
        raw_matches = [
            {
                "nfe_item": it,
                "empenho_item": None,
                "match_method": "nfe_only",
                "confidence": "medium",
            }
            for it in nfe.get("itens", [])
        ]

    # ── 5. Sugestão de produto para cada match ──
    matches = []
    for m in raw_matches:
        nfe_it = m.get("nfe_item")
        emp_it = m.get("empenho_item")
        suggestion = suggest_product(nfe_it, emp_it)
        matches.append({
            "nfe_item": nfe_it,
            "empenho_item": emp_it,
            "match_method": m.get("match_method", "none"),
            "match_confidence": m.get("confidence", "low"),
            "suggestion": suggestion,
        })

    # ── 6. Consolidação de warnings ──
    warnings = list(validation.get("warnings", []))

    ocr_itens_conf = nfe.get("_confidence", {}).get("itens")
    if ocr_itens_conf == "low":
        w_ocr = "Descrições de itens com baixa confiança (OCR)"
        if w_ocr not in warnings:
            warnings.append(w_ocr)

    qtd_nfe = len(nfe.get("itens") or [])
    qtd_emp = len(empenho.get("itens") or [])
    if empenho and qtd_nfe != qtd_emp:
        w_qtd = f"{qtd_nfe} itens na NFe, {qtd_emp} no Empenho."
        if w_qtd not in warnings:
            warnings.append(w_qtd)

    # ── 7. Sugestões de cabeçalho ──
    data_val = nfe.get("data_saida") or nfe.get("data_emissao")
    data_mov_iso = (
        data_val.isoformat()
        if hasattr(data_val, "isoformat")
        else (str(data_val) if data_val else None)
    )

    emitente = nfe.get("emitente") if isinstance(nfe.get("emitente"), dict) else {}
    header_suggestions = {
        "nota_fiscal": nfe.get("numero_nf"),
        "documento_referencia": (
            empenho.get("numero_empenho")
            if empenho
            else nfe.get("empenho_referencia")
        ),
        "data_movimentacao": data_mov_iso,
        "fornecedor_nome": emitente.get("razao_social"),
        "fornecedor_cnpj": emitente.get("cnpj"),
    }

    return {
        "nfe": nfe,
        "empenho": empenho,
        "validation": validation,
        "matches": matches,
        "header_suggestions": header_suggestions,
        "warnings": warnings,
    }
