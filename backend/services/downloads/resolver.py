from __future__ import annotations

from typing import Any


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
