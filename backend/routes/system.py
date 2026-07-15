from __future__ import annotations

from fastapi import APIRouter

from backend.config import settings
from backend.models import SystemStatusResponse
from backend.services.downloads.manager import download_job_manager
from backend.services.system import (
    disk_free_gb,
    download_directory_ready,
    download_directory_writable,
    ffmpeg_available,
    yt_dlp_available,
)


router = APIRouter(tags=["system"])


@router.get("/system/status", response_model=SystemStatusResponse)
def system_status() -> SystemStatusResponse:
    active_downloads, queued_downloads = download_job_manager.active_counts()
    return SystemStatusResponse(
        status="ok",
        ffmpeg_available=ffmpeg_available(),
        yt_dlp_available=yt_dlp_available(),
        download_directory_ready=download_directory_ready(),
        download_directory_writable=download_directory_writable(),
        free_space_gb=disk_free_gb(),
        minimum_free_space_gb=settings.min_free_disk_gb,
        active_downloads=active_downloads,
        queued_downloads=queued_downloads,
    )
