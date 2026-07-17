from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class ConfigurationError(ValueError):
    pass


def validate_reddit_settings_values(
    client_id: str | None,
    client_secret: str | None,
    user_agent: str | None,
) -> None:
    missing = [
        name
        for name, value in {
            "REDDIT_CLIENT_ID": client_id,
            "REDDIT_CLIENT_SECRET": client_secret,
            "REDDIT_USER_AGENT": user_agent,
        }.items()
        if not value
    ]
    if missing:
        raise ConfigurationError("Missing Reddit configuration values: " + ", ".join(missing))


class Settings(BaseModel):
    model_config = ConfigDict(validate_assignment=False)

    app_name: str = "Reddit Media Downloader"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_data_dir: str = "app-data"
    download_dir: str = "downloads"
    database_filename: str = "reddit_media_library.sqlite3"
    thumbnail_format: Literal["webp", "jpeg", "png"] = "webp"
    thumbnail_max_width: int = Field(default=480, gt=0)
    thumbnail_max_height: int = Field(default=360, gt=0)
    database_backup_retention: int = Field(default=7, ge=1)
    database_backup_interval_hours: float = Field(default=24, gt=0)
    library_reconcile_on_startup: bool = True
    generate_missing_thumbnails_on_startup: bool = True
    session_file: str = "app-data/sessions/session.json"
    debug: bool = True
    reddit_connect_timeout: float = Field(default=10, gt=0)
    reddit_read_timeout: float = Field(default=20, gt=0)
    media_connect_timeout: float = Field(default=10, gt=0)
    media_read_timeout: float = Field(default=60, gt=0)
    download_total_timeout: float = Field(default=600, gt=0)
    max_download_size_mb: int = Field(default=2048, gt=0)
    checksum_large_file_threshold_mb: int = Field(default=2048, gt=0)
    max_api_retries: int = Field(default=2, ge=0)
    max_download_retries: int = Field(default=2, ge=0)
    shutdown_grace_period_seconds: float = Field(default=15, gt=0)
    download_cancel_timeout_seconds: float = Field(default=10, gt=0)
    subprocess_terminate_timeout_seconds: float = Field(default=5, gt=0)
    download_job_retention_hours: float = Field(default=24, ge=0)
    failed_job_retention_hours: float = Field(default=48, ge=0)
    part_file_max_age_hours: float = Field(default=12, ge=0)
    maintenance_interval_minutes: float = Field(default=30, gt=0)
    library_reconcile_batch_size: int = Field(default=100, ge=1)
    library_reconcile_max_concurrency: int = Field(default=4, ge=1)
    thumbnail_regen_max_concurrency: int = Field(default=2, ge=1)
    media_cache_ttl_minutes: float = Field(default=45, gt=0)
    media_cache_max_items: int = Field(default=1000, ge=1)
    reddit_hydration_timeout: float = Field(default=20, gt=0)
    min_free_disk_gb: float = Field(default=2, ge=0)
    search_limit: int = Field(default=24, ge=1)
    search_fetch_multiplier: int = Field(default=3, ge=1)
    search_syntax: str = "lucene"
    universal_search_retention_minutes: float = Field(default=30, ge=0)
    universal_search_max_jobs: int = Field(default=100, ge=1)
    universal_search_max_concurrency: int = Field(default=4, ge=1)
    universal_search_default_limit: int = Field(default=24, ge=1, le=100)
    universal_search_max_limit: int = Field(default=100, ge=1, le=100)
    max_concurrent_downloads: int = Field(default=2, ge=1)
    tumblr_consumer_key: str | None = None
    tumblr_consumer_secret: str | None = None
    tumblr_oauth_token: str | None = None
    tumblr_oauth_token_secret: str | None = None
    tumblr_api_base_url: str = "https://api.tumblr.com/v2"
    tumblr_request_timeout_seconds: float = Field(default=20, gt=0)
    tumblr_max_retries: int = Field(default=2, ge=0)
    tumblr_default_limit: int = Field(default=20, ge=1, le=50)
    tumblr_max_limit: int = Field(default=50, ge=1, le=50)
    tumblr_cache_ttl_seconds: int = Field(default=120, ge=0)
    tumblr_max_pages_per_search: int = Field(default=3, ge=1, le=10)
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str | None = None
    reddit_redirect_uri: str | None = None

    @field_validator("thumbnail_format", mode="before")
    @classmethod
    def normalize_thumbnail_format(cls, value: Any) -> str:
        normalized = str(value or "webp").strip().lower()
        if normalized == "jpg":
            return "jpeg"
        return normalized

    @model_validator(mode="after")
    def validate_tumblr_limits(self) -> "Settings":
        if self.tumblr_default_limit > self.tumblr_max_limit:
            raise ValueError("TUMBLR_DEFAULT_LIMIT must be less than or equal to TUMBLR_MAX_LIMIT")
        return self

    @field_validator(
        "library_reconcile_on_startup",
        "generate_missing_thumbnails_on_startup",
        "debug",
        mode="before",
    )
    @classmethod
    def parse_bool(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "production"}:
            return False
        raise ValueError("must be a valid Boolean value")

    def validate_reddit_settings(self) -> None:
        validate_reddit_settings_values(
            self.reddit_client_id,
            self.reddit_client_secret,
            self.reddit_user_agent,
        )

    @property
    def download_dir_path(self) -> Path:
        path = Path(self.download_dir)
        if not path.is_absolute():
            path = BASE_DIR / path
        return path

    @property
    def session_file_path(self) -> Path:
        path = Path(self.session_file)
        if not path.is_absolute():
            path = BASE_DIR / path
        return path


ENV_FIELDS = {
    "APP_NAME": ("app_name", str),
    "APP_HOST": ("app_host", str),
    "APP_PORT": ("app_port", int),
    "APP_DATA_DIR": ("app_data_dir", str),
    "DOWNLOAD_DIR": ("download_dir", str),
    "DATABASE_FILENAME": ("database_filename", str),
    "THUMBNAIL_FORMAT": ("thumbnail_format", str),
    "THUMBNAIL_MAX_WIDTH": ("thumbnail_max_width", int),
    "THUMBNAIL_MAX_HEIGHT": ("thumbnail_max_height", int),
    "DATABASE_BACKUP_RETENTION": ("database_backup_retention", int),
    "DATABASE_BACKUP_INTERVAL_HOURS": ("database_backup_interval_hours", float),
    "LIBRARY_RECONCILE_ON_STARTUP": ("library_reconcile_on_startup", str),
    "GENERATE_MISSING_THUMBNAILS_ON_STARTUP": ("generate_missing_thumbnails_on_startup", str),
    "SESSION_FILE": ("session_file", str),
    "DEBUG": ("debug", str),
    "REDDIT_CONNECT_TIMEOUT": ("reddit_connect_timeout", float),
    "REDDIT_READ_TIMEOUT": ("reddit_read_timeout", float),
    "MEDIA_CONNECT_TIMEOUT": ("media_connect_timeout", float),
    "MEDIA_READ_TIMEOUT": ("media_read_timeout", float),
    "DOWNLOAD_TOTAL_TIMEOUT": ("download_total_timeout", float),
    "MAX_DOWNLOAD_SIZE_MB": ("max_download_size_mb", int),
    "CHECKSUM_LARGE_FILE_THRESHOLD_MB": ("checksum_large_file_threshold_mb", int),
    "MAX_API_RETRIES": ("max_api_retries", int),
    "MAX_DOWNLOAD_RETRIES": ("max_download_retries", int),
    "SHUTDOWN_GRACE_PERIOD_SECONDS": ("shutdown_grace_period_seconds", float),
    "DOWNLOAD_CANCEL_TIMEOUT_SECONDS": ("download_cancel_timeout_seconds", float),
    "SUBPROCESS_TERMINATE_TIMEOUT_SECONDS": ("subprocess_terminate_timeout_seconds", float),
    "DOWNLOAD_JOB_RETENTION_HOURS": ("download_job_retention_hours", float),
    "FAILED_JOB_RETENTION_HOURS": ("failed_job_retention_hours", float),
    "PART_FILE_MAX_AGE_HOURS": ("part_file_max_age_hours", float),
    "MAINTENANCE_INTERVAL_MINUTES": ("maintenance_interval_minutes", float),
    "LIBRARY_RECONCILE_BATCH_SIZE": ("library_reconcile_batch_size", int),
    "LIBRARY_RECONCILE_MAX_CONCURRENCY": ("library_reconcile_max_concurrency", int),
    "THUMBNAIL_REGEN_MAX_CONCURRENCY": ("thumbnail_regen_max_concurrency", int),
    "MEDIA_CACHE_TTL_MINUTES": ("media_cache_ttl_minutes", float),
    "MEDIA_CACHE_MAX_ITEMS": ("media_cache_max_items", int),
    "REDDIT_HYDRATION_TIMEOUT": ("reddit_hydration_timeout", float),
    "MIN_FREE_DISK_GB": ("min_free_disk_gb", float),
    "SEARCH_LIMIT": ("search_limit", int),
    "SEARCH_FETCH_MULTIPLIER": ("search_fetch_multiplier", int),
    "SEARCH_SYNTAX": ("search_syntax", str),
    "UNIVERSAL_SEARCH_RETENTION_MINUTES": ("universal_search_retention_minutes", float),
    "UNIVERSAL_SEARCH_MAX_JOBS": ("universal_search_max_jobs", int),
    "UNIVERSAL_SEARCH_MAX_CONCURRENCY": ("universal_search_max_concurrency", int),
    "UNIVERSAL_SEARCH_DEFAULT_LIMIT": ("universal_search_default_limit", int),
    "UNIVERSAL_SEARCH_MAX_LIMIT": ("universal_search_max_limit", int),
    "MAX_CONCURRENT_DOWNLOADS": ("max_concurrent_downloads", int),
    "TUMBLR_CONSUMER_KEY": ("tumblr_consumer_key", str),
    "TUMBLR_CONSUMER_SECRET": ("tumblr_consumer_secret", str),
    "TUMBLR_OAUTH_TOKEN": ("tumblr_oauth_token", str),
    "TUMBLR_OAUTH_TOKEN_SECRET": ("tumblr_oauth_token_secret", str),
    "TUMBLR_API_BASE_URL": ("tumblr_api_base_url", str),
    "TUMBLR_REQUEST_TIMEOUT_SECONDS": ("tumblr_request_timeout_seconds", float),
    "TUMBLR_MAX_RETRIES": ("tumblr_max_retries", int),
    "TUMBLR_DEFAULT_LIMIT": ("tumblr_default_limit", int),
    "TUMBLR_MAX_LIMIT": ("tumblr_max_limit", int),
    "TUMBLR_CACHE_TTL_SECONDS": ("tumblr_cache_ttl_seconds", int),
    "TUMBLR_MAX_PAGES_PER_SEARCH": ("tumblr_max_pages_per_search", int),
    "REDDIT_CLIENT_ID": ("reddit_client_id", str),
    "REDDIT_CLIENT_SECRET": ("reddit_client_secret", str),
    "REDDIT_USER_AGENT": ("reddit_user_agent", str),
    "REDDIT_REDIRECT_URI": ("reddit_redirect_uri", str),
}


def _settings_from_environment() -> Settings:
    values: dict[str, object] = {}
    for env_name, (field_name, converter) in ENV_FIELDS.items():
        raw = os.getenv(env_name)
        if raw is None:
            continue
        try:
            values[field_name] = converter(raw)
        except ValueError as exc:
            raise ConfigurationError(f"Invalid configuration: {env_name} has an invalid value.") from exc
    if "reddit_redirect_uri" not in values:
        host = str(values.get("app_host", Settings.model_fields["app_host"].default))
        port = int(values.get("app_port", Settings.model_fields["app_port"].default))
        callback_host = "127.0.0.1" if host == "0.0.0.0" else host
        values["reddit_redirect_uri"] = f"http://{callback_host}:{port}/api/reddit/auth/callback"
    try:
        return Settings(**values)
    except ValidationError as exc:
        first = exc.errors()[0]
        field_name = str(first["loc"][0])
        env_name = next((key for key, value in ENV_FIELDS.items() if value[0] == field_name), field_name)
        raise ConfigurationError(f"Invalid configuration: {env_name} {first['msg']}.") from exc


settings = _settings_from_environment()
