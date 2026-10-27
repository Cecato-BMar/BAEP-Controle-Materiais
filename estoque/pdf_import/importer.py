import re
from datetime import datetime, date
from decimal import Decimal
from typing import Any

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from estoque.models import (
    MovimentacaoEstoque, Fornecedor, Produto, AnexoMovimentacao,
)


@transaction.atomic
def create_movimentacoes_from_import(
    request: Any,
    header_data: dict,
    items: list[dict],
    nfe_file: Any,
    empenho_file: Any,
) -> dict:
    """
    Cria N MovimentacaoEstoque + 2 AnexoMovimentacao por movimentação (compartilha arquivos físicos).
    Executa em transação atômica — se qualquer item falhar, nada é persistido.
    """
    # ── 1. Validar header
    nota_fiscal = (header_data.get("nota_fiscal") or "").strip()
    doc_ref = (header_data.get("documento_referencia") or "").strip()
    data_raw = header_data.get("data_movimentacao")

    if not nota_fiscal:
        raise ValueError("Número da NF é obrigatório.")
    if not doc_ref:
        raise ValueError("Número do Empenho é obrigatório.")
    if not data_raw:
        raise ValueError("Data da movimentação é obrigatória.")

    if isinstance(data_raw, date):
        data_mov = data_raw
    else:
        try:
            data_mov = datetime.strptime(str(data_raw)[:10], "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Data inválida. Use formato YYYY-MM-DD.")

    # ── 2. Resolver fornecedor (normalizando documento para dígitos puros)
    fornecedor = None
    fornecedor_id = header_data.get("fornecedor_id")
    if fornecedor_id:
        fornecedor = Fornecedor.objects.filter(pk=fornecedor_id).first()

    if not fornecedor:
        cnpj_raw = header_data.get("fornecedor_cnpj") or ""
        cnpj_limpo = re.sub(r"\D", "", str(cnpj_raw))
        if cnpj_limpo:
            fornecedor, _ = Fornecedor.objects.get_or_create(
                documento=cnpj_limpo,
                defaults={
                    "nome": header_data.get("fornecedor_nome") or cnpj_limpo,
                    "tipo_pessoa": "JURIDICA",
                },
            )

    # ── 3. Validar items
    if not items:
        raise ValueError("Nenhum item para importar.")

    for i, item in enumerate(items, start=1):
        pid = item.get("produto_id")
        if not pid:
            raise ValueError(f"Item {i}: produto não selecionado.")
        try:
            qtd = Decimal(str(item.get("quantidade", 0)))
        except Exception:
            raise ValueError(f"Item {i}: quantidade inválida.")
        if qtd <= 0:
            raise ValueError(f"Item {i}: quantidade deve ser > 0.")
        try:
            vunit = Decimal(str(item.get("valor_unitario", 0)))
        except Exception:
            raise ValueError(f"Item {i}: valor unitário inválido.")
        if vunit < 0:
            raise ValueError(f"Item {i}: valor unitário não pode ser negativo.")
        if not Produto.objects.filter(pk=pid).exists():
            raise ValueError(f"Item {i}: produto ID {pid} não existe.")

    # ── 4. Salvar PDFs UMA vez (evitar N cópias físicas em disco)
    now = timezone.now()
    prefix = f"comprovantes_estoque/{now.year}/{now.month:02d}"

    nfe_stored_path = default_storage.save(
        f"{prefix}/nfe_{nota_fiscal}_{now.strftime('%Y%m%d%H%M%S')}.pdf",
        nfe_file,
    )
    empenho_stored_path = default_storage.save(
        f"{prefix}/empenho_{doc_ref}_{now.strftime('%Y%m%d%H%M%S')}.pdf",
        empenho_file,
    )

    # ── 5. Criar N MovimentacaoEstoque
    movs = []
    for item in items:
        qtd = Decimal(str(item["quantidade"]))
        vunit = Decimal(str(item["valor_unitario"]))

        mov = MovimentacaoEstoque(
            produto_id=item["produto_id"],
            subtipo="COMPRA_NOVA",       # tipo_movimentacao é derivado no save()
            data_movimentacao=data_mov,
            quantidade=qtd,
            valor_unitario=vunit,
            nota_fiscal=nota_fiscal,
            documento_referencia=doc_ref,
            fornecedor=fornecedor,
            observacoes=item.get("observacoes", ""),
            usuario=request.user,
        )
        if hasattr(mov, "_request") or True:
            mov._request = request       # injeta request para capturar ip_address
        mov.save()
        movs.append(mov)

    # ── 6. Criar 2 AnexoMovimentacao por movimentação (compartilhando os paths salvos)
    for mov in movs:
        AnexoMovimentacao.objects.create(
            movimentacao=mov,
            tipo="NFE",
            arquivo=nfe_stored_path,
            nome_original=getattr(nfe_file, "name", "nfe.pdf"),
            criado_por=request.user,
        )
        AnexoMovimentacao.objects.create(
            movimentacao=mov,
            tipo="EMPENHO",
            arquivo=empenho_stored_path,
            nome_original=getattr(empenho_file, "name", "empenho.pdf"),
            criado_por=request.user,
        )

    return {
        "movimentacoes_criadas": len(movs),
        "anexos_criados": len(movs) * 2,
        "ids": [m.pk for m in movs],
    }
