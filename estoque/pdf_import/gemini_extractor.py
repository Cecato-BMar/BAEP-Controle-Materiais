import json
import logging
from decimal import Decimal
from typing import Any

from django.conf import settings
import google.generativeai as genai

from .nfe_parser import _parse_decimal

logger = logging.getLogger(__name__)

PROMPT_DANFE_ITEMS = (
    "Extraia todos os itens desta DANFE. "
    "Retorne um JSON com uma lista de objetos contendo: "
    "codigo, descricao, ncm, cfop, quantidade, valor_unitario, valor_total."
)


def extract_nfe_items_with_gemini(pdf_bytes: bytes) -> list[dict]:
    """
    Extrai a lista de itens de uma DANFE em PDF usando Google Gemini (gemini-2.0-flash).

    Retorna lista de dicionários normalizados:
    [
        {
            "codigo": str | None,
            "descricao": str,
            "ncm": str | None,
            "cfop": str | None,
            "unidade": str | None,
            "quantidade": Decimal | None,
            "valor_unitario": Decimal | None,
            "valor_total": Decimal | None,
        },
        ...
    ]
    """
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise ValueError("GEMINI_API_KEY não configurada em settings.py.")

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config={"response_mime_type": "application/json"},
    )

    pdf_part = {
        "mime_type": "application/pdf",
        "data": pdf_bytes,
    }

    try:
        response = model.generate_content([pdf_part, PROMPT_DANFE_ITEMS])
        text_content = getattr(response, "text", "") or ""
        parsed = json.loads(text_content)
    except Exception as exc:
        logger.error(f"Erro ao chamar Google Gemini para extração de itens: {exc}", exc_info=True)
        raise RuntimeError(f"Falha na extração de itens via Gemini: {exc}") from exc

    raw_items = []
    if isinstance(parsed, list):
        raw_items = parsed
    elif isinstance(parsed, dict):
        for key in ["itens", "items", "produtos", "dados"]:
            if isinstance(parsed.get(key), list):
                raw_items = parsed[key]
                break
        if not raw_items and ("codigo" in parsed or "descricao" in parsed):
            raw_items = [parsed]

    normalized_items = []
    for it in raw_items:
        if not isinstance(it, dict):
            continue

        qtd = _parse_decimal(str(it.get("quantidade", "") or ""))
        vunit = _parse_decimal(str(it.get("valor_unitario", "") or ""))
        vtot = _parse_decimal(str(it.get("valor_total", "") or ""))

        # Se valor_total faltar mas tiver qtd e vunit, calcula
        if vtot is None and qtd is not None and vunit is not None:
            vtot = (qtd * vunit).quantize(Decimal("0.01"))

        normalized_items.append({
            "codigo": str(it.get("codigo") or "").strip() or None,
            "descricao": str(it.get("descricao") or "").strip(),
            "ncm": str(it.get("ncm") or "").strip() or None,
            "cfop": str(it.get("cfop") or "").strip() or None,
            "unidade": str(it.get("unidade") or "").strip() or None,
            "quantidade": qtd,
            "valor_unitario": vunit,
            "valor_total": vtot,
        })

    return normalized_items
