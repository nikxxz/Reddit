from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

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
        raise ConfigurationError(
            "Missing Reddit configuration values: " + ", ".join(missing)
        )


class Settings:
    app_name: str = os.getenv("APP_NAME", "Reddit Media Downloader")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    download_dir: str = os.getenv("DOWNLOAD_DIR", "downloads")
    session_file: str = os.getenv("SESSION_FILE", "backend/data/session.json")
    debug: bool = os.getenv("DEBUG", "true").lower() in {"1", "true", "yes", "on"}
    reddit_connect_timeout: float = float(os.getenv("REDDIT_CONNECT_TIMEOUT", "10"))
    reddit_read_timeout: float = float(os.getenv("REDDIT_READ_TIMEOUT", "20"))
    media_connect_timeout: float = float(os.getenv("MEDIA_CONNECT_TIMEOUT", "10"))
    media_read_timeout: float = float(os.getenv("MEDIA_READ_TIMEOUT", "60"))
    download_total_timeout: float = float(os.getenv("DOWNLOAD_TOTAL_TIMEOUT", "600"))
    max_download_size_mb: int = int(os.getenv("MAX_DOWNLOAD_SIZE_MB", "2048"))
    max_api_retries: int = int(os.getenv("MAX_API_RETRIES", "2"))
    max_download_retries: int = int(os.getenv("MAX_DOWNLOAD_RETRIES", "2"))
    download_job_retention_hours: float = float(os.getenv("DOWNLOAD_JOB_RETENTION_HOURS", "24"))
    failed_job_retention_hours: float = float(os.getenv("FAILED_JOB_RETENTION_HOURS", "48"))
    part_file_max_age_hours: float = float(os.getenv("PART_FILE_MAX_AGE_HOURS", "12"))
    media_cache_ttl_minutes: float = float(os.getenv("MEDIA_CACHE_TTL_MINUTES", "45"))
    media_cache_max_items: int = int(os.getenv("MEDIA_CACHE_MAX_ITEMS", "1000"))
    reddit_hydration_timeout: float = float(os.getenv("REDDIT_HYDRATION_TIMEOUT", "20"))
    min_free_disk_gb: float = float(os.getenv("MIN_FREE_DISK_GB", "2"))
    search_limit: int = int(os.getenv("SEARCH_LIMIT", "24"))
    search_fetch_multiplier: int = int(os.getenv("SEARCH_FETCH_MULTIPLIER", "3"))
    search_syntax: str = os.getenv("SEARCH_SYNTAX", "lucene")
    max_concurrent_downloads: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "2"))
    reddit_username: str | None = os.getenv("REDDIT_USERNAME")
    reddit_client_id: str | None = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret: str | None = os.getenv("REDDIT_CLIENT_SECRET")
    reddit_user_agent: str | None = os.getenv("REDDIT_USER_AGENT")
    reddit_redirect_uri: str = os.getenv(
        "REDDIT_REDIRECT_URI",
        f"http://{'127.0.0.1' if app_host == '0.0.0.0' else app_host}:{app_port}/api/reddit/auth/callback",
    )

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


settings = Settings()
