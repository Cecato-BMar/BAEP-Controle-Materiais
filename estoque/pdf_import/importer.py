import logging
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Any

from django.core.files.storage import default_storage
from django.db import transaction, models
from django.utils import timezone

from estoque.models import (
    MovimentacaoEstoque, Fornecedor, Produto, AnexoMovimentacao,
)

logger = logging.getLogger(__name__)


@transaction.atomic
def create_movimentacoes_from_import(
    request: Any,
    header_data: dict,
    items: list[dict],
    nfe_file: Any,
    empenho_file: Any = None,
) -> dict:
    """
    Cria ou atualiza MovimentacaoEstoque + AnexoMovimentacao por movimentação (compartilha arquivos físicos).
    Nota Fiscal é obrigatória. Nota de Empenho é opcional.
    Se já existirem registros para a mesma NF e produto, atualiza o documento_referencia e anexos
    em vez de duplicar registros ou saldos de estoque.
    Executa em transação atômica — se qualquer item falhar, nada é persistido.
    """
    # ── 1. Validar header
    nota_fiscal = (header_data.get("nota_fiscal") or "").strip()
    doc_ref = (header_data.get("documento_referencia") or "").strip() or None
    data_raw = header_data.get("data_movimentacao")

    if not nota_fiscal:
        raise ValueError("Número da NF é obrigatório.")
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
    empenho_stored_path = None
    if empenho_file:
        empenho_stored_path = default_storage.save(
            f"{prefix}/empenho_{doc_ref or 'ref'}_{now.strftime('%Y%m%d%H%M%S')}.pdf",
            empenho_file,
        )

    # ── 5. Criar ou Atualizar MovimentacaoEstoque (Idempotência por Chave Natural)
    mov_query = MovimentacaoEstoque.objects.filter(
        nota_fiscal=nota_fiscal,
        subtipo="COMPRA_NOVA",
    )
    if fornecedor:
        mov_query = mov_query.filter(
            models.Q(fornecedor=fornecedor) | models.Q(fornecedor__isnull=True)
        )

    existing_movs = list(mov_query)
    matched_existing_ids = set()

    movs = []
    movs_criadas = []
    movs_atualizadas = []

    for item in items:
        pid = item["produto_id"]
        qtd = Decimal(str(item["quantidade"]))
        vunit = Decimal(str(item["valor_unitario"]))
        obs = item.get("observacoes", "")

        existing_mov = None
        for m in existing_movs:
            if m.produto_id == pid and m.pk not in matched_existing_ids:
                existing_mov = m
                matched_existing_ids.add(m.pk)
                break

        if existing_mov:
            updated_fields = []
            if doc_ref and existing_mov.documento_referencia != doc_ref:
                existing_mov.documento_referencia = doc_ref
                updated_fields.append("documento_referencia")
            if fornecedor and not existing_mov.fornecedor_id:
                existing_mov.fornecedor = fornecedor
                updated_fields.append("fornecedor")
            if data_mov and existing_mov.data_movimentacao != data_mov:
                existing_mov.data_movimentacao = data_mov
                updated_fields.append("data_movimentacao")
            if obs and existing_mov.observacoes != obs:
                existing_mov.observacoes = obs
                updated_fields.append("observacoes")

            if updated_fields:
                existing_mov.save(update_fields=updated_fields)

            movs_atualizadas.append(existing_mov)
            movs.append(existing_mov)
        else:
            mov = MovimentacaoEstoque(
                produto_id=pid,
                subtipo="COMPRA_NOVA",       # tipo_movimentacao é derivado no save()
                data_movimentacao=data_mov,
                quantidade=qtd,
                valor_unitario=vunit,
                nota_fiscal=nota_fiscal,
                documento_referencia=doc_ref,
                fornecedor=fornecedor,
                observacoes=obs,
                usuario=request.user,
            )
            mov._request = request       # injeta request para capturar ip_address
            mov.save()
            movs_criadas.append(mov)
            movs.append(mov)

    # ── 6. Criar AnexoMovimentacao por movimentação (compartilhando os paths salvos)
    novos_anexos = 0
    for mov in movs:
        if nfe_stored_path:
            if not AnexoMovimentacao.objects.filter(movimentacao=mov, tipo="NFE").exists():
                AnexoMovimentacao.objects.create(
                    movimentacao=mov,
                    tipo="NFE",
                    arquivo=nfe_stored_path,
                    nome_original=getattr(nfe_file, "name", "nfe.pdf"),
                    criado_por=request.user,
                )
                novos_anexos += 1

        if empenho_stored_path:
            if not AnexoMovimentacao.objects.filter(movimentacao=mov, tipo="EMPENHO").exists():
                AnexoMovimentacao.objects.create(
                    movimentacao=mov,
                    tipo="EMPENHO",
                    arquivo=empenho_stored_path,
                    nome_original=getattr(empenho_file, "name", "empenho.pdf"),
                    criado_por=request.user,
                )
                novos_anexos += 1

    status_flag = "COM_EMPENHO" if doc_ref else "SEM_EMPENHO"
    if not doc_ref:
        logger.info(
            "NF %s: NF recebida sem empenho; registro criado/atualizado (criadas: %d, atualizadas: %d)",
            nota_fiscal, len(movs_criadas), len(movs_atualizadas)
        )
    else:
        logger.info(
            "NF %s: NF recebida com empenho %s; registro criado/atualizado (criadas: %d, atualizadas: %d)",
            nota_fiscal, doc_ref, len(movs_criadas), len(movs_atualizadas)
        )

    return {
        "movimentacoes_criadas": len(movs_criadas),
        "movimentacoes_atualizadas": len(movs_atualizadas),
        "anexos_criados": novos_anexos,
        "ids": [m.pk for m in movs],
        "status_empenho": status_flag,
    }
