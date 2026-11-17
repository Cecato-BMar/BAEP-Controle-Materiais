import re
import xml.etree.ElementTree as ET
from datetime import datetime, date
from decimal import Decimal
from typing import Any

from nfelib import XmlParser, ParserConfig
from nfelib.nfe.bindings.v4_0.proc_nfe_v4_00 import NfeProc
from nfelib.nfe.bindings.v4_0.nfe_v4_00 import Nfe


def parse_nfe_xml(xml_bytes: bytes) -> dict[str, Any]:
    """
    Extrai dados estruturados de uma NF-e em formato XML usando a biblioteca nfelib.
    Suporta tanto documento raiz <NFe> quanto documento envelopado <nfeProc>.

    Retorna um dicionário normalizado e desacoplado de models:
    {
        "chave_nfe": str | None,
        "numero_nf": str,
        "serie": str,
        "data_emissao": date | None,
        "emitente_cnpj": str | None,
        "emitente_nome": str | None,
        "destinatario_doc": str | None,
        "destinatario_nome": str | None,
        "valor_total": Decimal,
        "itens": [
            {
                "codigo": str,
                "descricao": str,
                "ncm": str | None,
                "cfop": str | None,
                "unidade": str,
                "quantidade": Decimal,
                "valor_unitario": Decimal,
                "valor_total": Decimal,
            },
            ...
        ]
    }
    Lança ValueError com mensagem clara se o XML for inválido ou não for uma NF-e.
    """
    if not xml_bytes or not xml_bytes.strip():
        raise ValueError("Conteúdo XML vazio ou não fornecido.")

    # 1. Validação preliminar e detecção do elemento raiz
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        raise ValueError(f"XML malformado: {e}")

    tag_root = root.tag.split("}")[-1] if "}" in root.tag else root.tag

    parser = XmlParser(
        config=ParserConfig(
            fail_on_unknown_properties=False,
            fail_on_converter_warnings=False,
        )
    )

    chave_nfe = None
    nfe_obj = None

    if tag_root == "nfeProc":
        try:
            proc = parser.from_bytes(xml_bytes, NfeProc)
            nfe_obj = getattr(proc, "NFe", None) or getattr(proc, "nfe", None)
            prot = getattr(proc, "protNFe", None) or getattr(proc, "prot_nfe", None)
            if prot and hasattr(prot, "infProt") and getattr(prot.infProt, "chNFe", None):
                chave_nfe = str(prot.infProt.chNFe).strip()
        except Exception as e:
            raise ValueError(f"Falha ao interpretar nfeProc com nfelib: {e}")
    elif tag_root == "NFe":
        try:
            nfe_obj = parser.from_bytes(xml_bytes, Nfe)
        except Exception as e:
            raise ValueError(f"Falha ao interpretar NFe com nfelib: {e}")
    else:
        raise ValueError(
            f"Formato XML não suportado. Esperado <NFe> ou <nfeProc>, recebido <{tag_root}>."
        )

    if not nfe_obj:
        raise ValueError("Estrutura NFe não encontrada no documento XML.")

    inf = getattr(nfe_obj, "infNFe", None) or getattr(nfe_obj, "inf_nfe", None)
    if not inf:
        raise ValueError("Estrutura infNFe ausente na NFe.")

    # 2. Chave de acesso (chNFe)
    if not chave_nfe and hasattr(inf, "Id") and inf.Id:
        limpo = re.sub(r"\D", "", str(inf.Id))
        if len(limpo) == 44:
            chave_nfe = limpo
        elif limpo:
            chave_nfe = limpo

    # 3. Dados de identificação (ide)
    ide = getattr(inf, "ide", None) or getattr(inf, "Ide", None)
    if not ide:
        raise ValueError("Estrutura ide ausente na NFe.")

    numero_nf = str(getattr(ide, "nNF", "") or "").strip()
    if not numero_nf:
        raise ValueError("Número da NF (nNF) ausente no XML.")

    serie = str(getattr(ide, "serie", "") or "").strip()

    dh_raw = getattr(ide, "dhEmi", None) or getattr(ide, "dEmi", None)
    data_emissao = None
    if dh_raw:
        dh_str = str(dh_raw)[:10]
        try:
            data_emissao = datetime.strptime(dh_str, "%Y-%m-%d").date()
        except ValueError:
            data_emissao = None

    # 4. Emitente (emit)
    emit = getattr(inf, "emit", None) or getattr(inf, "Emit", None)
    emitente_cnpj = None
    emitente_nome = None
    if emit:
        emitente_cnpj = str(getattr(emit, "CNPJ", None) or getattr(emit, "CPF", None) or "")
        emitente_cnpj = re.sub(r"\D", "", emitente_cnpj) or None
        emitente_nome = str(getattr(emit, "xNome", "") or "").strip() or None

    # 5. Destinatário (dest)
    dest = getattr(inf, "dest", None) or getattr(inf, "Dest", None)
    destinatario_doc = None
    destinatario_nome = None
    if dest:
        destinatario_doc = str(getattr(dest, "CNPJ", None) or getattr(dest, "CPF", None) or "")
        destinatario_doc = re.sub(r"\D", "", destinatario_doc) or None
        destinatario_nome = str(getattr(dest, "xNome", "") or "").strip() or None

    # 6. Total da Nota (total/ICMSTot)
    valor_total = Decimal("0.00")
    total = getattr(inf, "total", None) or getattr(inf, "Total", None)
    if total:
        icms_tot = getattr(total, "ICMSTot", None) or getattr(total, "icms_tot", None)
        if icms_tot and getattr(icms_tot, "vNF", None) is not None:
            try:
                valor_total = Decimal(str(icms_tot.vNF))
            except Exception:
                pass

    # 7. Itens (det)
    det_list = getattr(inf, "det", None) or getattr(inf, "Det", None) or []
    itens = []
    for d in det_list:
        prod = getattr(d, "prod", None) or getattr(d, "Prod", None)
        if not prod:
            continue
        c_prod = str(getattr(prod, "cProd", "") or "").strip()
        x_prod = str(getattr(prod, "xProd", "") or "").strip()
        ncm = str(getattr(prod, "NCM", "") or "").strip() or None
        cfop = str(getattr(prod, "CFOP", "") or "").strip() or None
        u_com = str(getattr(prod, "uCom", "") or "").strip() or "UN"

        try:
            q_com = Decimal(str(getattr(prod, "qCom", 0) or 0))
        except Exception:
            q_com = Decimal("0.00")

        try:
            v_un_com = Decimal(str(getattr(prod, "vUnCom", 0) or 0))
        except Exception:
            v_un_com = Decimal("0.00")

        try:
            v_prod = Decimal(str(getattr(prod, "vProd", 0) or 0))
        except Exception:
            v_prod = q_com * v_un_com

        itens.append({
            "codigo": c_prod,
            "descricao": x_prod,
            "ncm": ncm,
            "cfop": cfop,
            "unidade": u_com,
            "quantidade": q_com,
            "valor_unitario": v_un_com,
            "valor_total": v_prod,
        })

    return {
        "chave_nfe": chave_nfe,
        "numero_nf": numero_nf,
        "serie": serie,
        "data_emissao": data_emissao,
        "emitente_cnpj": emitente_cnpj,
        "emitente_nome": emitente_nome,
        "destinatario_doc": destinatario_doc,
        "destinatario_nome": destinatario_nome,
        "valor_total": valor_total,
        "itens": itens,
    }
