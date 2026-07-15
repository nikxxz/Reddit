from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models.downloads import (
    DownloadRequest,
    DownloadStartResponse,
    DownloadStatusResponse,
)
from backend.services.downloads.manager import download_job_manager


router = APIRouter(tags=["downloads"])


@router.post("/downloads", response_model=DownloadStartResponse)
async def start_download(request: DownloadRequest) -> DownloadStartResponse:
    job = await download_job_manager.create_job(request)
    return DownloadStartResponse(job_id=job.job_id, status="queued")


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
