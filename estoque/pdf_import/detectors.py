import io
import logging
from pathlib import Path
from typing import Union, BinaryIO

import pdfplumber

from .ocr import read_file_bytes, read_chave_from_barcode, extract_text_raw

logger = logging.getLogger(__name__)

TYPE_NFE = "nfe"
TYPE_EMPENHO = "empenho"
TYPE_UNKNOWN = "unknown"


def detect_pdf_type(file_obj: Union[str, Path, BinaryIO, bytes]) -> str:
    """
    Detecta o tipo de documento contido no PDF.
    Retorna: 'nfe' | 'empenho' | 'unknown'

    Heurística:
    1. Extração digital rápida com pdfplumber:
       - Empenho: 'NOTA DE EMPENHO' e 'SIAFISICO'
       - NFe: 'DANFE' ou 'DOCUMENTO AUXILIAR DA NOTA FISCAL'
    2. Se texto vetorial for vazio (PDF escaneado como nfe_sample.pdf):
       - Checa presença de chave de acesso (44 dígitos) via código de barras
       - Executa OCR de fallback procurando 'DANFE' / 'DOCUMENTO AUXILIAR'
    3. Nunca levanta exceção: retorna 'unknown' em caso de falha ou documento irreconhecível.
    """
    try:
        data = read_file_bytes(file_obj)
        if not data or not data.startswith(b"%PDF-"):
            return TYPE_UNKNOWN

        # 1. Tenta extração direta com pdfplumber (rápida, em memória)
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                if pdf.pages:
                    text_p0 = (pdf.pages[0].extract_text() or "").upper()
                    if "NOTA DE EMPENHO" in text_p0 and "SIAFISICO" in text_p0:
                        return TYPE_EMPENHO
                    if "DANFE" in text_p0 or "DOCUMENTO AUXILIAR DA NOTA FISCAL" in text_p0:
                        return TYPE_NFE
        except Exception as err_plumber:
            logger.debug(f"pdfplumber não conseguiu ler o PDF: {err_plumber}")

        # 2. Se for PDF escaneado (sem texto digital), verifica barcode da NFe
        chave = read_chave_from_barcode(io.BytesIO(data))
        if chave and len(chave) == 44:
            return TYPE_NFE

        # 3. Fallback: OCR direto da primeira página/documento
        ocr_text = extract_text_raw(io.BytesIO(data)).upper()
        if "NOTA DE EMPENHO" in ocr_text and "SIAFISICO" in ocr_text:
            return TYPE_EMPENHO
        if "DANFE" in ocr_text or "DOCUMENTO AUXILIAR" in ocr_text:
            return TYPE_NFE

    except Exception as e:
        logger.warning(f"Erro ao detectar tipo de PDF: {e}", exc_info=True)

    return TYPE_UNKNOWN
