import logging
import os
from decimal import Decimal
from typing import Any

from django.conf import settings
from google import genai
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ItemNFeSchema(BaseModel):
    codigo: str | None = None
    descricao: str
    ncm: str | None = None
    cfop: str | None = None
    unidade: str | None = None
    quantidade: float
    valor_unitario: float
    valor_total: float


class NFeSchema(BaseModel):
    itens: list[ItemNFeSchema]


def extract_nfe_items_with_gemini(pdf_bytes: bytes) -> list[dict]:
    """
    Extrai todos os itens de uma DANFE em PDF usando o SDK oficial google-genai.
    Retorna lista de dicionários normalizados ou lista vazia em caso de falha/ausência de chave.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        logger.warning("GEMINI_API_KEY ausente.")
        return []

    try:
        client = genai.Client(api_key=api_key)

        logger.info(
            "Gemini: enviando PDF (%d bytes) para extração de itens...",
            len(pdf_bytes) if pdf_bytes else 0,
        )

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf'),
                (
                    "Analise este PDF de uma DANFE (Documento Auxiliar da Nota Fiscal Eletrônica) brasileira. "
                    "Extraia TODOS os itens/produtos listados na nota. "
                    "Para cada item retorne: codigo (código do produto), descricao, ncm, cfop, unidade, "
                    "quantidade (numérico), valor_unitario (numérico) e valor_total (numérico). "
                    "Se o PDF estiver escaneado ou for uma imagem, faça OCR antes de extrair."
                ),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=NFeSchema,
                temperature=0,
            ),
        )

        raw_text = response.text
        logger.info("Gemini: resposta recebida (%d chars): %s", len(raw_text), raw_text[:500])

        result = NFeSchema.model_validate_json(raw_text)
        items = []
        for item in result.itens:
            d = item.model_dump()
            items.append({
                "codigo": d.get("codigo"),
                "descricao": d.get("descricao"),
                "ncm": d.get("ncm"),
                "cfop": d.get("cfop"),
                "unidade": d.get("unidade"),
                "quantidade": Decimal(str(d["quantidade"])),
                "valor_unitario": Decimal(str(d["valor_unitario"])),
                "valor_total": Decimal(str(d["valor_total"])),
            })

        logger.info("Gemini: %d itens extraídos com sucesso.", len(items))
        return items

    except Exception as e:
        logger.error("Erro no Gemini: %s", e, exc_info=True)
        return []


def test_gemini_connection() -> dict:
    """
    Testa a conectividade com a API do Gemini.
    Retorna dict com status, mensagem e detalhes.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return {
            "ok": False,
            "error": "GEMINI_API_KEY não está configurada nas variáveis de ambiente.",
            "key_preview": None,
        }

    key_preview = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "***"

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=["Responda apenas: OK"],
            config=types.GenerateContentConfig(temperature=0),
        )
        return {
            "ok": True,
            "message": f"Conexão OK. Resposta: {response.text.strip()[:50]}",
            "key_preview": key_preview,
            "model": "gemini-2.0-flash",
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "key_preview": key_preview,
        }
