"""Re-export para compatibilidade de integracoes.services.backup."""

from integracoes.backup import (
    BACKUP_DIR,
    cleanup_old_backups,
    create_db_backup,
    get_backup_dir,
    restore_db,
    serialize_instance,
)

__all__ = [
    "BACKUP_DIR",
    "get_backup_dir",
    "create_db_backup",
    "cleanup_old_backups",
    "restore_db",
    "serialize_instance",
]
