from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.paths import resolve_download_path, to_relative_download_path
from backend.database.connection import get_connection


_schema_ready = False


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_download_record(
    *,
    job_id: str,
    post_id: str,
    title: str | None,
    subreddit: str | None,
    author: str | None,
    media_type: str,
    download_scope: str,
    status: str = "queued",
    retry_of_id: str | None = None,
) -> str:
    _ensure_schema()
    download_id = str(uuid.uuid4())
    timestamp = now()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO downloads(
                id, job_id, post_id, title, subreddit, author, media_type,
                download_scope, status, availability, retry_of_id, resolver_version,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'unknown', ?, 'resolver-v1', ?, ?)
            """,
            (
                download_id,
                job_id,
                post_id,
                title,
                subreddit,
                author,
                media_type,
                download_scope,
                status,
                retry_of_id,
                timestamp,
                timestamp,
            ),
        )
    return download_id


def update_download_status(
    job_id: str,
    status: str,
    *,
    error_code: str | None = None,
    error_message: str | None = None,
    expected_file_count: int | None = None,
) -> None:
    _ensure_schema()
    timestamp = now()
    fields = ["status = ?", "updated_at = ?"]
    values: list[Any] = [status, timestamp]
    if status in {"resolving", "downloading", "merging", "finalizing"}:
        fields.append("started_at = COALESCE(started_at, ?)")
        values.append(timestamp)
    if status in {"completed", "failed", "cancelled", "completed_with_errors"}:
        fields.append("completed_at = COALESCE(completed_at, ?)")
        values.append(timestamp)
    if error_code is not None:
        fields.append("error_code = ?")
        values.append(error_code)
    if error_message is not None:
        fields.append("error_message = ?")
        values.append(error_message)
    if expected_file_count is not None:
        fields.append("expected_file_count = ?")
        values.append(expected_file_count)
    values.append(job_id)
    with get_connection() as connection:
        connection.execute(f"UPDATE downloads SET {', '.join(fields)} WHERE job_id = ?", values)


def get_download_id_for_job(job_id: str) -> str | None:
    _ensure_schema()
    with get_connection() as connection:
        row = connection.execute("SELECT id FROM downloads WHERE job_id = ?", (job_id,)).fetchone()
        return str(row["id"]) if row else None


def add_file_record(
    *,
    job_id: str,
    path: Path,
    category: str,
    gallery_index: int | None = None,
    checksum_sha256: str | None = None,
    mime_type: str | None = None,
) -> str | None:
    _ensure_schema()
    download_id = get_download_id_for_job(job_id)
    if not download_id:
        return None
    relative_path = to_relative_download_path(path)
    timestamp = now()
    stat = path.stat() if path.exists() else None
    file_id = str(uuid.uuid4())
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO download_files(
                id, download_id, gallery_index, relative_path, filename, category,
                extension, mime_type, size_bytes, checksum_sha256, exists_on_disk,
                created_at, last_verified_at, updated_at
            )
            VALUES (
                COALESCE((SELECT id FROM download_files WHERE download_id = ? AND relative_path = ?), ?),
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                download_id,
                relative_path,
                file_id,
                download_id,
                gallery_index,
                relative_path,
                path.name,
                category,
                path.suffix.lower(),
                mime_type,
                stat.st_size if stat else None,
                checksum_sha256,
                1 if path.exists() else 0,
                timestamp,
                timestamp,
                timestamp,
            ),
        )
    return file_id


def set_thumbnail(
    *,
    download_id: str,
    source_file_id: str | None,
    relative_path: str | None,
    source_type: str,
    width: int | None = None,
    height: int | None = None,
    exists_on_disk: bool = False,
) -> str:
    _ensure_schema()
    thumbnail_id = str(uuid.uuid4())
    timestamp = now()
    with get_connection() as connection:
        connection.execute("DELETE FROM download_thumbnails WHERE download_id = ?", (download_id,))
        connection.execute(
            """
            INSERT INTO download_thumbnails(
                id, download_id, source_file_id, relative_path, source_type, width, height,
                exists_on_disk, generated_at, last_verified_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                thumbnail_id,
                download_id,
                source_file_id,
                relative_path,
                source_type,
                width,
                height,
                1 if exists_on_disk else 0,
                timestamp if exists_on_disk else None,
                timestamp,
                timestamp,
            ),
        )
    return thumbnail_id


def update_availability(download_id: str) -> str:
    _ensure_schema()
    timestamp = now()
    with get_connection() as connection:
        files = connection.execute(
            "SELECT exists_on_disk FROM download_files WHERE download_id = ?",
            (download_id,),
        ).fetchall()
        expected_row = connection.execute(
            "SELECT expected_file_count FROM downloads WHERE id = ?",
            (download_id,),
        ).fetchone()
        expected = int(expected_row["expected_file_count"] or len(files) or 1) if expected_row else len(files)
        existing = sum(1 for file in files if file["exists_on_disk"])
        if not files and expected <= 0:
            availability = "unknown"
        elif existing >= expected and expected > 0:
            availability = "available"
        elif existing > 0:
            availability = "partially_available"
        else:
            availability = "missing"
        connection.execute(
            "UPDATE downloads SET availability = ?, last_verified_at = ?, updated_at = ? WHERE id = ?",
            (availability, timestamp, timestamp, download_id),
        )
        return availability


def mark_interrupted_jobs() -> int:
    _ensure_schema()
    timestamp = now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE downloads
            SET status = 'failed',
                error_code = 'interrupted_by_restart',
                error_message = 'The download was interrupted when the application stopped.',
                completed_at = COALESCE(completed_at, ?),
                updated_at = ?
            WHERE status IN ('queued', 'resolving', 'downloading', 'merging', 'finalizing')
            """,
            (timestamp, timestamp),
        )
        return cursor.rowcount


def list_downloads(
    *,
    status_filter: str = "all",
    availability_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[sqlite3.Row]:
    _ensure_schema()
    where = []
    values: list[Any] = []
    if status_filter not in {"all", "active"}:
        where.append("status = ?")
        values.append(status_filter)
    elif status_filter == "active":
        where.append("status IN ('queued', 'resolving', 'downloading', 'merging', 'finalizing')")
    if availability_filter:
        mapped = "partially_available" if availability_filter == "partial" else availability_filter
        where.append("availability = ?")
        values.append(mapped)
    sql = "SELECT * FROM downloads"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY COALESCE(completed_at, started_at, created_at) DESC LIMIT ? OFFSET ?"
    values.extend([min(max(limit, 1), 500), max(offset, 0)])
    with get_connection() as connection:
        return list(connection.execute(sql, values).fetchall())


def files_for_download(download_id: str) -> list[sqlite3.Row]:
    _ensure_schema()
    with get_connection() as connection:
        return list(
            connection.execute(
                "SELECT * FROM download_files WHERE download_id = ? ORDER BY COALESCE(gallery_index, 0), filename",
                (download_id,),
            ).fetchall()
        )


def thumbnail_for_download(download_id: str) -> sqlite3.Row | None:
    _ensure_schema()
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM download_thumbnails WHERE download_id = ? ORDER BY updated_at DESC LIMIT 1",
            (download_id,),
        ).fetchone()


def find_duplicate(post_id: str, media_type: str, download_scope: str, gallery_index: int | None) -> sqlite3.Row | None:
    _ensure_schema()
    media_clause = "" if media_type == "unknown" else "AND d.media_type = ?"
    values: list[Any] = [post_id]
    if media_clause:
        values.append(media_type)
    values.extend([download_scope, gallery_index, gallery_index])
    with get_connection() as connection:
        return connection.execute(
            f"""
            SELECT d.*
            FROM downloads d
            WHERE d.post_id = ?
              {media_clause}
              AND d.download_scope = ?
              AND d.status IN ('completed', 'completed_with_errors')
              AND d.availability IN ('available', 'partially_available')
              AND (
                    ? IS NULL
                    OR EXISTS (
                        SELECT 1 FROM download_files f
                        WHERE f.download_id = d.id AND f.gallery_index = ? AND f.exists_on_disk = 1
                    )
              )
            ORDER BY COALESCE(d.completed_at, d.created_at) DESC
            LIMIT 1
            """,
            values,
        ).fetchone()


def delete_download(download_id: str) -> int:
    _ensure_schema()
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
        return cursor.rowcount


def delete_terminal_records(statuses: set[str] | None = None) -> int:
    _ensure_schema()
    terminal = statuses or {"completed", "completed_with_errors", "failed", "cancelled"}
    allowed = sorted(terminal & {"completed", "completed_with_errors", "failed", "cancelled"})
    if not allowed:
        return 0
    placeholders = ",".join("?" for _ in allowed)
    with get_connection() as connection:
        cursor = connection.execute(f"DELETE FROM downloads WHERE status IN ({placeholders})", allowed)
        return cursor.rowcount


def counts() -> dict[str, int]:
    _ensure_schema()
    with get_connection() as connection:
        downloads = connection.execute("SELECT COUNT(*) AS count FROM downloads").fetchone()["count"]
        files = connection.execute("SELECT COUNT(*) AS count FROM download_files").fetchone()["count"]
        missing = connection.execute(
            "SELECT COUNT(*) AS count FROM download_files WHERE exists_on_disk = 0"
        ).fetchone()["count"]
        return {"downloads": int(downloads), "files": int(files), "missing_files": int(missing)}


def all_download_ids() -> list[str]:
    _ensure_schema()
    with get_connection() as connection:
        return [str(row["id"]) for row in connection.execute("SELECT id FROM downloads").fetchall()]


def refresh_file_existence(download_id: str) -> tuple[int, int]:
    _ensure_schema()
    timestamp = now()
    checked = 0
    missing = 0
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, relative_path FROM download_files WHERE download_id = ?",
            (download_id,),
        ).fetchall()
        for row in rows:
            checked += 1
            exists = resolve_download_path(str(row["relative_path"])).exists()
            if not exists:
                missing += 1
            connection.execute(
                "UPDATE download_files SET exists_on_disk = ?, last_verified_at = ?, updated_at = ? WHERE id = ?",
                (1 if exists else 0, timestamp, timestamp, row["id"]),
            )
    update_availability(download_id)
    return checked, missing


def _ensure_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    from backend.database.migrations import initialize_database

    initialize_database()
    _schema_ready = True
