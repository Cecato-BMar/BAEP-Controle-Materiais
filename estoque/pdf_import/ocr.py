import logging
import os
import re
import shutil
from io import BytesIO
from pathlib import Path
from typing import Union, BinaryIO

from PIL import Image
from pdf2image import convert_from_bytes, convert_from_path
import pytesseract
from pyzbar.pyzbar import decode

logger = logging.getLogger(__name__)


def get_tesseract_cmd() -> str:
    """
    Identifica o executável do Tesseract-OCR na seguinte ordem de prioridade:
    1. Variável de ambiente TESSERACT_CMD
    2. Binário no PATH do sistema operacional (Docker Linux: /usr/bin/tesseract, etc.)
    3. Locais comuns no Windows
    """
    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd and os.path.exists(env_cmd):
        return env_cmd

    which_cmd = shutil.which("tesseract")
    if which_cmd:
        return which_cmd

    for win_path in [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
    ]:
        if os.path.exists(win_path):
            return win_path

    return ""


def get_poppler_path() -> str | None:
    """
    Identifica o diretório de binários do Poppler (contendo pdftoppm):
    1. Variável de ambiente POPPLER_PATH
    2. PATH do sistema operacional (Docker Linux / poppler-utils nativo) -> retorna None para pdf2image usar o PATH
    3. Locais comuns no Windows (C:\\poppler\\Library\\bin, etc.)
    """
    env_poppler = os.environ.get("POPPLER_PATH")
    if env_poppler and os.path.exists(env_poppler):
        return env_poppler

    if shutil.which("pdftoppm"):
        return None

    for win_dir in [
        r"C:\poppler\Library\bin",
        r"C:\poppler\bin",
        os.path.expandvars(r"%LOCALAPPDATA%\poppler\Library\bin"),
    ]:
        if os.path.exists(win_dir):
            return win_dir

    return None


def ensure_tesseract() -> str:
    """
    Valida a presença do Tesseract e configura pytesseract.
    Levanta RuntimeError com mensagem explicativa se o binário não for encontrado.
    """
    cmd = get_tesseract_cmd()
    if not cmd:
        raise RuntimeError(
            "Tesseract-OCR não foi encontrado no sistema. "
            "Certifique-se de que o Tesseract está instalado no sistema ou configure a variável de ambiente TESSERACT_CMD."
        )
    pytesseract.pytesseract.tesseract_cmd = cmd
    return cmd


def get_lang() -> str:
    """Retorna 'por' se o pacote de idioma português estiver disponível no Tesseract, senão 'eng'."""
    try:
        ensure_tesseract()
        langs = pytesseract.get_languages()
        if "por" in langs:
            return "por"
    except RuntimeError:
        raise
    except Exception as e:
        logger.warning(f"Não foi possível obter idiomas instalados do Tesseract: {e}")
    return "eng"


def read_file_bytes(file_obj: Union[str, Path, BinaryIO, bytes]) -> bytes:
    """
    Extrai bytes de qualquer fonte de arquivo (caminho, UploadedFile, BytesIO ou bytes).
    Preserva a posição do cursor caso o objeto seja seekable.
    """
    if isinstance(file_obj, (str, Path)):
        with open(file_obj, "rb") as f:
            return f.read()
    if isinstance(file_obj, bytes):
        return file_obj
    if hasattr(file_obj, "read"):
        pos = None
        if hasattr(file_obj, "tell") and hasattr(file_obj, "seek"):
            try:
                pos = file_obj.tell()
            except Exception:
                pos = None
        data = file_obj.read()
        if pos is not None and hasattr(file_obj, "seek"):
            try:
                file_obj.seek(pos)
            except Exception:
                pass
        return data
    raise ValueError(f"Tipo de arquivo não suportado: {type(file_obj)}")


def read_chave_from_barcode(file_obj: Union[str, Path, BinaryIO, bytes]) -> str | None:
    """
    Lê a chave de acesso (44 dígitos numéricos) do código de barras da DANFE via pyzbar.
    Retorna a chave com 44 dígitos se encontrada, ou None se:
    - O PDF não possuir código de barras
    - O barcode existir mas não tiver exatamente 44 dígitos
    - O arquivo for inválido / corrompido (loga warning e retorna None)
    """
    try:
        data = read_file_bytes(file_obj)
        if not data or not data.startswith(b"%PDF-"):
            return None

        poppler = get_poppler_path()
        images = convert_from_bytes(
            data,
            dpi=200,
            first_page=1,
            last_page=1,
            poppler_path=poppler,
        )
        if not images:
            logger.warning("Nenhuma imagem gerada para leitura do código de barras.")
            return None

        barcodes = decode(images[0])
        for b in barcodes:
            raw_text = b.data.decode("utf-8", errors="ignore").strip()
            digits = re.sub(r"\D", "", raw_text)
            if len(digits) == 44:
                return digits

        # Fallback: corte superior (região do cabeçalho da DANFE onde fica o Code 128)
        w, h = images[0].size
        top_crop = images[0].crop((0, 0, w, int(h * 0.4)))
        barcodes_top = decode(top_crop)
        for b in barcodes_top:
            raw_text = b.data.decode("utf-8", errors="ignore").strip()
            digits = re.sub(r"\D", "", raw_text)
            if len(digits) == 44:
                return digits

    except Exception as e:
        logger.warning(f"Falha ao ler código de barras da NFe: {e}", exc_info=True)

    return None


def extract_text_raw(file_obj: Union[str, Path, BinaryIO, bytes], config: str | None = None) -> str:
    """
    Executa OCR direto de todas as páginas do PDF (sem pré-processamento destrutivo).
    PDF -> Imagens de todas as páginas -> pytesseract com idioma configurado (por / eng).
    Concatena todas as páginas com '\n\n' para garantir leitura integral de notas multipágina.
    Por padrão, inclui leitura de layout geral e leitura tabular (--psm 6) para captura fiel de tabelas.
    Levanta RuntimeError com mensagem clara se o Tesseract não estiver instalado.
    Retorna string vazia com warning caso o arquivo seja inválido ou ocorra erro de imagem.
    """
    ensure_tesseract()
    try:
        data = read_file_bytes(file_obj)
        if not data or not data.startswith(b"%PDF-"):
            logger.warning("Arquivo fornecido para OCR não é um PDF válido.")
            return ""

        poppler = get_poppler_path()
        images = convert_from_bytes(data, dpi=200, poppler_path=poppler)
        if not images:
            logger.warning("Nenhuma página convertida para OCR.")
            return ""

        lang = get_lang()
        page_texts = []
        for i, img in enumerate(images):
            try:
                if config:
                    txt = pytesseract.image_to_string(img, lang=lang, config=config)
                    if txt:
                        page_texts.append(txt.strip())
                else:
                    txt_std = pytesseract.image_to_string(img, lang=lang)
                    if txt_std:
                        page_texts.append(txt_std.strip())
                    # Extração adicional com psm 6 para tabelas de produtos
                    txt_table = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
                    if txt_table and txt_table.strip() != txt_std.strip():
                        page_texts.append(txt_table.strip())
            except Exception as page_err:
                logger.warning(f"Erro no OCR da página {i}: {page_err}")

        return "\n\n".join(page_texts)

    except Exception as e:
        logger.warning(f"Erro durante a extração de texto OCR: {e}", exc_info=True)
        return ""

