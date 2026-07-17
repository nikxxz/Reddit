from __future__ import annotations

from pathlib import Path
from time import monotonic
from typing import Any

from backend.config import settings
from backend.models.downloads import DownloadRequest
from backend.models.reddit import RedditGalleryItem, RedditMediaItem
from backend.services.downloads.direct import validate_download_url
from backend.services.downloads.errors import MediaResolutionError
from backend.services.downloads.filenames import build_download_filename
from backend.services.reddit.media_cache import normalized_media_cache
from backend.services.reddit.media_hydrator import hydrate_submission_media, validate_post_id
from backend.utils.logging import get_logger
from backend.utils.urls import (
    clean_url,
    is_direct_gif,
    is_direct_image,
    is_direct_video,
    is_known_external_media_url,
    is_reddit_video_url,
    provider_for_url,
)


logger = get_logger(__name__)

CATEGORY_BY_MEDIA_TYPE = {
    "image": "images",
    "video": "videos",
    "gif": "gifs",
    "gallery": "galleries",
    "external": "external",
}

YT_DLP_HOSTS = {
    "reddit.com",
    "www.reddit.com",
    "old.reddit.com",
    "new.reddit.com",
    "v.redd.it",
    "imgur.com",
    "i.imgur.com",
    "redgifs.com",
    "www.redgifs.com",
    "streamable.com",
    "www.streamable.com",
}

RETRYABLE_RESOLUTION_CODES = {
    "hydration_failed",
    "missing_cached_item",
    "hydration_returned_no_media",
}


class ResolvedDownload:
    def __init__(
        self,
        *,
        strategy: str,
        category: str,
        urls: list[str],
        filenames: list[str],
        media_type: str,
        post_id: str,
        provider: str | None = None,
        gallery_items: list[RedditGalleryItem] | None = None,
        selected_gallery_item: RedditGalleryItem | None = None,
    ) -> None:
        self.strategy = strategy
        self.category = category
        self.urls = urls
        self.filenames = filenames
        self.media_type = media_type
        self.post_id = post_id
        self.provider = provider
        self.gallery_items = gallery_items or []
        self.selected_gallery_item = selected_gallery_item

    @property
    def output_dir(self) -> Path:
        return settings.download_dir_path / self.category


async def resolve_download_request(
    request: DownloadRequest,
    *,
    force_hydrate: bool = False,
    job_id: str | None = None,
) -> ResolvedDownload:
    started = monotonic()
    post_id = request.post_id if request.provider == "tumblr" else validate_post_id(request.post_id)
    logger.info(
        "download.resolve.start job_id=%s post_id=%s media_type=%s download_scope=%s gallery_index=%s",
        job_id,
        post_id,
        request.media_type,
        request.download_scope,
        request.gallery_index,
    )

    cache_hit = False
    hydrated = False
    item = None if force_hydrate else normalized_media_cache.get(post_id)
    if item:
        cache_hit = True
        logger.info("download.resolve.cache_hit job_id=%s post_id=%s media_type=%s", job_id, post_id, item.media_type)
    else:
        logger.info("download.resolve.cache_miss job_id=%s post_id=%s", job_id, post_id)
        item = _item_from_request(request)

    if request.provider != "tumblr" and _needs_hydration(item, request):
        logger.info(
            "download.resolve.cache_incomplete job_id=%s post_id=%s cache_hit=%s has_media_url=%s has_post_url=%s has_gallery_metadata=%s has_reddit_video_metadata=%s",
            job_id,
            post_id,
            cache_hit,
            bool(getattr(item, "media_url", None)),
            bool(getattr(item, "post_url", None) or getattr(item, "permalink", None)),
            bool(getattr(item, "gallery_items", None) or getattr(item, "media_urls", None)),
            bool(getattr(item, "reddit_video", None)),
        )
        hydrated = True
        item = await hydrate_submission_media(post_id)

    try:
        resolved = _resolve_item(item, request)
        logger.info(
            "download.resolve.%s.success job_id=%s post_id=%s media_type=%s provider=%s download_scope=%s gallery_index=%s gallery_item_count=%s cache_hit=%s hydrated=%s elapsed_ms=%s",
            "gallery" if resolved.strategy == "gallery" else "video" if resolved.media_type == "video" else "external" if resolved.media_type == "external" else "direct",
            job_id,
            post_id,
            resolved.media_type,
            resolved.provider,
            request.download_scope,
            request.gallery_index,
            len(resolved.gallery_items),
            cache_hit,
            hydrated,
            int((monotonic() - started) * 1000),
        )
        return resolved
    except MediaResolutionError as exc:
        if exc.code in {"invalid_url", "unsafe_url", "unsupported_host"} and cache_hit:
            normalized_media_cache.invalidate(post_id)
        context = _safe_failure_context(job_id, post_id, item, request, cache_hit, hydrated, exc.code, started)
        logger.warning(
            "download.resolve.failed job_id=%s post_id=%s media_type=%s provider=%s download_scope=%s gallery_index=%s gallery_item_count=%s cache_hit=%s hydrated=%s reason_code=%s elapsed_ms=%s has_media_url=%s has_post_url=%s has_permalink=%s has_gallery_metadata=%s has_reddit_video_metadata=%s",
            *context,
        )
        raise


def choose_download_strategy(item: Any) -> str:
    strategy = getattr(item, "download_strategy", None)
    if strategy in {"direct", "yt_dlp", "resolve_details", "unsupported"}:
        return strategy
    media_type = getattr(item, "media_type", "")
    media_url = getattr(item, "media_url", None)
    if media_type in {"image", "gif", "gallery"}:
        return "direct" if media_url or getattr(item, "media_urls", None) else "resolve_details"
    if media_type in {"video", "external"}:
        return "yt_dlp"
    return "unsupported"


def _item_from_request(request: DownloadRequest) -> RedditMediaItem:
    gallery_items = [
        RedditGalleryItem(index=index, url=url)
        for index, url in enumerate(request.gallery_urls)
        if clean_url(url)
    ]
    return RedditMediaItem(
        id=request.post_id,
        title=request.title or "",
        subreddit=request.subreddit or request.provider,
        author=request.author,
        permalink=clean_url(request.post_url),
        post_url=clean_url(request.post_url),
        media_type=request.media_type,
        thumbnail_url=clean_url(request.thumbnail_url),
        media_url=clean_url(request.media_url),
        media_urls=[url for url in (clean_url(url) for url in request.gallery_urls) if url],
        gallery_items=gallery_items,
        gallery_count=len(gallery_items),
        is_gallery=request.media_type == "gallery",
        download_strategy=request.download_strategy or "unsupported",
    )


def _needs_hydration(item: RedditMediaItem | None, request: DownloadRequest) -> bool:
    if item is None:
        return True
    if item.media_type not in {"image", "gif", "video", "gallery", "external"}:
        return True
    if request.download_scope in {"gallery_current", "gallery_all", "gallery_missing"}:
        if not _gallery_urls(item):
            return True
        return False
    if item.media_type == "video" and choose_download_strategy(item) == "yt_dlp":
        return not (item.post_url or item.permalink or is_reddit_video_url(item.media_url))
    if item.media_type == "external":
        return not bool(item.post_url or item.media_url)
    if item.media_type in {"image", "gif"}:
        return not bool(item.media_url)
    return False


def _resolve_item(item: RedditMediaItem | None, request: DownloadRequest) -> ResolvedDownload:
    if item is None:
        raise MediaResolutionError("missing_cached_item")
    if request.download_scope in {"gallery_current", "gallery_all", "gallery_missing"}:
        return _resolve_gallery(item, request)
    media_type = item.media_type
    if media_type == "image":
        url = _required_url(item.media_url, "missing_media_url")
        return _resolved(item, request, "direct", "images", [url])
    if media_type == "gif":
        url = _required_url(item.media_url, "missing_media_url")
        strategy = "direct" if is_direct_gif(url) or is_direct_image(url) or is_direct_video(url) else "yt_dlp"
        return _resolved(item, request, strategy, "gifs", [url])
    if media_type == "video":
        return _resolve_video(item, request)
    if media_type == "external":
        return _resolve_external(item, request)
    raise MediaResolutionError("unsupported_media_type")


def _resolve_video(item: RedditMediaItem, request: DownloadRequest) -> ResolvedDownload:
    url = clean_url(item.post_url) or clean_url(item.permalink)
    if is_reddit_video_url(item.media_url):
        url = url or item.media_url
    if choose_download_strategy(item) == "direct" or item.provider == "tumblr":
        direct = _required_url(item.media_url, "missing_media_url")
        return _resolved(item, request, "direct", "videos", [direct])
    if not url:
        if item.reddit_video:
            raise MediaResolutionError("reddit_video_metadata_missing")
        raise MediaResolutionError("missing_post_url")
    return _resolved(item, request, "yt_dlp", "videos", [url])


def _resolve_external(item: RedditMediaItem, request: DownloadRequest) -> ResolvedDownload:
    url = clean_url(item.post_url) or clean_url(item.media_url)
    url = _required_url(url, "missing_post_url")
    provider = provider_for_url(url)
    if not provider:
        raise MediaResolutionError("external_media_unsupported")
    if provider == "imgur" and is_direct_image(url):
        return _resolved(item, request, "direct", "external", [url])
    if not is_known_external_media_url(url):
        raise MediaResolutionError("unsupported_host")
    return _resolved(item, request, "yt_dlp", "external", [url])


def _resolve_gallery(item: RedditMediaItem, request: DownloadRequest) -> ResolvedDownload:
    gallery_items = item.gallery_items or [
        RedditGalleryItem(index=index, url=url)
        for index, url in enumerate(item.media_urls)
        if clean_url(url)
    ]
    if not gallery_items:
        raise MediaResolutionError("missing_gallery_urls")
    if request.download_scope == "gallery_current":
        index = request.gallery_index
        if index is None or index < 0 or index >= len(gallery_items):
            raise MediaResolutionError("invalid_gallery_index")
        selected = gallery_items[index]
        urls = [selected.url]
        indices = [selected.index + 1]
        selected_item = selected
    else:
        urls = [gallery_item.url for gallery_item in gallery_items]
        indices = [gallery_item.index + 1 for gallery_item in gallery_items]
        selected_item = None
    for url in urls:
        _validate_direct(url)
    filenames = [
        build_download_filename(
            subreddit=item.subreddit or request.subreddit or request.provider,
            author=item.author or request.author,
            title=item.title or request.title,
            post_id=item.id or request.post_id,
            source_url=url,
            gallery_index=index,
        )
        for url, index in zip(urls, indices)
    ]
    return ResolvedDownload(
        strategy="gallery",
        category="galleries",
        urls=urls,
        filenames=filenames,
        media_type="gallery",
        post_id=item.id or request.post_id,
        provider=item.provider,
        gallery_items=gallery_items,
        selected_gallery_item=selected_item,
    )


def _resolved(
    item: RedditMediaItem,
    request: DownloadRequest,
    strategy: str,
    category: str,
    urls: list[str],
) -> ResolvedDownload:
    for url in urls:
        try:
            validate_download_url(url, allowed_hosts=YT_DLP_HOSTS if strategy == "yt_dlp" else None)
        except MediaResolutionError:
            raise
    filenames = [
        build_download_filename(
            subreddit=item.subreddit or request.subreddit or request.provider,
            author=item.author or request.author,
            title=item.title or request.title,
            post_id=item.id or request.post_id,
            source_url=url,
        )
        for url in urls
    ]
    return ResolvedDownload(
        strategy=strategy,
        category=category,
        urls=urls,
        filenames=filenames,
        media_type=item.media_type,
        post_id=item.id or request.post_id,
        provider=item.provider or request.provider or provider_for_url(urls[0]),
        gallery_items=item.gallery_items,
    )


def _gallery_urls(item: RedditMediaItem) -> list[str]:
    if item.gallery_items:
        return [gallery_item.url for gallery_item in item.gallery_items]
    return item.media_urls or ([item.media_url] if item.media_url else [])


def _required_url(url: str | None, code: str) -> str:
    cleaned = clean_url(url)
    if not cleaned:
        raise MediaResolutionError(code)
    return cleaned


def _validate_direct(url: str) -> None:
    validate_download_url(url)


def _safe_failure_context(
    job_id: str | None,
    post_id: str,
    item: RedditMediaItem | None,
    request: DownloadRequest,
    cache_hit: bool,
    hydrated: bool,
    reason_code: str,
    started: float,
) -> tuple[object, ...]:
    return (
        job_id,
        post_id,
        getattr(item, "media_type", request.media_type),
        getattr(item, "provider", None),
        request.download_scope,
        request.gallery_index,
        len(getattr(item, "gallery_items", []) or []),
        cache_hit,
        hydrated,
        reason_code,
        int((monotonic() - started) * 1000),
        bool(getattr(item, "media_url", None)),
        bool(getattr(item, "post_url", None)),
        bool(getattr(item, "permalink", None)),
        bool(getattr(item, "gallery_items", None) or getattr(item, "media_urls", None)),
        bool(getattr(item, "reddit_video", None)),
    )
