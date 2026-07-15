from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str


class AppConfigResponse(BaseModel):
    app_name: str
    reddit_username: str | None = None


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
    database_schema_version: int | None = None
    database_backup_available: bool = False
    database_last_backup_at: str | None = None
    library_download_count: int = 0
    library_file_count: int = 0
    library_missing_file_count: int = 0
    thumbnail_directory_ready: bool = False
