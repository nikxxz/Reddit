from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str


class ReadinessResponse(BaseModel):
    ready: bool
    database_ready: bool
    download_manager_ready: bool
    shutting_down: bool


class AppConfigResponse(BaseModel):
    app_name: str


class SystemStatusResponse(BaseModel):
    status: str
    ffmpeg_available: bool
    yt_dlp_available: bool
    download_directory_ready: bool
    download_directory_writable: bool
    free_space_gb: float
    minimum_free_space_gb: float
    active_downloads: int
    queued_downloads: int
    database_ready: bool = False
    database_writable: bool = False
    database_schema_version: int | None = None
    database_expected_schema_version: int | None = None
    database_migration_required: bool = False
    database_last_error_code: str | None = None
    database_backup_available: bool = False
    database_last_backup_at: str | None = None
    library_download_count: int = 0
    library_file_count: int = 0
    library_missing_file_count: int = 0
    thumbnail_directory_ready: bool = False
    application_ready: bool = False
    application_shutting_down: bool = False
    library_reconciliation_in_progress: bool = False
    maintenance_tasks_running: bool = False
    active_background_tasks: int = 0
    last_reconciliation_at: str | None = None
    last_reconciliation_error: str | None = None
    last_backup_at: str | None = None


class ReconciliationStartResponse(BaseModel):
    started: bool
    already_running: bool


class ReconciliationStatusResponse(BaseModel):
    running: bool
    started_at: str | None = None
    downloads_examined: int = 0
    files_examined: int = 0
    files_missing: int = 0
    thumbnails_regenerated: int = 0
    last_error: str | None = None
