from typing import Any
from urllib.parse import urlparse


DIRECT_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".avif")
DIRECT_VIDEO_EXTENSIONS = (".mp4", ".m4v", ".mov", ".webm")
KNOWN_EXTERNAL_MEDIA_HOSTS = (
    "imgur.com",
    "i.imgur.com",
    "redgifs.com",
    "www.redgifs.com",
    "streamable.com",
    "www.streamable.com",
    "gfycat.com",
    "www.gfycat.com",
)


def clean_url(url: Any) -> str | None:
    if not isinstance(url, str):
        return None
    from backend.utils.html import decode_html_entities

    cleaned = (decode_html_entities(url) or "").strip()
    if not cleaned:
        return None
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return cleaned


def url_path_lower(url: str | None) -> str:
    if not url:
        return ""
    return urlparse(url).path.lower()


def is_direct_image(url: str | None) -> bool:
    return url_path_lower(url).endswith(DIRECT_IMAGE_EXTENSIONS)


def is_direct_gif(url: str | None) -> bool:
    return url_path_lower(url).endswith(".gif")


def is_gifv(url: str | None) -> bool:
    return url_path_lower(url).endswith(".gifv")


def is_direct_video(url: str | None) -> bool:
    return url_path_lower(url).endswith(DIRECT_VIDEO_EXTENSIONS)


def host_lower(url: str | None) -> str:
    if not url:
        return ""
    return urlparse(url).hostname or ""


def is_reddit_video_url(url: str | None) -> bool:
    return host_lower(url).lower().endswith("v.redd.it")


def is_known_external_media_url(url: str | None) -> bool:
    host = host_lower(url).lower()
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in KNOWN_EXTERNAL_MEDIA_HOSTS)
