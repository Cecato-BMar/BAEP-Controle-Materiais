import logging
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from estoque.models import (
    MovimentacaoEstoque,
    Fornecedor,
    Produto,
    Categoria,
    UnidadeMedida,
    AnexoMovimentacao,
)
from .nfe_xml_parser import parse_nfe_xml

logger = logging.getLogger(__name__)


@transaction.atomic
def process_nfe_xml(
    xml_bytes: bytes,
    empenho: str | None = None,
    usuario: User | None = None,
    xml_filename: str | None = None,
) -> dict[str, Any]:
    """
    Processa o XML de uma NF-e (usando parse_nfe_xml e nfelib) e persiste/atualiza
    as movimentações de estoque correspondentes com garantia de idempotência.

    - Nota Fiscal é obrigatória; Nota de Empenho é opcional.
    - Se empenho for None/vazio, grava documento_referencia=None e status_empenho='SEM_EMPENHO'.
    - Se a NF já existir e chegar o empenho depois, atualiza o registro existente sem duplicar saldo.
    - Usa chave natural: chave_nfe (44 dígitos) ou combinação (numero_nf + fornecedor).
    - Loga: "NF recebida sem empenho; registro criado/atualizado" quando sem empenho.
    """
    # 1. Parse do XML com nfelib
    parsed = parse_nfe_xml(xml_bytes)

    numero_nf = parsed["numero_nf"]
    chave_nfe = parsed.get("chave_nfe")
    itens = parsed.get("itens") or []
    if not itens:
        raise ValueError("NF-e sem itens de produto para dar entrada.")

    # 2. Resolução do usuário responsável
    if not usuario or not usuario.is_authenticated:
        usuario = User.objects.filter(is_superuser=True).first() or User.objects.first()

    # 3. Resolução ou criação do Fornecedor
    fornecedor = None
    emitente_cnpj = parsed.get("emitente_cnpj")
    if emitente_cnpj:
        fornecedor, _ = Fornecedor.objects.get_or_create(
            documento=emitente_cnpj,
            defaults={
                "nome": parsed.get("emitente_nome") or emitente_cnpj,
                "tipo_pessoa": "JURIDICA",
            },
        )

    empenho_limpo = str(empenho).strip() if empenho and str(empenho).strip() else None

    # 4. Criar ou atualizar produtos e movimentações por item (Idempotência)
    criadas = []
    atualizadas = []
    now = timezone.now()
    data_mov = parsed.get("data_emissao") or now.date()

    for item in itens:
        c_prod = item.get("codigo") or ""
        x_prod = item.get("descricao") or ""
        u_com = item.get("unidade") or "UN"
        qtd = Decimal(str(item.get("quantidade", 0)))
        v_unit = Decimal(str(item.get("valor_unitario", 0)))

        # Resolução do Produto
        produto = None
        if c_prod:
            produto = Produto.objects.filter(codigo=c_prod).first()
        if not produto and x_prod:
            produto = Produto.objects.filter(nome__iexact=x_prod).first()
        if not produto:
            cat_default, _ = Categoria.objects.get_or_create(
                nome="Geral", defaults={"codigo": "CAT-GER"}
            )
            unid_default, _ = UnidadeMedida.objects.get_or_create(
                sigla=u_com[:10].upper(), defaults={"nome": u_com}
            )
            # Evita colisão de código
            cod_final = c_prod if (c_prod and not Produto.objects.filter(codigo=c_prod).exists()) else f"MAT-{Produto.objects.count() + 1:04d}"
            produto = Produto.objects.create(
                codigo=cod_final,
                nome=x_prod[:200],
                categoria=cat_default,
                unidade_medida=unid_default,
                status="ATIVO",
                criado_por=usuario,
            )

        # Chave natural para compra nova:
        # Preferir chave_nfe + produto; se não houver chave_nfe, usar nota_fiscal + fornecedor + produto
        lookup = {
            "subtipo": "COMPRA_NOVA",
            "produto": produto,
        }
        if chave_nfe:
            lookup["chave_nfe"] = chave_nfe
        else:
            lookup["nota_fiscal"] = numero_nf
            if fornecedor:
                lookup["fornecedor"] = fornecedor

        existing_mov = MovimentacaoEstoque.objects.filter(**lookup).first()

        if existing_mov:
            # Atualização idempotente (ex: empenho que chegou a posteriori)
            updated_fields = []
            if empenho_limpo and existing_mov.documento_referencia != empenho_limpo:
                existing_mov.documento_referencia = empenho_limpo
                updated_fields.append("documento_referencia")
            if fornecedor and not existing_mov.fornecedor_id:
                existing_mov.fornecedor = fornecedor
                updated_fields.append("fornecedor")
            if chave_nfe and not existing_mov.chave_nfe:
                existing_mov.chave_nfe = chave_nfe
                updated_fields.append("chave_nfe")
            if data_mov and existing_mov.data_movimentacao != data_mov:
                existing_mov.data_movimentacao = data_mov
                updated_fields.append("data_movimentacao")

            if updated_fields:
                existing_mov.save(update_fields=updated_fields)

            atualizadas.append(existing_mov)
        else:
            # Criação de novo registro de entrada
            mov = MovimentacaoEstoque(
                produto=produto,
                subtipo="COMPRA_NOVA",
                tipo_movimentacao="ENTRADA",
                data_movimentacao=data_mov,
                quantidade=qtd,
                valor_unitario=v_unit,
                nota_fiscal=numero_nf,
                chave_nfe=chave_nfe,
                documento_referencia=empenho_limpo,
                fornecedor=fornecedor,
                usuario=usuario,
            )
            mov.save()
            criadas.append(mov)

    # 5. Salvar anexo do XML uma única vez
    todas_movs = criadas + atualizadas
    safe_name = xml_filename or f"nfe_{chave_nfe or numero_nf}_{now.strftime('%Y%m%d%H%M%S')}.xml"

    for m in todas_movs:
        if not AnexoMovimentacao.objects.filter(movimentacao=m, tipo="NFE").exists():
            anexo = AnexoMovimentacao(
                movimentacao=m,
                tipo="NFE",
                nome_original=safe_name,
                criado_por=usuario,
            )
            anexo.arquivo.save(safe_name, ContentFile(xml_bytes), save=True)

    # 6. Rastreabilidade e Log operacional
    status_flag = "COM_EMPENHO" if empenho_limpo else "SEM_EMPENHO"
    if not empenho_limpo:
        logger.info(
            "NF %s: NF recebida sem empenho; registro criado/atualizado (chave: %s, criadas: %d, atualizadas: %d)",
            numero_nf, chave_nfe or "-", len(criadas), len(atualizadas)
        )
    else:
        logger.info(
            "NF %s: NF recebida com empenho %s; registro criado/atualizado (chave: %s, criadas: %d, atualizadas: %d)",
            numero_nf, empenho_limpo, chave_nfe or "-", len(criadas), len(atualizadas)
        )

    return {
        "chave_nfe": chave_nfe,
        "numero_nf": numero_nf,
        "serie": parsed.get("serie"),
        "emitente_nome": parsed.get("emitente_nome"),
        "emitente_cnpj": parsed.get("emitente_cnpj"),
        "valor_total": parsed.get("valor_total"),
        "movimentacoes_criadas": len(criadas),
        "movimentacoes_atualizadas": len(atualizadas),
        "status_empenho": status_flag,
        "ids": [m.pk for m in todas_movs],
    }
