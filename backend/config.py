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
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    download_dir: str = os.getenv("DOWNLOAD_DIR", "downloads")
    debug: bool = os.getenv("DEBUG", "true").lower() in {"1", "true", "yes", "on"}
    reddit_client_id: str | None = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret: str | None = os.getenv("REDDIT_CLIENT_SECRET")
    reddit_user_agent: str | None = os.getenv("REDDIT_USER_AGENT")

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


settings = Settings()
