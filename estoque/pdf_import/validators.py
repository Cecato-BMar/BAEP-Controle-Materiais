import re
from decimal import Decimal


def _normalize_cnpj(cnpj: str | None) -> str | None:
    if not cnpj:
        return None
    clean = re.sub(r"\D", "", str(cnpj))
    return clean if clean else None


def validate_nfe_vs_empenho(nfe: dict, empenho: dict) -> dict:
    """
    Valida consistência entre os dois documentos (NFe e Nota de Empenho).
    
    Retorna:
    {
        "valid": bool,                    # True se não houver erros bloqueantes
        "errors": [str, ...],             # bloqueantes (import não deve prosseguir)
        "warnings": [str, ...],           # não bloqueantes (operador deve revisar)
        "checks": {
            "cnpj_match": bool,
            "valor_match": bool,
            "empenho_ref_match": bool,
            "totais_itens_match": bool,
        }
    }
    """
    errors = []
    warnings = []

    # 1. CNPJ Match
    cnpj_nfe = _normalize_cnpj(nfe.get("emitente", {}).get("cnpj") if isinstance(nfe.get("emitente"), dict) else None)
    cnpj_emp = _normalize_cnpj(empenho.get("credor", {}).get("cnpj") if isinstance(empenho.get("credor"), dict) else None)

    cnpj_match = False
    if cnpj_nfe and cnpj_emp:
        if cnpj_nfe == cnpj_emp:
            cnpj_match = True
        else:
            errors.append(f"CNPJ do emitente da NFe ({cnpj_nfe}) difere do CNPJ do credor no Empenho ({cnpj_emp}).")
    else:
        warnings.append("Não foi possível comparar CNPJs: CNPJ ausente na NFe ou no Empenho (possível falha de OCR/leitura).")

    # 2. Valor Total Match
    valor_nfe = nfe.get("valor_total_nota")
    valor_emp = empenho.get("valor_empenho")

    valor_match = False
    if valor_nfe is not None and valor_emp is not None:
        try:
            diff = abs(Decimal(str(valor_nfe)) - Decimal(str(valor_emp)))
            if diff <= Decimal("0.01"):
                valor_match = True
            else:
                errors.append(f"Valor total da NFe (R$ {valor_nfe}) diverge do valor da Nota de Empenho (R$ {valor_emp}).")
        except Exception:
            errors.append("Erro ao calcular e comparar os valores monetários totais.")
    else:
        warnings.append("Valor total ausente na NFe ou no Empenho.")

    # 3. Empenho de Referência Match
    emp_ref = nfe.get("empenho_referencia")
    num_emp = empenho.get("numero_empenho")

    empenho_ref_match = False
    if emp_ref and num_emp:
        emp_ref_clean = emp_ref.strip().upper()
        num_emp_clean = num_emp.strip().upper()
        if emp_ref_clean == num_emp_clean:
            empenho_ref_match = True
        else:
            errors.append(f"Número de empenho referenciado na NFe ({emp_ref}) não confere com o Empenho importado ({num_emp}).")
    else:
        warnings.append("Número de empenho de referência não encontrado nas observações da NFe ou número de empenho ausente.")

    # 4. Totais dos Itens vs Valor Total da Nota
    totais_itens_match = False
    itens_nfe = nfe.get("itens") or []
    if itens_nfe and valor_nfe is not None:
        try:
            soma_itens = sum(
                Decimal(str(item["valor_total"]))
                for item in itens_nfe
                if item.get("valor_total") is not None
            )
            if abs(soma_itens - Decimal(str(valor_nfe))) <= Decimal("0.01"):
                totais_itens_match = True
            else:
                warnings.append(
                    f"A soma dos itens da NFe (R$ {soma_itens:.2f}) diverge do valor total da nota (R$ {valor_nfe}). "
                    "Verifique se algum item não foi capturado pelo OCR."
                )
        except Exception:
            warnings.append("Falha ao somar valores dos itens da NFe.")
    else:
        warnings.append("Itens da NFe ou valor total da nota não disponíveis para conferência de soma dos itens.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "checks": {
            "cnpj_match": cnpj_match,
            "valor_match": valor_match,
            "empenho_ref_match": empenho_ref_match,
            "totais_itens_match": totais_itens_match,
        },
    }
