from __future__ import annotations

import hashlib
import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

from backend.database.repositories import downloads as downloads_repo
from backend.models.downloads import DownloadRequest
from backend.services.library.thumbnails import generate_thumbnail_for_download
from backend.utils.logging import get_logger


logger = get_logger(__name__)
T = TypeVar("T")


@dataclass(frozen=True)
class PersistenceResult:
    success: bool
    warning_code: str | None = None
    safe_message: str | None = None
    value: object | None = None


HISTORY_WARNING = "history_persistence_failed"
HISTORY_WARNING_MESSAGE = "The file downloaded, but its history record could not be saved completely."


def create_download(job_id: str, request: DownloadRequest, retry_of_id: str | None = None) -> PersistenceResult:
    return _with_retry(
        "library.persistence.download_create.failed",
        lambda: downloads_repo.create_download_record(
            job_id=job_id,
            post_id=request.post_id,
            provider=request.provider,
            title=request.title,
            subreddit=request.subreddit,
            author=request.author,
            media_type=request.media_type,
            download_scope=request.download_scope,
            retry_of_id=retry_of_id,
        ),
        job_id=job_id,
    )


def update_status(
    job_id: str,
    status: str,
    *,
    error_code: str | None = None,
    error_message: str | None = None,
    expected_file_count: int | None = None,
) -> PersistenceResult:
    return _with_retry(
        "library.persistence.status_update.failed",
        lambda: downloads_repo.update_download_status(
            job_id,
            status,
            error_code=error_code,
            error_message=error_message,
            expected_file_count=expected_file_count,
        ),
        job_id=job_id,
        status=status,
    )


def persist_file(job_id: str, path: Path, category: str, gallery_index: int | None = None) -> PersistenceResult:
    def add_file() -> str:
        file_id = downloads_repo.add_file_record(
            job_id=job_id,
            path=path,
            category=category,
            gallery_index=gallery_index,
            checksum_sha256=_sha256(path),
            mime_type=mimetypes.guess_type(path.name)[0],
        )
        if not file_id:
            raise RuntimeError("download record unavailable")
        return file_id

    return _with_retry(
        "library.persistence.file_create.failed",
        add_file,
        job_id=job_id,
        filename=path.name,
    )


def finalize_download(job_id: str, expected_file_count: int, status: str = "completed") -> PersistenceResult:
    def finalize() -> None:
        download_id = downloads_repo.get_download_id_for_job(job_id)
        if not download_id:
            raise RuntimeError("download record unavailable")
        downloads_repo.update_download_status(job_id, status, expected_file_count=expected_file_count)
        downloads_repo.update_availability(download_id)
        generate_thumbnail_for_download(download_id)

    return _with_retry("library.persistence.finalize.failed", finalize, job_id=job_id, status=status)


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _with_retry(message: str, operation: Callable[[], T], **safe_fields: object) -> PersistenceResult:
    for attempt in range(2):
        try:
            return PersistenceResult(success=True, value=operation())
        except Exception:
            if attempt == 0:
                logger.warning(
                    "download.persistence.retry warning_code=%s %s",
                    HISTORY_WARNING,
                    _safe_log_fields(safe_fields),
                )
                time.sleep(0.05)
                continue
            logger.exception("%s warning_code=%s %s", message, HISTORY_WARNING, _safe_log_fields(safe_fields))
            return PersistenceResult(
                success=False,
                warning_code=HISTORY_WARNING,
                safe_message=HISTORY_WARNING_MESSAGE,
            )
    return PersistenceResult(success=False, warning_code=HISTORY_WARNING, safe_message=HISTORY_WARNING_MESSAGE)


def _safe_log_fields(fields: dict[str, object]) -> str:
    return " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
