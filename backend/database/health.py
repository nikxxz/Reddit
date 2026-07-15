from __future__ import annotations

from dataclasses import dataclass

from backend.database.connection import get_connection
from backend.database.migrations import CURRENT_SCHEMA_VERSION


@dataclass(frozen=True)
class DatabaseHealth:
    ready: bool
    writable: bool
    schema_version: int | None
    expected_schema_version: int
    migration_required: bool
    last_error_code: str | None = None


def check_database_health() -> DatabaseHealth:
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
            foreign_keys = int(connection.execute("PRAGMA foreign_keys").fetchone()[0] or 0)
            schema_row = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
            schema_version = 0
            if schema_row:
                version_row = connection.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
                schema_version = int(version_row["version"] or 0)
            writable = not bool(connection.execute("PRAGMA query_only").fetchone()[0])
            migration_required = schema_version < CURRENT_SCHEMA_VERSION
            ready = bool(foreign_keys) and writable and not migration_required
            code = None
            if not writable:
                code = "database_read_only"
            elif migration_required:
                code = "schema_mismatch"
            elif not foreign_keys:
                code = "foreign_keys_disabled"
            return DatabaseHealth(
                ready=ready,
                writable=writable,
                schema_version=schema_version,
                expected_schema_version=CURRENT_SCHEMA_VERSION,
                migration_required=migration_required,
                last_error_code=code,
            )
    except Exception:
        return DatabaseHealth(
            ready=False,
            writable=False,
            schema_version=None,
            expected_schema_version=CURRENT_SCHEMA_VERSION,
            migration_required=False,
            last_error_code="database_unavailable",
        )
