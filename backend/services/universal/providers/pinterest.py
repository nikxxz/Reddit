from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from backend.config import settings
from backend.models.universal_search import ProviderCapabilities, ProviderHealth, ProviderSearchRequest, ProviderSearchResult
from backend.services.universal.providers.pinterest_extractor import PinterestGalleryDlExtractor, pinterest_extractor
from backend.services.universal.providers.pinterest_models import PinterestExtractorError
from backend.services.universal.providers.pinterest_normalizer import normalize_pinterest_records
from backend.services.universal.providers.pinterest_session import PinterestSessionStore, pinterest_session_store
from backend.services.universal.providers.pinterest_urls import (
    normalize_board_url,
    normalize_pin_url,
    normalize_profile_url,
    search_url,
)
from backend.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class CacheEntry:
    value: ProviderSearchResult
    cached_at: float
    session_generation: int


class PinterestUniversalProvider:
    provider_name = "pinterest"
    display_name = "Pinterest"
    implementation_status = "available"

    def __init__(
        self,
        extractor: PinterestGalleryDlExtractor | None = None,
        session_store: PinterestSessionStore | None = None,
    ) -> None:
        self.extractor = extractor or pinterest_extractor
        self.session_store = session_store or pinterest_session_store
        self._cache: dict[str, CacheEntry] = {}
        self._last_success_at: float | None = None
        self._last_error_code: str | None = None

    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        if not settings.pinterest_enabled:
            return ProviderSearchResult(provider="pinterest", status="unavailable", error_code="pinterest_disabled")
        probe = await self.extractor.probe()
        if not probe.available:
            return ProviderSearchResult(provider="pinterest", status="extractor_unavailable", error_code=probe.error_code)
        if not self.session_store.status().configured:
            return ProviderSearchResult(provider="pinterest", status="session_required", error_code="pinterest_session_required")

        mode, url, collection_label = self._resolve_mode(request)
        if not url:
            return ProviderSearchResult(provider="pinterest", status="failed", error_code="pinterest_invalid_request")
        cache_key = self._cache_key(request, mode, url)
        cached = self._cache_get(cache_key)
        if cached:
            logger.info("pinterest.search.cache_hit mode=%s result_count=%s", mode, len(cached.items))
            return cached
        started = monotonic()
        logger.info("pinterest.search.started mode=%s query_length=%s", mode, len(request.query))
        try:
            offset = _offset_from_cursor(request.cursor)
            records = await self.extractor.extract(
                url,
                limit=min(request.limit, settings.pinterest_max_results),
                cookie_file=self.session_store.path,
                offset=offset,
            )
            items = normalize_pinterest_records(records, media_types=request.media_types, collection_label=collection_label)
            result = ProviderSearchResult(
                provider="pinterest",
                status="completed" if items else "no_results",
                items=items,
                next_cursor=f"offset:{offset + len(items)}" if len(items) >= min(request.limit, settings.pinterest_max_results) else None,
            )
            self._cache_set(cache_key, result)
            self._last_success_at = monotonic()
            self._last_error_code = None
            logger.info(
                "pinterest.search.completed mode=%s result_count=%s elapsed_ms=%s",
                mode,
                len(items),
                int((monotonic() - started) * 1000),
            )
            return result
        except PinterestExtractorError as exc:
            self._last_error_code = exc.code
            status = "session_required" if exc.code in {"pinterest_session_required", "pinterest_session_invalid"} else "failed"
            logger.warning(
                "pinterest.search.failed mode=%s error_code=%s elapsed_ms=%s",
                mode,
                exc.code,
                int((monotonic() - started) * 1000),
            )
            return ProviderSearchResult(provider="pinterest", status=status, error_code=exc.code)

    async def health(self) -> ProviderHealth:
        if not settings.pinterest_enabled:
            return ProviderHealth(state="unavailable", authenticated=False, error_code="pinterest_disabled")
        probe = await self.extractor.probe()
        if not probe.available:
            return ProviderHealth(
                state="extractor_unavailable",
                authenticated=False,
                error_code=probe.error_code or "pinterest_extractor_unavailable",
            )
        session = self.session_store.status()
        if not session.configured or session.valid is False:
            return ProviderHealth(
                state="session_required",
                authenticated=False,
                error_code=session.error_code or "pinterest_session_required",
            )
        return ProviderHealth(
            state="ready",
            authenticated=True,
            error_code=self._last_error_code,
            rate_limit={
                "limited": False,
                "retry_after_seconds": None,
                "extractor_version": probe.version,
                "session_configured": session.configured,
                "last_success_at": self._last_success_at,
            },
        )

    def capabilities(self) -> ProviderCapabilities:
        available = settings.pinterest_enabled
        return ProviderCapabilities(
            keyword_search=available,
            account_browse=available,
            collection_browse=available,
            image_results=available,
            gif_results=False,
            video_results=available,
            gallery_results=available,
            single_download=False,
            gallery_download=False,
        )

    def invalidate_cache(self) -> None:
        self._cache.clear()

    def _resolve_mode(self, request: ProviderSearchRequest) -> tuple[str, str | None, str | None]:
        pinterest_filter = request.provider_filters.pinterest
        mode = pinterest_filter.mode if pinterest_filter else "search"
        if mode == "pin":
            return mode, normalize_pin_url(pinterest_filter.pin_url if pinterest_filter else None), "Pin"
        if mode == "profile":
            return mode, normalize_profile_url(pinterest_filter.profile if pinterest_filter else None), "Profile"
        if mode in {"board", "section"}:
            return mode, normalize_board_url(
                pinterest_filter.board if pinterest_filter else None,
                pinterest_filter.section if pinterest_filter else None,
            ), "Board"
        return "search", search_url(request.query), "Search"

    def _cache_key(self, request: ProviderSearchRequest, mode: str, url: str) -> str:
        return "|".join(
            [
                "pinterest",
                mode,
                url.lower(),
                ",".join(sorted(request.media_types)),
                str(request.limit),
                request.cursor or "",
                str(self.session_store.generation),
            ]
        )

    def _cache_get(self, key: str) -> ProviderSearchResult | None:
        entry = self._cache.get(key)
        if not entry:
            return None
        if entry.session_generation != self.session_store.generation:
            self._cache.pop(key, None)
            return None
        if settings.pinterest_cache_ttl_seconds <= 0 or monotonic() - entry.cached_at > settings.pinterest_cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        return entry.value.model_copy(deep=True)

    def _cache_set(self, key: str, value: ProviderSearchResult) -> None:
        if settings.pinterest_cache_ttl_seconds <= 0:
            return
        self._cache[key] = CacheEntry(
            value=value.model_copy(deep=True),
            cached_at=monotonic(),
            session_generation=self.session_store.generation,
        )


pinterest_provider = PinterestUniversalProvider()


def _offset_from_cursor(cursor: str | None) -> int:
    if not cursor or not cursor.startswith("offset:"):
        return 0
    try:
        return max(0, int(cursor.split(":", 1)[1]))
    except ValueError:
        return 0
