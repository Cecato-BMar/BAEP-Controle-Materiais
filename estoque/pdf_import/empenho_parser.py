import io
import logging
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Union, BinaryIO

import pdfplumber

from .ocr import read_file_bytes

logger = logging.getLogger(__name__)

MESES_PT = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}


def _parse_data_pt(s: str | None) -> date | None:
    """Extrai objeto datetime.date a partir de strings no formato 18SET2026."""
    if not s:
        return None
    m = re.search(r"(\d{2})([A-Za-z]{3})(\d{4})", str(s).strip())
    if not m:
        return None
    dia, mes_str, ano = m.groups()
    mes = MESES_PT.get(mes_str.upper())
    if not mes:
        return None
    try:
        return date(int(ano), mes, int(dia))
    except ValueError:
        return None


def _parse_decimal(val_str: str | None) -> Decimal | None:
    """Converte strings numéricas em formato monetário ou decimal brasileiro para Decimal."""
    if not val_str:
        return None
    val_clean = re.sub(r"[^\d,\.]", "", str(val_str).strip())
    if not val_clean:
        return None
    if "," in val_clean and "." in val_clean:
        val_clean = val_clean.replace(".", "").replace(",", ".")
    elif "," in val_clean:
        val_clean = val_clean.replace(",", ".")
    try:
        d = Decimal(val_clean)
        if d.as_tuple().exponent < -2:
            return d.quantize(Decimal("0.01"))
        return d
    except Exception:
        return None


def parse_empenho(file_obj: Union[str, Path, BinaryIO, bytes]) -> dict:
    """
    Extrai dados da Nota de Empenho (SIAFISICO-SP) via pdfplumber direto (sem OCR).
    Resiliente a encoding corrompido: processa página por página e protege cada campo com try/except.
    Nunca levanta exceção para não interromper fluxos de importação.
    """
    empty_result = {
        "numero_empenho": None,
        "ug": None,
        "ug_descricao": None,
        "data_emissao": None,
        "credor": {
            "cnpj": None,
            "razao_social": None,
        },
        "numero_processo": None,
        "numero_contrato": None,
        "valor_empenho": None,
        "itens": [],
        "local_entrega": None,
        "data_entrega": None,
        "_parser": "empenho",
        "_confidence": {
            "numero_empenho": "low",
            "ug": "low",
            "data_emissao": "low",
            "credor": "low",
            "valor_empenho": "low",
            "itens": "low",
            "local_entrega": "low",
            "data_entrega": "low",
        },
    }

    try:
        data = read_file_bytes(file_obj)
        if not data or not data.startswith(b"%PDF-"):
            logger.warning("Arquivo fornecido para parse_empenho não é um PDF válido.")
            return empty_result
    except Exception as e:
        logger.warning(f"Erro ao ler bytes do arquivo em parse_empenho: {e}")
        return empty_result

    pages_text = []
    all_tables = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    txt = page.extract_text(layout=False) or ""
                    pages_text.append(txt)
                except Exception as page_err:
                    logger.warning(f"Erro ao extrair texto da página {i} do empenho: {page_err}")
                try:
                    tbls = page.extract_tables() or []
                    all_tables.extend(tbls)
                except Exception as tbl_err:
                    logger.debug(f"Falha ao extrair tabelas da página {i}: {tbl_err}")
    except Exception as pdf_err:
        logger.warning(f"Falha geral ao abrir PDF do empenho com pdfplumber: {pdf_err}")
        return empty_result

    full_text = "\n".join(pages_text)
    if not full_text.strip():
        logger.warning("Nenhum texto extraído do PDF da Nota de Empenho.")
        return empty_result

    # 1. Número do Empenho
    numero_empenho = None
    try:
        m_emp = re.search(r"NOTA DE EMPENHO\s*-\s*SIAFISICO\s*-\s*(\d{4}NE\d+)", full_text, re.IGNORECASE)
        if not m_emp:
            m_emp = re.search(r"(\d{4}NE\d{5,})", full_text)
        if m_emp:
            numero_empenho = m_emp.group(1).strip()
        else:
            logger.warning("Número de empenho não encontrado no cabeçalho.")
    except Exception as e:
        logger.warning(f"Erro ao extrair numero_empenho: {e}")

    # 2. Unidade Gestora (UG) e Descrição
    ug = None
    ug_descricao = None
    try:
        m_ug = re.search(r"UG\s*(\d{6})\s*-\s*([^\n\r]+)", full_text)
        if m_ug:
            ug = m_ug.group(1).strip()
            ug_descricao = m_ug.group(2).strip()
    except Exception as e:
        logger.warning(f"Erro ao extrair UG: {e}")

    # 3. Data de Emissão
    data_emissao = None
    try:
        m_emissao = re.search(r"Data de Emiss[ãa]o\s*(\d{2}[A-Za-z]{3}\d{4})", full_text, re.IGNORECASE)
        if m_emissao:
            data_emissao = _parse_data_pt(m_emissao.group(1))
    except Exception as e:
        logger.warning(f"Erro ao extrair data_emissao: {e}")

    # 4. Credor (CNPJ de 14 dígitos e Razão Social)
    cnpj_credor = None
    razao_credor = None
    try:
        m_cnpj = re.search(r"CNPJ/CPF/UG\s*(\d{11,14})", full_text)
        if not m_cnpj:
            m_cnpj = re.search(r"(\d{14})", full_text)
        if m_cnpj:
            cnpj_credor = m_cnpj.group(1).strip()

        m_credor = re.search(r"Credor\s*([^\n\r]+)", full_text)
        if m_credor:
            razao_credor = m_credor.group(1).strip()
    except Exception as e:
        logger.warning(f"Erro ao extrair credor: {e}")

    # 5. Processo e Contrato
    numero_processo = None
    numero_contrato = None
    try:
        m_proc = re.search(r"N[oº°]?\s*Processo\s*(\d+)", full_text, re.IGNORECASE)
        if m_proc:
            numero_processo = m_proc.group(1).strip()

        m_ct = re.search(r"N[ºo°]?\s*Contrato\s*(\d{4}CT\d+)", full_text, re.IGNORECASE)
        if m_ct:
            numero_contrato = m_ct.group(1).strip()
    except Exception as e:
        logger.warning(f"Erro ao extrair processo/contrato: {e}")

    # 6. Valor do Empenho
    valor_empenho = None
    try:
        m_val = re.search(r"Valor do Empenho\s*R\$\s*([\d\.,]+)", full_text, re.IGNORECASE)
        if not m_val:
            m_val = re.search(r"Total ou Valor a Transportar\s*R\$\s*([\d\.,]+)", full_text, re.IGNORECASE)
        if m_val:
            valor_empenho = _parse_decimal(m_val.group(1))
    except Exception as e:
        logger.warning(f"Erro ao extrair valor_empenho: {e}")

    # 7. Local de Entrega e Data de Entrega
    local_entrega = None
    data_entrega = None
    try:
        m_local = re.search(r"Local de Entrega\s*([^\n\r]+)", full_text, re.IGNORECASE)
        if m_local:
            raw_local = m_local.group(1).strip()
            # Substitui caracteres de controle ou codificação ruim
            clean_local = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", raw_local)
            clean_local = clean_local.replace("2 BAEP", "2º BAEP")
            local_entrega = re.sub(r"\s+", " ", clean_local).strip()

        m_dt_ent = re.search(r"Data de Entrega\s*(\d{2}[A-Za-z]{3}\d{4})", full_text, re.IGNORECASE)
        if m_dt_ent:
            data_entrega = _parse_data_pt(m_dt_ent.group(1))
    except Exception as e:
        logger.warning(f"Erro ao extrair entrega: {e}")

    # 8. Extração dos Itens (via regex de blocos do SIAFISICO)
    itens = []
    try:
        item_regex = re.compile(
            r"Sequ[êe]ncia\s*(?P<seq>\d{3})\s*Item\s*(?P<item>[\d-]+)\s*Unid\.\s*Forn\.\s*(?P<unid>\d+)\s*\n"
            r"Quantidade\s*(?P<qtd>[\d\.,]+)\s*Valor\s*Unit[áa]rio\s*(?P<vunit>[\d\.,]+)\s*Pre[çc]o\s*Total\s*(?P<vtot>[\d\.,]+)\s*\n"
            r"Descri[çc][ãa]o\s*\n(?P<desc>[\s\S]+?)(?=(?:Sequ[êe]ncia\s*\d{3}|Total\s*ou\s*Valor|Impresso\s*peloSiafisico|\Z))",
            re.IGNORECASE,
        )

        for m in item_regex.finditer(full_text):
            d = m.groupdict()
            seq = d["seq"].strip()
            codigo_item = d["item"].strip()
            unid_forn = d["unid"].strip()
            qtd = _parse_decimal(d["qtd"])
            vunit = _parse_decimal(d["vunit"])
            vtot = _parse_decimal(d["vtot"])

            raw_desc = d["desc"].strip()
            clean_desc = re.sub(r"\s+", " ", raw_desc)
            clean_desc = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", clean_desc).strip()

            itens.append({
                "sequencia": seq,
                "codigo_item": codigo_item,
                "unidade_fornecedor": unid_forn,
                "quantidade": qtd,
                "valor_unitario": vunit,
                "preco_total": vtot,
                "descricao": clean_desc,
            })
    except Exception as e:
        logger.warning(f"Erro na extração de itens via regex do empenho: {e}")

    # Fallback para itens via extract_tables se o regex não capturar
    if not itens and all_tables:
        try:
            for tbl in all_tables:
                if len(tbl) >= 3 and any("Sequência" in str(cell) or "Sequncia" in str(cell) for cell in tbl[0]):
                    row0 = tbl[0]
                    row1 = tbl[1]
                    row3 = tbl[3] if len(tbl) > 3 else None
                    seq = row0[1] if len(row0) > 1 else ""
                    codigo_item = row0[3] if len(row0) > 3 else ""
                    unid_forn = row0[5] if len(row0) > 5 else ""
                    qtd = _parse_decimal(row1[1]) if len(row1) > 1 else None
                    vunit = _parse_decimal(row1[3]) if len(row1) > 3 else None
                    vtot = _parse_decimal(row1[5]) if len(row1) > 5 else None
                    desc = str(row3[0] if row3 and len(row3) > 0 else "").replace("\n", " ").strip()

                    if seq and codigo_item:
                        itens.append({
                            "sequencia": seq,
                            "codigo_item": codigo_item,
                            "unidade_fornecedor": unid_forn,
                            "quantidade": qtd,
                            "valor_unitario": vunit,
                            "preco_total": vtot,
                            "descricao": desc,
                        })
        except Exception as e:
            logger.warning(f"Erro na extração de itens via tabelas do empenho: {e}")

    # Confiança dos campos
    confidence = {
        "numero_empenho": "high" if numero_empenho else "low",
        "ug": "high" if ug else "low",
        "data_emissao": "high" if data_emissao else "low",
        "credor": "high" if (cnpj_credor and razao_credor) else "low",
        "valor_empenho": "high" if valor_empenho else "low",
        "itens": "high" if itens else "low",
        "local_entrega": "high" if local_entrega else "low",
        "data_entrega": "high" if data_entrega else "low",
    }

    return {
        "numero_empenho": numero_empenho,
        "ug": ug,
        "ug_descricao": ug_descricao,
        "data_emissao": data_emissao,
        "credor": {
            "cnpj": cnpj_credor,
            "razao_social": razao_credor,
        },
        "numero_processo": numero_processo,
        "numero_contrato": numero_contrato,
        "valor_empenho": valor_empenho,
        "itens": itens,
        "local_entrega": local_entrega,
        "data_entrega": data_entrega,
        "_parser": "empenho",
        "_confidence": confidence,
    }
