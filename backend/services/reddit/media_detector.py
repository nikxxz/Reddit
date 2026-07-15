from __future__ import annotations

import re
from typing import Any

from backend.utils.urls import is_direct_gif, is_direct_image, is_gifv


ALLOWED_MEDIA_TYPES = {"all", "image", "video", "gif", "gallery"}
ALLOWED_SORTS = {"relevance", "hot", "top", "new", "comments"}
ALLOWED_TIME_FILTERS = {"hour", "day", "week", "month", "year", "all"}
SUBREDDIT_NAME_RE = re.compile(r"^[A-Za-z0-9_]{2,21}$")


def get_value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def reddit_video(submission: Any) -> Any:
    media = get_value(submission, "media") or {}
    video = get_value(media, "reddit_video")
    if video:
        return video
    secure_media = get_value(submission, "secure_media") or {}
    return get_value(secure_media, "reddit_video")


def detect_media_type(submission: Any) -> str | None:
    if bool(get_value(submission, "is_gallery", False)):
        return "gallery"
    if reddit_video(submission) or bool(get_value(submission, "is_video", False)):
        return "video"

    url = get_value(submission, "url")
    if is_direct_gif(url):
        return "gif"
    if is_gifv(url):
        return "video"
    if is_direct_image(url):
        return "image"
    return None
