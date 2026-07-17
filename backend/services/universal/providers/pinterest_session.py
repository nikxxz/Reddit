from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from backend.config import settings
from backend.services.universal.providers.pinterest_models import PinterestSessionStatus
from backend.utils.logging import get_logger


logger = get_logger(__name__)
MAX_COOKIE_BYTES = 2 * 1024 * 1024


class PinterestSessionStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.pinterest_cookie_file_path
        self._last_status: PinterestSessionStatus | None = None
        self.generation = 0

    def status(self) -> PinterestSessionStatus:
        configured = self.path.exists()
        if self._last_status and configured:
            return self._last_status
        return PinterestSessionStatus(configured=configured, valid=None)

    def import_cookie_bytes(self, content: bytes) -> PinterestSessionStatus:
        text = validate_cookie_bytes(content)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(text, encoding="utf-8", newline="\n")
        try:
            os.replace(temp_path, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        self.generation += 1
        self._last_status = PinterestSessionStatus(
            configured=True,
            valid=True,
            last_checked_at=datetime.now(timezone.utc),
        )
        logger.info("pinterest.session.imported session_configured=true")
        return self._last_status

    def clear(self) -> PinterestSessionStatus:
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
        self.generation += 1
        self._last_status = PinterestSessionStatus(configured=False, valid=None)
        logger.info("pinterest.session.cleared")
        return self._last_status

    def mark_tested(self, *, valid: bool, error_code: str | None = None) -> PinterestSessionStatus:
        self._last_status = PinterestSessionStatus(
            configured=self.path.exists(),
            valid=valid,
            last_checked_at=datetime.now(timezone.utc),
            error_code=error_code,
        )
        logger.info("pinterest.session.%s error_code=%s", "validated" if valid else "invalid", error_code)
        return self._last_status


def validate_cookie_bytes(content: bytes) -> str:
    if len(content) > MAX_COOKIE_BYTES:
        raise ValueError("pinterest_cookie_oversized")
    if b"\x00" in content:
        raise ValueError("pinterest_cookie_binary")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("pinterest_cookie_binary") from exc
    lines = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
    if not lines:
        raise ValueError("pinterest_cookie_invalid")
    has_pinterest = False
    for line in lines:
        fields = line.split("\t")
        if len(fields) != 7:
            raise ValueError("pinterest_cookie_invalid")
        domain = fields[0].lstrip(".").lower()
        if domain == "pinterest.com" or domain.endswith(".pinterest.com"):
            has_pinterest = True
    if not has_pinterest:
        raise ValueError("pinterest_cookie_missing_domain")
    return text


pinterest_session_store = PinterestSessionStore()
