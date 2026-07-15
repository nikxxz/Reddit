from __future__ import annotations

from fastapi import APIRouter, HTTPException
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
from backend.utils.logging import get_logger


router = APIRouter(tags=["downloads"])
logger = get_logger(__name__)


@router.get("/downloads", response_model=DownloadJobListResponse)
def list_downloads(status: DownloadJobFilter = "all") -> DownloadJobListResponse:
    started = monotonic()
    logger.info("download.jobs.list.start status_filter=%s", status)
    try:
        jobs = download_job_manager.list_jobs(status)
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
    return ClearDownloadsResponse(removed=removed)


@router.post("/downloads/clear", response_model=ClearDownloadsResponse)
def clear_downloads(request: ClearDownloadsRequest) -> ClearDownloadsResponse:
    removed = download_job_manager.clear_terminal_jobs(set(request.statuses))
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
