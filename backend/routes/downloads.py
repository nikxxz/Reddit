from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from time import monotonic

from backend.models.downloads import (
    ClearDownloadsRequest,
    ClearDownloadsResponse,
    DownloadJobFilter,
    DownloadJobListResponse,
    DownloadRequest,
    DownloadStartResponse,
    DownloadStatusResponse,
)
from backend.services.downloads.errors import DownloadError
from backend.services.downloads.manager import download_job_manager
from backend.database.repositories import downloads as downloads_repo
from backend.utils.logging import get_logger


router = APIRouter(tags=["downloads"])
logger = get_logger(__name__)


@router.get("/downloads", response_model=DownloadJobListResponse)
def list_downloads(
    status: DownloadJobFilter = "all",
    availability: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> DownloadJobListResponse:
    started = monotonic()
    logger.info("download.jobs.list.start status_filter=%s", status)
    try:
        active_jobs = download_job_manager.list_jobs(status)
        active_job_ids = {job.job_id for job in active_jobs}
        historical = [
            _history_summary(row)
            for row in downloads_repo.list_downloads(
                status_filter=status,
                availability_filter=availability,
                limit=limit,
                offset=offset,
            )
            if row["job_id"] not in active_job_ids
        ]
        jobs = [*active_jobs, *historical]
        logger.info(
            "download.jobs.list.success status_filter=%s job_count=%s elapsed_ms=%s",
            status,
            len(jobs),
            int((monotonic() - started) * 1000),
        )
        return DownloadJobListResponse(jobs=jobs)
    except Exception:
        logger.exception(
            "download.jobs.list.failed status_filter=%s elapsed_ms=%s",
            status,
            int((monotonic() - started) * 1000),
        )
        raise


@router.post("/downloads", response_model=DownloadStartResponse)
async def start_download(request: DownloadRequest) -> DownloadStartResponse:
    try:
        job = await download_job_manager.create_job(request)
    except DownloadError as exc:
        raise HTTPException(status_code=507, detail=str(exc)) from exc
    return DownloadStartResponse(job_id=job.job_id, status="queued")


@router.delete("/downloads/terminal", response_model=ClearDownloadsResponse)
def clear_terminal_downloads() -> ClearDownloadsResponse:
    removed = download_job_manager.clear_terminal_jobs()
    downloads_repo.delete_terminal_records()
    return ClearDownloadsResponse(removed=removed)


@router.post("/downloads/clear", response_model=ClearDownloadsResponse)
def clear_downloads(request: ClearDownloadsRequest) -> ClearDownloadsResponse:
    removed = download_job_manager.clear_terminal_jobs(set(request.statuses))
    downloads_repo.delete_terminal_records(set(request.statuses))
    return ClearDownloadsResponse(removed=removed)


@router.get("/downloads/{job_id}", response_model=DownloadStatusResponse)
def get_download(job_id: str) -> DownloadStatusResponse:
    status = download_job_manager.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Download job not found.")
    return status


@router.post("/downloads/{job_id}/cancel", response_model=DownloadStatusResponse)
def cancel_download(job_id: str) -> DownloadStatusResponse:
    status = download_job_manager.cancel_job(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Download job not found.")
    return status


@router.post("/downloads/{job_id}/retry", response_model=DownloadStartResponse)
async def retry_download(job_id: str) -> DownloadStartResponse:
    try:
        job = await download_job_manager.retry_job(job_id)
    except DownloadError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found.")
    return DownloadStartResponse(job_id=job.job_id, status=job.status)


def _history_summary(row) -> object:
    files = [
        {
            "id": file["id"],
            "filename": file["filename"],
            "category": file["category"],
            "index": file["gallery_index"],
            "status": "completed" if file["exists_on_disk"] else "missing",
            "size_bytes": file["size_bytes"],
            "exists_on_disk": bool(file["exists_on_disk"]),
        }
        for file in downloads_repo.files_for_download(str(row["id"]))
    ]
    return {
        "id": row["id"],
        "job_id": row["job_id"] or row["id"],
        "post_id": row["post_id"],
        "status": row["status"],
        "availability": row["availability"],
        "progress": 100 if row["status"] == "completed" else None,
        "message": row["error_message"] or "",
        "media_type": row["media_type"] or "media",
        "title": row["title"],
        "subreddit": row["subreddit"],
        "author": row["author"],
        "thumbnail_url": f"/api/library/thumbnails/{row['id']}",
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
        "files": files,
        "error": row["error_message"],
        "error_code": row["error_code"],
        "cancellable": False,
        "retryable": row["status"] in {"failed", "cancelled"} or row["availability"] in {"missing", "partially_available"},
    }
