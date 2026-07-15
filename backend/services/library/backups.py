from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic

from backend.config import settings
from backend.core.paths import get_backup_root, get_database_path
from backend.database.connection import connect
from backend.utils.logging import get_logger


logger = get_logger(__name__)
BACKUP_PREFIX = "reddit_media_library_"


def create_pre_migration_backup(schema_version: int) -> Path:
    timestamp = _stamp()
    filename = f"reddit_media_library_pre_migration_v{schema_version}_{timestamp}.sqlite3"
    return _backup_to(filename, fail_hard=True)


def create_routine_backup_if_due() -> Path | None:
    root = get_backup_root()
    root.mkdir(parents=True, exist_ok=True)
    latest = _latest_backup(root)
    if latest and datetime.now(timezone.utc).timestamp() - latest.stat().st_mtime < settings.database_backup_interval_hours * 3600:
        return None
    try:
        path = _backup_to(f"{BACKUP_PREFIX}{_stamp()}.sqlite3", fail_hard=False)
        prune_backups()
        return path
    except Exception:
        logger.exception("library.backup.failed")
        return None


def backup_status() -> tuple[bool, str | None]:
    latest = _latest_backup(get_backup_root())
    if not latest:
        return False, None
    return True, datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc).isoformat()


def prune_backups() -> int:
    root = get_backup_root()
    backups = sorted(root.glob(f"{BACKUP_PREFIX}*.sqlite3"), key=lambda path: path.stat().st_mtime, reverse=True)
    removed = 0
    for path in backups[settings.database_backup_retention :]:
        path.unlink(missing_ok=True)
        removed += 1
    logger.info("library.backup.retention.completed backups_removed=%s", removed)
    return removed


def _backup_to(filename: str, *, fail_hard: bool) -> Path:
    started = monotonic()
    database = get_database_path()
    target = get_backup_root() / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if not database.exists():
        return target
    logger.info("library.backup.start backup_filename=%s", target.name)
    try:
        source = connect(database)
        destination = sqlite3.connect(target)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        logger.info(
            "library.backup.completed backup_filename=%s backup_size_bytes=%s elapsed_ms=%s",
            target.name,
            target.stat().st_size,
            int((monotonic() - started) * 1000),
        )
        return target
    except Exception:
        logger.exception("library.backup.failed backup_filename=%s", target.name)
        if fail_hard:
            raise
        return target


def _latest_backup(root: Path) -> Path | None:
    if not root.exists():
        return None
    backups = [*root.glob(f"{BACKUP_PREFIX}*.sqlite3"), *root.glob("reddit_media_library_pre_migration_v*.sqlite3")]
    if not backups:
        return None
    return max(backups, key=lambda path: path.stat().st_mtime)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
