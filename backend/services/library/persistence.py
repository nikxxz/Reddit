from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from backend.database.repositories import downloads as downloads_repo
from backend.models.downloads import DownloadRequest
from backend.services.library.thumbnails import generate_thumbnail_for_download
from backend.utils.logging import get_logger


logger = get_logger(__name__)


def create_download(job_id: str, request: DownloadRequest, retry_of_id: str | None = None) -> str | None:
    try:
        return downloads_repo.create_download_record(
            job_id=job_id,
            post_id=request.post_id,
            title=request.title,
            subreddit=request.subreddit,
            author=request.author,
            media_type=request.media_type,
            download_scope=request.download_scope,
            retry_of_id=retry_of_id,
        )
    except Exception:
        logger.exception("library.persistence.download_create.failed job_id=%s post_id=%s", job_id, request.post_id)
        return None


def update_status(
    job_id: str,
    status: str,
    *,
    error_code: str | None = None,
    error_message: str | None = None,
    expected_file_count: int | None = None,
) -> None:
    try:
        downloads_repo.update_download_status(
            job_id,
            status,
            error_code=error_code,
            error_message=error_message,
            expected_file_count=expected_file_count,
        )
    except Exception:
        logger.exception("library.persistence.status_update.failed job_id=%s status=%s", job_id, status)


def persist_file(job_id: str, path: Path, category: str, gallery_index: int | None = None) -> None:
    try:
        downloads_repo.add_file_record(
            job_id=job_id,
            path=path,
            category=category,
            gallery_index=gallery_index,
            checksum_sha256=_sha256(path),
            mime_type=mimetypes.guess_type(path.name)[0],
        )
    except Exception:
        logger.exception("library.persistence.file_create.failed job_id=%s filename=%s", job_id, path.name)


def finalize_download(job_id: str, expected_file_count: int) -> None:
    try:
        download_id = downloads_repo.get_download_id_for_job(job_id)
        if not download_id:
            return
        downloads_repo.update_download_status(job_id, "completed", expected_file_count=expected_file_count)
        downloads_repo.update_availability(download_id)
        generate_thumbnail_for_download(download_id)
    except Exception:
        logger.exception("library.persistence.finalize.failed job_id=%s", job_id)


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
