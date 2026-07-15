from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.config import settings
from backend.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class RedditSessionData:
    refresh_token: str
    username: str | None = None


class RedditSessionStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.session_file_path

    def load(self) -> RedditSessionData | None:
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("reddit.oauth.session.load_failed error_type=%s", exc.__class__.__name__)
            return None
        refresh_token = data.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            return None
        username = data.get("username") if isinstance(data.get("username"), str) else None
        return RedditSessionData(refresh_token=refresh_token, username=username)

    def save(self, session: RedditSessionData) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "refresh_token": session.refresh_token,
            "username": session.username,
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def delete(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("reddit.oauth.session.delete_failed error_type=%s", exc.__class__.__name__)
