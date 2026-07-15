from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.config import settings
from backend.models.downloads import DownloadRequest
from backend.services.downloads.direct import validate_download_url
from backend.services.downloads.errors import DownloadError
from backend.services.downloads.filenames import build_download_filename
from backend.utils.urls import is_direct_gif, is_direct_image, is_direct_video


def choose_download_strategy(item: Any) -> str:
    strategy = getattr(item, "download_strategy", None)
    if strategy in {"direct", "yt_dlp", "resolve_details", "unsupported"}:
        return strategy

    media_type = getattr(item, "media_type", "")
    media_url = getattr(item, "media_url", None)
    if media_type in {"image", "gif", "gallery"}:
        return "direct" if media_url or getattr(item, "media_urls", None) else "resolve_details"
    if media_type == "video":
        return "yt_dlp"
    if media_type == "external":
        return "yt_dlp"
    return "unsupported"


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
    "v.redd.it",
    "imgur.com",
    "i.imgur.com",
    "redgifs.com",
    "www.redgifs.com",
    "streamable.com",
    "www.streamable.com",
}


class ResolvedDownload:
    def __init__(
        self,
        *,
        strategy: str,
        category: str,
        urls: list[str],
        filenames: list[str],
    ) -> None:
        self.strategy = strategy
        self.category = category
        self.urls = urls
        self.filenames = filenames

    @property
    def output_dir(self) -> Path:
        return settings.download_dir_path / self.category


def resolve_download_request(request: DownloadRequest) -> ResolvedDownload:
    scope = request.download_scope
    media_type = request.media_type

    if scope in {"gallery_current", "gallery_all"}:
        return _resolve_gallery(request)

    if media_type == "image":
        url = _required_url(request.media_url)
        validate_download_url(url)
        return _resolved_direct(request, "images", [url])

    if media_type == "gif":
        url = _required_url(request.media_url)
        validate_download_url(url)
        strategy = "direct" if is_direct_gif(url) or is_direct_image(url) or is_direct_video(url) else "yt_dlp"
        return _resolved(request, strategy, "gifs", [url])

    if media_type == "video":
        url = _required_url(request.media_url or request.post_url)
        strategy = "direct" if is_direct_video(url) else "yt_dlp"
        return _resolved(request, strategy, "videos", [url])

    if media_type == "external":
        url = _required_url(request.post_url or request.media_url)
        return _resolved(request, "yt_dlp", "external", [url])

    raise DownloadError("The selected media cannot be downloaded.")


def _resolve_gallery(request: DownloadRequest) -> ResolvedDownload:
    urls = request.gallery_urls or ([request.media_url] if request.media_url else [])
    if request.download_scope == "gallery_current":
        index = request.gallery_index
        if index is None or index < 0 or index >= len(urls):
            raise DownloadError("The media URL is invalid.")
        urls = [urls[index]]
        indices = [index + 1]
    else:
        indices = list(range(1, len(urls) + 1))

    if not urls:
        raise DownloadError("The media URL is invalid.")

    for url in urls:
        validate_download_url(url)

    filenames = [
        build_download_filename(
            subreddit=request.subreddit,
            author=request.author,
            title=request.title,
            post_id=request.post_id,
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
    )


def _resolved_direct(request: DownloadRequest, category: str, urls: list[str]) -> ResolvedDownload:
    return _resolved(request, "direct", category, urls)


def _resolved(
    request: DownloadRequest,
    strategy: str,
    category: str,
    urls: list[str],
) -> ResolvedDownload:
    for url in urls:
        validate_download_url(url, allowed_hosts=YT_DLP_HOSTS if strategy == "yt_dlp" else None)

    filenames = [
        build_download_filename(
            subreddit=request.subreddit,
            author=request.author,
            title=request.title,
            post_id=request.post_id,
            source_url=url,
        )
        for url in urls
    ]
    return ResolvedDownload(
        strategy=strategy,
        category=category,
        urls=urls,
        filenames=filenames,
    )


def _required_url(url: str | None) -> str:
    if not url:
        raise DownloadError("The media URL is invalid.")
    return url
