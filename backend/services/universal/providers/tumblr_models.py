from __future__ import annotations

from dataclasses import dataclass

from backend.models.universal_search import UniversalMediaType


@dataclass(frozen=True)
class TumblrRateLimitState:
    limited: bool = False
    retry_after_seconds: int | None = None


@dataclass(frozen=True)
class TumblrMediaAsset:
    index: int
    media_type: UniversalMediaType
    preview_url: str | None = None
    download_url: str | None = None
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None
    mime_type: str | None = None
    filename_hint: str | None = None
    source_url: str | None = None


@dataclass(frozen=True)
class TumblrTaggedResponse:
    posts: list[dict[str, object]]
    next_before: int | None = None


@dataclass(frozen=True)
class TumblrBlogPostsResponse:
    posts: list[dict[str, object]]
    next_offset: int | None = None
    next_before: int | None = None


@dataclass(frozen=True)
class TumblrBlogInfo:
    name: str
    title: str | None = None
    url: str | None = None
