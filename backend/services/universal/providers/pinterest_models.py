from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from backend.models.universal_search import UniversalMediaType


@dataclass(frozen=True)
class PinterestSessionStatus:
    configured: bool
    valid: bool | None = None
    account_hint: str | None = None
    last_checked_at: datetime | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class PinterestExtractorProbe:
    available: bool
    version: str | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class PinterestExtractedAsset:
    index: int
    media_type: UniversalMediaType
    thumbnail_url: str | None = None
    preview_url: str | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None


@dataclass(frozen=True)
class PinterestExtractedPin:
    pin_id: str
    canonical_url: str
    title: str | None = None
    description: str | None = None
    author: str | None = None
    collection: str | None = None
    collection_label: str | None = None
    assets: list[PinterestExtractedAsset] = field(default_factory=list)


class PinterestExtractorError(RuntimeError):
    def __init__(self, code: str, safe_message: str = "Pinterest extraction failed.") -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
