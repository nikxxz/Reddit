from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from backend.database.connection import get_connection
from backend.services.library.backups import create_pre_migration_backup
from backend.utils.logging import get_logger


logger = get_logger(__name__)
CURRENT_SCHEMA_VERSION = 1

MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "initial_library",
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS app_metadata (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS downloads (
            id TEXT PRIMARY KEY,
            job_id TEXT UNIQUE,
            post_id TEXT NOT NULL,
            source_post_id TEXT,
            reddit_permalink TEXT,
            title TEXT,
            subreddit TEXT,
            author TEXT,
            media_type TEXT,
            provider TEXT,
            download_scope TEXT,
            status TEXT NOT NULL,
            availability TEXT NOT NULL,
            error_code TEXT,
            error_message TEXT,
            retry_of_id TEXT REFERENCES downloads(id),
            resolver_version TEXT,
            normalized_media_json TEXT,
            expected_file_count INTEGER,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            last_verified_at TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS download_files (
            id TEXT PRIMARY KEY,
            download_id TEXT NOT NULL REFERENCES downloads(id) ON DELETE CASCADE,
            gallery_index INTEGER,
            relative_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            category TEXT NOT NULL,
            extension TEXT,
            mime_type TEXT,
            size_bytes INTEGER,
            width INTEGER,
            height INTEGER,
            duration_seconds REAL,
            checksum_sha256 TEXT,
            exists_on_disk INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            last_verified_at TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(download_id, relative_path)
        );

        CREATE TABLE IF NOT EXISTS download_thumbnails (
            id TEXT PRIMARY KEY,
            download_id TEXT NOT NULL REFERENCES downloads(id) ON DELETE CASCADE,
            source_file_id TEXT REFERENCES download_files(id) ON DELETE SET NULL,
            relative_path TEXT,
            source_type TEXT NOT NULL,
            width INTEGER,
            height INTEGER,
            exists_on_disk INTEGER NOT NULL,
            generated_at TEXT,
            last_verified_at TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS download_events (
            id TEXT PRIMARY KEY,
            download_id TEXT NOT NULL REFERENCES downloads(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            message TEXT,
            created_at TEXT NOT NULL
        );
        """,
    )
]


def initialize_database() -> None:
    with get_connection() as connection:
        existing = _schema_exists(connection)
        current = _current_version(connection) if existing else 0
    if existing and current < CURRENT_SCHEMA_VERSION:
        create_pre_migration_backup(current)
    with get_connection() as connection:
        for version, name, sql in MIGRATIONS:
            if version <= _current_version(connection):
                continue
            logger.info("library.migration.apply version=%s name=%s", version, name)
            connection.executescript(sql)
            connection.execute(
                "INSERT OR REPLACE INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
                (version, name, _now()),
            )


def get_schema_version() -> int:
    with get_connection() as connection:
        return _current_version(connection)


def _schema_exists(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    return row is not None


def _current_version(connection: sqlite3.Connection) -> int:
    if not _schema_exists(connection):
        return 0
    row = connection.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
    return int(row["version"] or 0)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
