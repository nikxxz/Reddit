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
from backend.core.paths import get_thumbnail_root
from backend.database.health import check_database_health
from backend.database.repositories.downloads import counts as library_counts
from backend.services.library.backups import backup_status
from backend.services.lifecycle import application_lifecycle


router = APIRouter(tags=["system"])


@router.get("/system/status", response_model=SystemStatusResponse)
def system_status() -> SystemStatusResponse:
    active_downloads, queued_downloads = download_job_manager.active_counts()
    database_backup_available, database_last_backup_at = backup_status()
    database_health = check_database_health()
    lifecycle = application_lifecycle.snapshot()
    try:
        library = library_counts()
    except Exception:
        library = {"downloads": 0, "files": 0, "missing_files": 0}
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
        database_ready=database_health.ready,
        database_writable=database_health.writable,
        database_schema_version=database_health.schema_version,
        database_expected_schema_version=database_health.expected_schema_version,
        database_migration_required=database_health.migration_required,
        database_last_error_code=database_health.last_error_code,
        database_backup_available=database_backup_available,
        database_last_backup_at=database_last_backup_at,
        library_download_count=library["downloads"],
        library_file_count=library["files"],
        library_missing_file_count=library["missing_files"],
        thumbnail_directory_ready=get_thumbnail_root().exists(),
        application_ready=lifecycle.ready,
        application_shutting_down=lifecycle.shutting_down,
        library_reconciliation_in_progress=lifecycle.library_reconciliation_in_progress,
        maintenance_tasks_running=lifecycle.maintenance_tasks_running,
        active_background_tasks=lifecycle.active_background_tasks,
        last_reconciliation_at=lifecycle.last_reconciliation_at,
        last_reconciliation_error=lifecycle.last_reconciliation_error,
        last_backup_at=database_last_backup_at,
    )
