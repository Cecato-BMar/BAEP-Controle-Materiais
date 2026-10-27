import io
import logging
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Union, BinaryIO

from .ocr import read_file_bytes, read_chave_from_barcode, extract_text_raw

logger = logging.getLogger(__name__)


def _parse_decimal(val_str: str | None) -> Decimal | None:
    """Converte strings numéricas em formato monetário brasileiro ou decimal para Decimal."""
    if not val_str:
        return None
    val_clean = re.sub(r"[^\d,\.]", "", val_str.strip())
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


def _parse_date(date_str: str | None) -> date | None:
    """Extrai objeto datetime.date a partir de strings no formato DD/MM/AAAA."""
    if not date_str:
        return None
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", str(date_str))
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def parse_nfe(file_obj: Union[str, Path, BinaryIO, bytes]) -> dict:
    """
    Extrai dados da DANFE (NFe escaneada ou digital).

    Usa:
    - read_chave_from_barcode() para chave_acesso (100% confiável via pyzbar)
    - extract_text_raw() para OCR dos demais campos

    Retorna dict estruturado com campos, _ocr_used=True e _confidence.
    Nunca levanta exceção para arquivos inválidos ou campos não encontrados,
    retornando None nos campos respectivos.
    """
    empty_result = {
        "chave_acesso": None,
        "numero_nf": None,
        "serie": None,
        "data_emissao": None,
        "data_saida": None,
        "natureza_operacao": None,
        "emitente": {
            "razao_social": None,
            "cnpj": None,
        },
        "destinatario": {
            "razao_social": None,
            "cnpj": None,
        },
        "fatura": {
            "numero": None,
            "vencimento": None,
            "valor": None,
        },
        "valor_total_produtos": None,
        "valor_total_nota": None,
        "itens": [],
        "empenho_referencia": None,
        "_ocr_used": False,
        "_confidence": {
            "chave_acesso": "low",
            "cnpj_emitente": "low",
            "numero_nf": "low",
            "datas": "low",
            "valores": "low",
            "itens": "low",
            "empenho_referencia": "low",
        },
    }

    try:
        data = read_file_bytes(file_obj)
        if not data or not data.startswith(b"%PDF-"):
            logger.warning("Arquivo fornecido para parse_nfe não é um PDF válido.")
            return empty_result
    except Exception as e:
        logger.warning(f"Erro ao ler bytes do arquivo em parse_nfe: {e}")
        return empty_result

    # 1. Chave de acesso: SEMPRE do código de barras (não faz fallback de OCR para evitar erro de dígito)
    chave_acesso = read_chave_from_barcode(io.BytesIO(data))
    if not chave_acesso:
        logger.warning("Chave de acesso (44 dígitos) não foi encontrada no código de barras da NFe.")

    # 2. Extração OCR do texto integral
    text = extract_text_raw(io.BytesIO(data))
    if not text:
        logger.warning("Nenhum texto extraído do PDF da NFe.")
        res = empty_result.copy()
        res["chave_acesso"] = chave_acesso
        res["_ocr_used"] = True
        if chave_acesso:
            res["_confidence"]["chave_acesso"] = "high"
        return res

    # 3. Número da NF
    m_nf = re.search(r"N[ºo°]\.?\s*(\d{3,9})", text, re.IGNORECASE)
    numero_nf = m_nf.group(1) if m_nf else None
    if not numero_nf:
        logger.warning("Número da NF não identificado no texto.")

    # 4. Série da NF
    m_serie = re.search(r"S[EÉ]RIE:?\s*(\d+)", text, re.IGNORECASE)
    serie = m_serie.group(1) if m_serie else None

    # 5. Natureza da Operação
    m_nat = re.search(r"Natureza da opera[çc][ãa]o[^\n]*\n\s*([^\n\|]+)", text, re.IGNORECASE)
    natureza_operacao = None
    if m_nat:
        nat_cand = m_nat.group(1).strip()
        natureza_operacao = nat_cand.split("|")[0].strip()

    # 6. CNPJs (primeiro emitente, segundo destinatário)
    cnpjs = re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", text)
    cnpj_emitente = cnpjs[0] if len(cnpjs) > 0 else None
    cnpj_destinatario = cnpjs[1] if len(cnpjs) > 1 else None

    # 7. Razão Social do Emitente
    m_emit = re.search(
        r"RECEBEMOS DE\s*(?:[\d\.,/-]+\s+)?([A-Z\s]+?)\s+OS PRODUTOS",
        text,
        re.IGNORECASE,
    )
    razao_emitente = m_emit.group(1).strip() if m_emit else None

    # 8. Razão Social do Destinatário
    razao_destinatario = None
    if cnpj_destinatario:
        escaped_cnpj = re.escape(cnpj_destinatario)
        m_dest = re.search(
            rf"Destinat[áa]rio[\s\S]*?(?:Nome\s*/\s*Raz[ãa]o\s*Social[^\n]*\n)?[\s\S]*?([A-Za-z0-9\.\s-]+?)\s+{escaped_cnpj}",
            text,
            re.IGNORECASE,
        )
        if m_dest:
            lines = [l.strip() for l in m_dest.group(1).splitlines() if len(l.strip()) > 3]
            if lines:
                razao_destinatario = lines[-1]
    if not razao_destinatario:
        m_dest_fallback = re.search(
            r"Destinat[áa]rio/Remetente[\s\S]*?\n\s*([A-Za-z0-9\.\s-]+?)\s+\d{2}\.\d{3}\.\d{3}",
            text,
            re.IGNORECASE,
        )
        if m_dest_fallback:
            lines = [l.strip() for l in m_dest_fallback.group(1).splitlines() if len(l.strip()) > 3]
            if lines:
                razao_destinatario = lines[-1]

    # 9. Datas de Emissão e Saída
    m_dt_emissao = re.search(r"Data emiss[ãa]o\s*[\n\r]*\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    m_dt_saida = re.search(r"Data sa[íi]da\s*[\n\r]*\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)

    data_emissao = _parse_date(m_dt_emissao.group(1)) if m_dt_emissao else None
    data_saida = _parse_date(m_dt_saida.group(1)) if m_dt_saida else None

    # Fallback para datas gerais se não casar os rótulos exatos
    if not data_emissao:
        all_dates = re.findall(r"\d{2}/\d{2}/\d{4}", text)
        if all_dates:
            data_emissao = _parse_date(all_dates[0])
            if len(all_dates) > 1 and not data_saida:
                data_saida = _parse_date(all_dates[1])
    if not data_saida:
        data_saida = data_emissao

    # 10. Fatura
    m_fat = re.search(
        r"Faturas?[\s\S]*?(?:N[úu]mero[^\n]*\n)?\s*(\d{1,4})\s+(\d{2}/\d{2}/\d{4})\s+([\d\.,]+)",
        text,
        re.IGNORECASE,
    )
    if m_fat:
        fatura = {
            "numero": m_fat.group(1),
            "vencimento": _parse_date(m_fat.group(2)),
            "valor": _parse_decimal(m_fat.group(3)),
        }
    else:
        fatura = {"numero": None, "vencimento": None, "valor": None}

    # 11. Empenho de Referência (Dados Adicionais)
    m_emp = re.search(r"[Ee]mpenho\s*[:\s]*(\d{4}NE\d+)", text)
    empenho_referencia = m_emp.group(1) if m_emp else None
    if not empenho_referencia:
        logger.warning("Número de Nota de Empenho de referência não encontrado nas observações da NFe.")

    # 12. Itens da Nota Fiscal
    item_regex = re.compile(
        r'(?P<codigo>[a-zA-Z0-9_-]+)?\s*[\|\]]?\s*'
        r'(?P<descricao>[a-zA-Z0-9\s\.,_-]+?)\s+'
        r'(?P<ncm>\d{8})\s+'
        r'(?:\d{4}[\]\)]?\s+)?'
        r'(?P<cfop>\d\.\d{3})[\]\)]?\s+'
        r'(?P<unidade>[a-zA-Z]+)[\]\)]?\s+'
        r'(?P<qtd>[\d\.,]+)\s+'
        r'(?P<vunit>[\d\.,]+)\s+'
        r'(?P<vtot>[\d\.,]+)',
        re.IGNORECASE,
    )

    itens = []
    seen_descriptions = set()
    for line in text.splitlines():
        m_item = item_regex.search(line)
        if m_item:
            d = m_item.groupdict()
            desc = d["descricao"].strip()
            # Limpa prefixos de ruído de OCR comuns
            desc = re.sub(r"^[JjIli\-_\|\.]{1,2}\s*", "", desc).strip()
            
            # Evita duplicatas se a mesma linha foi extraída no bloco de layout e tabular
            desc_key = desc.lower()[:15]
            if desc_key in seen_descriptions:
                continue
            seen_descriptions.add(desc_key)

            qtd = _parse_decimal(d["qtd"])
            vunit = _parse_decimal(d["vunit"])
            vtot = _parse_decimal(d["vtot"])

            codigo = d["codigo"]
            if codigo:
                codigo = re.sub(r"^[IlJj\-_\|]{1,2}", "", codigo).strip()

            itens.append({
                "codigo": codigo,
                "descricao": desc,
                "ncm": d["ncm"],
                "cfop": d["cfop"],
                "unidade": d["unidade"],
                "quantidade": qtd,
                "valor_unitario": vunit,
                "valor_total": vtot,
            })

    # 13. Totais da Nota
    total_itens = sum((it["valor_total"] for it in itens if it["valor_total"] is not None), Decimal("0.00")) if itens else None

    m_tot = re.search(r"Valor total da nota\s*[\n\r\|]*\s*([\d\.,]+)", text, re.IGNORECASE)
    val_nota_cand = _parse_decimal(m_tot.group(1)) if m_tot else None
    if val_nota_cand and val_nota_cand > Decimal("0.00"):
        valor_total_nota = val_nota_cand
    elif fatura["valor"] and fatura["valor"] > Decimal("0.00"):
        valor_total_nota = fatura["valor"]
    elif total_itens and total_itens > Decimal("0.00"):
        valor_total_nota = total_itens
    else:
        valor_total_nota = None

    m_tot_prod = re.search(r"Valor total dos produtos\s*[\n\r\|]*\s*([\d\.,]+)", text, re.IGNORECASE)
    val_prod_cand = _parse_decimal(m_tot_prod.group(1)) if m_tot_prod else None
    if val_prod_cand and val_prod_cand > Decimal("0.00"):
        valor_total_produtos = val_prod_cand
    elif total_itens and total_itens > Decimal("0.00"):
        valor_total_produtos = total_itens
    else:
        valor_total_produtos = valor_total_nota

    # Confiança dos campos
    confidence = {
        "chave_acesso": "high" if chave_acesso else "low",
        "cnpj_emitente": "high" if cnpj_emitente else "low",
        "numero_nf": "high" if numero_nf else "low",
        "datas": "high" if data_emissao else "low",
        "valores": "high" if valor_total_nota else "low",
        "itens": "low",
        "empenho_referencia": "high" if empenho_referencia else "low",
    }

    return {
        "chave_acesso": chave_acesso,
        "numero_nf": numero_nf,
        "serie": serie,
        "data_emissao": data_emissao,
        "data_saida": data_saida,
        "natureza_operacao": natureza_operacao,
        "emitente": {
            "razao_social": razao_emitente,
            "cnpj": cnpj_emitente,
        },
        "destinatario": {
            "razao_social": razao_destinatario,
            "cnpj": cnpj_destinatario,
        },
        "fatura": fatura,
        "valor_total_produtos": valor_total_produtos,
        "valor_total_nota": valor_total_nota,
        "itens": itens,
        "empenho_referencia": empenho_referencia,
        "_ocr_used": True,
        "_confidence": confidence,
    }
