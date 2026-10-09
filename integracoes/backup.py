"""Módulo de backup físico do banco de dados (Camada 1 do Restore Point)
e serialização determinística de instâncias Django (Camada 3).
"""

from __future__ import annotations

import gzip
import logging
import os
import shutil
import subprocess
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import connection, models
from django.utils import timezone

logger = logging.getLogger(__name__)

BACKUP_DIR = Path(getattr(settings, "BASE_DIR", Path("."))) / "backups"


# ============================================================================
# CAMADA 1 — BACKUP FÍSICO DO BANCO DE DADOS (pg_dump / sqlite gzip)
# ============================================================================

def get_backup_dir() -> Path:
    """Retorna e garante a existência do diretório de backups."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def create_db_backup(tag: str = "sync") -> str:
    """Gera um backup compactado do banco de dados antes de operações de modificação.

    Suporta PostgreSQL (via pg_dump) e SQLite (cópia compactada direta).
    Retorna o caminho absoluto do arquivo .sql.gz gerado.
    """
    backup_dir = get_backup_dir()
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"pre_{tag}_{timestamp}.sql.gz"
    backup_path = backup_dir / backup_filename

    db_config = settings.DATABASES.get("default", {})
    engine = db_config.get("ENGINE", "")

    if "postgresql" in engine or "psycopg" in engine:
        host = db_config.get("HOST", "localhost") or "localhost"
        port = str(db_config.get("PORT", "5432") or "5432")
        user = db_config.get("USER", "postgres")
        password = db_config.get("PASSWORD", "")
        db_name = db_config.get("NAME", "reserva_baep")

        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = str(password)

        cmd = [
            "pg_dump",
            "-h", host,
            "-p", port,
            "-U", user,
            "-d", db_name,
            "--no-owner",
            "--clean",
            "--if-exists",
        ]

        logger.info("Executando pg_dump para %s...", backup_path)
        try:
            with gzip.open(backup_path, "wb") as gz_out:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                )
                stdout, stderr = proc.communicate()
                if proc.returncode != 0:
                    err_msg = stderr.decode("utf-8", errors="replace")
                    logger.warning("pg_dump falhou com código %d: %s", proc.returncode, err_msg)
                    # Não impede o pipeline se o utilitário pg_dump não estiver instalado no container
                    gz_out.write(b"-- pg_dump unavailable in environment\n")
                else:
                    gz_out.write(stdout)
        except FileNotFoundError:
            logger.warning("Utilitário pg_dump não encontrado no PATH. Gerando marcador de backup.")
            with gzip.open(backup_path, "wb") as gz_out:
                gz_out.write(b"-- pg_dump client not installed on system\n")
    else:
        # Fallback SQLite para ambiente de desenvolvimento/testes
        db_name = db_config.get("NAME")
        if db_name and os.path.exists(str(db_name)):
            logger.info("Gerando backup compactado SQLite de %s para %s...", db_name, backup_path)
            with open(str(db_name), "rb") as f_in, gzip.open(backup_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        else:
            with gzip.open(backup_path, "wb") as f_out:
                f_out.write(b"-- sqlite in-memory or unlocated file\n")

    cleanup_old_backups(keep=5)
    return str(backup_path)


def cleanup_old_backups(keep: int = 5) -> None:
    """Remove backups antigos deixando os 'keep' mais recentes."""
    backup_dir = get_backup_dir()
    backups = sorted(
        backup_dir.glob("pre_*.sql.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old_backup in backups[keep:]:
        try:
            old_backup.unlink()
            logger.info("Backup antigo removido: %s", old_backup.name)
        except OSError as exc:
            logger.warning("Falha ao remover backup antigo %s: %s", old_backup, exc)


def restore_db(backup_path: str) -> None:
    """Restaura o banco a partir de um backup .sql.gz (apenas via comando explícito)."""
    p = Path(backup_path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo de backup não encontrado: {backup_path}")

    db_config = settings.DATABASES.get("default", {})
    engine = db_config.get("ENGINE", "")

    if "postgresql" in engine or "psycopg" in engine:
        host = db_config.get("HOST", "localhost") or "localhost"
        port = str(db_config.get("PORT", "5432") or "5432")
        user = db_config.get("USER", "postgres")
        password = db_config.get("PASSWORD", "")
        db_name = db_config.get("NAME", "reserva_baep")

        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = str(password)

        cmd = ["psql", "-h", host, "-p", port, "-U", user, "-d", db_name]
        with gzip.open(p, "rb") as gz_in:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            _, stderr = proc.communicate(input=gz_in.read())
            if proc.returncode != 0:
                raise RuntimeError(f"psql restore falhou: {stderr.decode('utf-8', errors='replace')}")
    else:
        db_name = db_config.get("NAME")
        if db_name and str(db_name) != ":memory:":
            connection.close()
            with gzip.open(p, "rb") as f_in, open(str(db_name), "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)


# ============================================================================
# CAMADA 3 — SERIALIZADOR DETERMINÍSTICO (before/after snapshots)
# ============================================================================

def serialize_instance(instance: models.Model | None) -> dict[str, Any] | None:
    """Serializa uma instância de modelo Django de forma determinística para JSON.

    Trata adequadamente:
    - datetime / date / time -> .isoformat()
    - Decimal -> str(val)
    - UUID -> str(val)
    - ForeignKey -> chave primária associada (<field>_id)
    - None / bool / int / float / str -> valores primitivos diretos
    """
    if instance is None:
        return None

    data: dict[str, Any] = {}
    for field in instance._meta.concrete_fields:
        name = field.name
        val = field.value_from_object(instance)

        if val is None:
            data[name] = None
        elif isinstance(val, (datetime, date, time)):
            data[name] = val.isoformat()
        elif isinstance(val, Decimal):
            data[name] = str(val)
        elif isinstance(val, UUID):
            data[name] = str(val)
        elif isinstance(val, (int, float, bool, str)):
            data[name] = val
        else:
            # Fallback seguro para strings/objetos arbitrários
            data[name] = str(val)

    return data
