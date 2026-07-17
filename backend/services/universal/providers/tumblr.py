from __future__ import annotations

import re
from dataclasses import dataclass
from time import monotonic
from urllib.parse import urlparse

from backend.config import settings
from backend.models.universal_search import (
    ProviderCapabilities,
    ProviderHealth,
    ProviderSearchRequest,
    ProviderSearchResult,
)
from backend.services.universal.providers.tumblr_client import TumblrApiError, TumblrClient
from backend.services.universal.providers.tumblr_normalizer import normalize_tumblr_posts
from backend.utils.logging import get_logger


logger = get_logger(__name__)
BLOG_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,62}(?:\.tumblr\.com)?$")


@dataclass
class CacheEntry:
    value: ProviderSearchResult
    cached_at: float


class TumblrUniversalProvider:
    provider_name = "tumblr"
    display_name = "Tumblr"

    def __init__(self, client: TumblrClient | None = None) -> None:
        self._client = client
        self._cache: dict[str, CacheEntry] = {}
        self._last_success_at: float | None = None
        self._last_error_code: str | None = None

    @property
    def implementation_status(self) -> str:
        return "available" if self._configured else "configuration_required"

    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        if not self._configured:
            return ProviderSearchResult(provider="tumblr", status="unavailable", error_code="tumblr_configuration_required")
        started = monotonic()
        tumblr_filter = request.provider_filters.tumblr
        mode = tumblr_filter.mode if tumblr_filter else "tag"
        tag = (tumblr_filter.tag if tumblr_filter and tumblr_filter.tag else request.query).strip()
        blog = normalize_blog_identifier(tumblr_filter.blog) if tumblr_filter and tumblr_filter.blog else None
        if mode in {"blog", "blog_tag"} and not blog:
            return ProviderSearchResult(provider="tumblr", status="failed", error_code="tumblr_invalid_blog")
        if mode == "blog_tag" and not tag:
            return ProviderSearchResult(provider="tumblr", status="failed", error_code="tumblr_invalid_tag")

        cache_key = self._cache_key(request, mode, blog, tag)
        cached = self._cache_get(cache_key)
        if cached:
            logger.info("tumblr.search.cache_hit search_mode=%s result_count=%s", mode, len(cached.items))
            return cached

        logger.info("tumblr.search.started search_mode=%s query_length=%s", mode, len(request.query))
        try:
            client = self._get_client()
            limit = min(request.limit, settings.tumblr_max_limit)
            if mode == "tag":
                response = await client.get_tagged_posts(tag, limit=limit)
                posts = response.posts
                cursor = str(response.next_before) if response.next_before else None
            else:
                response = await client.get_blog_posts(
                    blog or "",
                    limit=limit,
                    tag=tag if mode == "blog_tag" else None,
                )
                posts = response.posts
                cursor = str(response.next_offset) if response.next_offset is not None else None
            items = normalize_tumblr_posts(posts, media_types=request.media_types, include_nsfw=request.include_nsfw)
            result = ProviderSearchResult(
                provider="tumblr",
                status="completed" if items else "no_results",
                items=items,
                next_cursor=cursor,
            )
            self._cache_set(cache_key, result)
            self._last_success_at = monotonic()
            self._last_error_code = None
            logger.info(
                "tumblr.search.completed search_mode=%s result_count=%s elapsed_ms=%s",
                mode,
                len(items),
                int((monotonic() - started) * 1000),
            )
            return result
        except TumblrApiError as exc:
            self._last_error_code = exc.code
            status = "rate_limited" if exc.code == "tumblr_rate_limited" else "authentication_required" if exc.code in {"tumblr_unauthorized", "tumblr_forbidden"} else "failed"
            logger.warning(
                "tumblr.search.failed search_mode=%s error_code=%s status_code=%s elapsed_ms=%s",
                mode,
                exc.code,
                exc.status_code,
                int((monotonic() - started) * 1000),
            )
            return ProviderSearchResult(provider="tumblr", status=status, error_code=exc.code)

    async def health(self) -> ProviderHealth:
        if not self._configured:
            return ProviderHealth(state="unavailable", authenticated=False, error_code="tumblr_configuration_required")
        try:
            client = self._get_client()
            return ProviderHealth(
                state="rate_limited" if client.rate_limit.limited else "ready",
                authenticated=True,
                error_code=self._last_error_code,
                rate_limit={
                    "limited": client.rate_limit.limited,
                    "retry_after_seconds": client.rate_limit.retry_after_seconds,
                },
            )
        except TumblrApiError as exc:
            return ProviderHealth(state="unavailable", authenticated=False, error_code=exc.code)

    def capabilities(self) -> ProviderCapabilities:
        available = self._configured
        return ProviderCapabilities(
            keyword_search=available,
            account_browse=available,
            collection_browse=available,
            image_results=available,
            gif_results=available,
            video_results=available,
            gallery_results=available,
            single_download=available,
            gallery_download=available,
        )

    @property
    def _configured(self) -> bool:
        return bool(settings.tumblr_consumer_key or (self._client and self._client.consumer_key))

    def _get_client(self) -> TumblrClient:
        if self._client is None:
            self._client = TumblrClient()
        return self._client

    def _cache_key(self, request: ProviderSearchRequest, mode: str, blog: str | None, tag: str) -> str:
        return "|".join(
            [
                "tumblr",
                mode,
                (blog or "").lower(),
                tag.lower(),
                ",".join(sorted(request.media_types)),
                str(request.include_nsfw),
                str(request.limit),
            ]
        )

    def _cache_get(self, key: str) -> ProviderSearchResult | None:
        entry = self._cache.get(key)
        if not entry:
            return None
        if settings.tumblr_cache_ttl_seconds <= 0 or monotonic() - entry.cached_at > settings.tumblr_cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        return entry.value.model_copy(deep=True)

    def _cache_set(self, key: str, value: ProviderSearchResult) -> None:
        if settings.tumblr_cache_ttl_seconds <= 0:
            return
        self._cache[key] = CacheEntry(value=value.model_copy(deep=True), cached_at=monotonic())


def normalize_blog_identifier(value: str | None) -> str | None:
    if not value or any(ord(char) < 32 for char in value):
        return None
    raw = value.strip()
    parsed = urlparse(raw)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return None
    if parsed.scheme:
        host = (parsed.hostname or "").lower()
        if host in {"www.tumblr.com", "tumblr.com"}:
            parts = [part for part in parsed.path.split("/") if part]
            candidate = parts[0] if parts else ""
        elif host.endswith(".tumblr.com"):
            candidate = host
        else:
            return None
    else:
        candidate = raw.lower().removeprefix("@")
    candidate = candidate.removesuffix("/")
    if candidate.endswith(".tumblr.com"):
        normalized = candidate
    else:
        normalized = f"{candidate}.tumblr.com"
    return normalized if BLOG_IDENTIFIER_RE.fullmatch(normalized) else None
