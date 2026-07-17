from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from time import monotonic

from backend.api.errors import InvalidSubredditError, RedditSearchError
from backend.models.reddit import RedditMediaItem
from backend.models.universal_search import (
    ProviderCapabilities,
    ProviderHealth,
    ProviderSearchRequest,
    ProviderSearchResult,
    UniversalMediaItem,
    UniversalMediaType,
)
from backend.services.reddit import RedditSearchService
from backend.utils.logging import get_logger
from backend.utils.urls import is_direct_video, is_reddit_video_url


logger = get_logger(__name__)


class RedditUniversalProvider:
    provider_name = "reddit"
    display_name = "Reddit"
    implementation_status = "available"

    def __init__(self, search_service: RedditSearchService | None = None) -> None:
        self.search_service = search_service or RedditSearchService()

    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        started = monotonic()
        logger.info(
            "universal.provider.search.started provider=reddit query_length=%s selected_media_types=%s",
            len(request.query),
            ",".join(request.media_types),
        )
        try:
            reddit_response = await asyncio.to_thread(
                self.search_service.search_media,
                query=request.query,
                subreddit=None,
                media_type=self._reddit_media_filter(request.media_types),
                sort=self._reddit_sort(request.sort),
                time_filter="all",
                limit=request.limit,
                after=None,
                include_nsfw=request.include_nsfw,
            )
            items = [
                self._map_item(item)
                for item in reddit_response.items
                if self._map_media_type(item.media_type) in request.media_types
            ]
            logger.info(
                "universal.reddit_adapter.mapping.completed result_count=%s elapsed_ms=%s",
                len(items),
                int((monotonic() - started) * 1000),
            )
            status = "completed" if items else "no_results"
            logger.info(
                "universal.provider.search.completed provider=reddit result_count=%s status=%s elapsed_ms=%s",
                len(items),
                status,
                int((monotonic() - started) * 1000),
            )
            return ProviderSearchResult(
                provider="reddit",
                status=status,
                items=items,
                next_cursor=reddit_response.next_after,
            )
        except InvalidSubredditError:
            return self._failure("unavailable", "invalid_collection", started)
        except RedditSearchError:
            return self._failure("failed", "reddit_search_failed", started)
        except Exception:
            logger.exception("universal.reddit_adapter.mapping.failed provider=reddit")
            return self._failure("failed", "reddit_adapter_failed", started)

    async def health(self) -> ProviderHealth:
        try:
            _client_type, username = self.search_service.client_provider.client_context()
        except Exception:
            return ProviderHealth(state="degraded", authenticated=False, error_code="reddit_context_unavailable")
        return ProviderHealth(state="ready", authenticated=bool(username))

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            keyword_search=True,
            account_browse=False,
            collection_browse=True,
            image_results=True,
            gif_results=True,
            video_results=True,
            gallery_results=True,
            single_download=False,
            gallery_download=False,
        )

    def _failure(self, status: str, error_code: str, started: float) -> ProviderSearchResult:
        logger.warning(
            "universal.provider.search.failed provider=reddit status=%s error_code=%s elapsed_ms=%s",
            status,
            error_code,
            int((monotonic() - started) * 1000),
        )
        return ProviderSearchResult(provider="reddit", status=status, items=[], error_code=error_code)

    def _reddit_media_filter(self, media_types: list[UniversalMediaType]) -> str:
        reddit_types = {media_type for media_type in media_types if media_type != "unknown"}
        if len(reddit_types) == 1:
            return next(iter(reddit_types))
        return "all"

    def _reddit_sort(self, sort: str) -> str:
        if sort in {"new", "top"}:
            return sort
        return "relevance"

    def _map_item(self, item: RedditMediaItem) -> UniversalMediaItem:
        media_type = self._map_media_type(item.media_type)
        media_urls = self._media_urls(item)
        created_at = (
            datetime.fromtimestamp(item.created_utc, tz=timezone.utc)
            if item.created_utc is not None
            else None
        )
        return UniversalMediaItem(
            provider="reddit",
            provider_item_id=item.id,
            canonical_url=self._canonical_url(item),
            title=item.title or "Untitled Reddit post",
            author=item.author or None,
            collection=item.subreddit,
            media_type=media_type,
            thumbnail_url=item.thumbnail_url,
            preview_url=self._preview_url(item, media_urls),
            media_urls=media_urls,
            media_count=item.gallery_count or (len(media_urls) if media_type == "gallery" else None),
            width=item.width,
            height=item.height,
            duration_seconds=item.duration,
            created_at=created_at,
            nsfw=item.is_nsfw,
            source_metadata={"collection_label": "Subreddit"},
        )

    def _map_media_type(self, media_type: str) -> UniversalMediaType:
        if media_type in {"image", "gif", "video", "gallery", "external"}:
            return media_type
        return "unknown"

    def _canonical_url(self, item: RedditMediaItem) -> str | None:
        if item.permalink and item.permalink.startswith("/"):
            return f"https://www.reddit.com{item.permalink}"
        return item.permalink or item.post_url

    def _media_urls(self, item: RedditMediaItem) -> list[str]:
        urls: list[str] = []
        if item.media_url:
            urls.append(item.media_url)
        urls.extend(item.media_urls or [])
        urls.extend(gallery_item.url for gallery_item in item.gallery_items if gallery_item.url)
        if item.reddit_video:
            video_url = item.reddit_video.get("fallback_url") or item.reddit_video.get("hls_url")
            if isinstance(video_url, str):
                urls.append(video_url)
        return list(dict.fromkeys(urls))

    def _preview_url(self, item: RedditMediaItem, media_urls: list[str]) -> str | None:
        if item.media_type in {"video", "gif"}:
            direct_video = next((url for url in media_urls if is_direct_video(url) or is_reddit_video_url(url)), None)
            return direct_video or item.thumbnail_url
        return media_urls[0] if media_urls else item.thumbnail_url

