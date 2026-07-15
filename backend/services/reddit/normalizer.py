from __future__ import annotations

from typing import Any

from backend.models.reddit import RedditMediaItem
from backend.services.reddit.media_detector import get_value, reddit_video
from backend.utils.urls import clean_url, is_direct_gif, is_direct_image, is_gifv

PLACEHOLDER_THUMBNAILS = {"", "self", "default", "nsfw", "spoiler", "image"}


def safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def subreddit_name(submission: Any) -> str | None:
    subreddit = get_value(submission, "subreddit")
    display_name = get_value(subreddit, "display_name")
    return str(display_name or subreddit) if subreddit else None


def author_name(submission: Any) -> str | None:
    author = get_value(submission, "author")
    if author is None:
        return None
    return str(author)


def permalink(submission: Any) -> str | None:
    value = get_value(submission, "permalink")
    if not value:
        return None
    value = str(value)
    if value.startswith("http://") or value.startswith("https://"):
        return clean_url(value)
    return clean_url(f"https://www.reddit.com{value}")


def preview_image_url(submission: Any) -> str | None:
    preview = get_value(submission, "preview") or {}
    images = get_value(preview, "images") or []
    if not images:
        return None
    image = images[0]
    source = get_value(image, "source") or {}
    url = clean_url(get_value(source, "url"))
    if url:
        return url
    resolutions = get_value(image, "resolutions") or []
    if resolutions:
        return clean_url(get_value(resolutions[-1], "url"))
    return None


def valid_thumbnail(submission: Any) -> str | None:
    thumbnail = clean_url(get_value(submission, "thumbnail"))
    if not thumbnail or thumbnail.lower() in PLACEHOLDER_THUMBNAILS:
        return None
    return thumbnail


def gallery_preview_url(item_meta: Any) -> str | None:
    previews = get_value(item_meta, "p") or []
    if isinstance(previews, list) and previews:
        preview_url = clean_url(get_value(previews[-1], "u"))
        if preview_url:
            return preview_url
    preview_url = clean_url(get_value(item_meta, "p"))
    if preview_url:
        return preview_url
    source = get_value(item_meta, "s") or {}
    return clean_url(get_value(source, "u") or get_value(source, "gif"))


def base_item(
    submission: Any,
    media_type: str,
    media_url: str | None,
    thumbnail_url: str | None,
    width: int | None = None,
    height: int | None = None,
    duration: int | None = None,
    is_gallery: bool = False,
    gallery_count: int = 0,
) -> RedditMediaItem:
    return RedditMediaItem(
        id=str(get_value(submission, "id") or ""),
        title=str(get_value(submission, "title") or ""),
        subreddit=subreddit_name(submission),
        author=author_name(submission),
        created_utc=get_value(submission, "created_utc"),
        permalink=permalink(submission),
        post_url=clean_url(get_value(submission, "url")) or permalink(submission),
        media_type=media_type,
        thumbnail_url=thumbnail_url,
        media_url=media_url,
        width=width,
        height=height,
        duration=duration,
        is_gallery=is_gallery,
        gallery_count=gallery_count,
        is_nsfw=bool(get_value(submission, "over_18", False)),
    )


def extract_image_media(submission: Any) -> RedditMediaItem | None:
    url = clean_url(get_value(submission, "url"))
    if not is_direct_image(url):
        return None
    return base_item(
        submission,
        "image",
        url,
        preview_image_url(submission) or valid_thumbnail(submission) or url,
    )


def extract_gif_media(submission: Any) -> RedditMediaItem | None:
    url = clean_url(get_value(submission, "url"))
    if not is_direct_gif(url):
        return None
    return base_item(
        submission,
        "gif",
        url,
        preview_image_url(submission) or valid_thumbnail(submission),
    )


def extract_video_media(submission: Any) -> RedditMediaItem | None:
    video = reddit_video(submission)
    url = clean_url(get_value(video, "fallback_url")) if video else None
    direct_url = clean_url(get_value(submission, "url"))
    if not url and is_gifv(direct_url):
        url = direct_url
    if not url and not bool(get_value(submission, "is_video", False)):
        return None
    return base_item(
        submission,
        "video",
        url or direct_url,
        preview_image_url(submission) or valid_thumbnail(submission),
        width=safe_int(get_value(video, "width")) if video else None,
        height=safe_int(get_value(video, "height")) if video else None,
        duration=safe_int(get_value(video, "duration")) if video else None,
    )


def extract_gallery_media(submission: Any) -> RedditMediaItem | None:
    if not bool(get_value(submission, "is_gallery", False)):
        return None

    gallery_data = get_value(submission, "gallery_data") or {}
    gallery_items = get_value(gallery_data, "items") or []
    media_metadata = get_value(submission, "media_metadata") or {}
    first_meta = None
    for gallery_item in gallery_items:
        media_id = get_value(gallery_item, "media_id")
        if media_id:
            first_meta = get_value(media_metadata, str(media_id))
            if first_meta:
                break
    if first_meta is None and media_metadata:
        first_meta = next(iter(media_metadata.values()))

    source = get_value(first_meta, "s") or {}
    media_url = clean_url(get_value(source, "u") or get_value(source, "gif"))
    thumbnail = preview_image_url(submission) or gallery_preview_url(first_meta)
    count = len(gallery_items) if gallery_items else len(media_metadata)
    if not media_url and not thumbnail:
        return None

    return base_item(
        submission,
        "gallery",
        media_url,
        thumbnail or media_url,
        width=safe_int(get_value(source, "x")),
        height=safe_int(get_value(source, "y")),
        is_gallery=True,
        gallery_count=count,
    )


def extract_external_media(submission: Any) -> RedditMediaItem | None:
    return extract_gif_media(submission) or extract_image_media(submission)


def crosspost_source(submission: Any) -> Any | None:
    crossposts = get_value(submission, "crosspost_parent_list") or []
    if crossposts and isinstance(crossposts, list):
        return crossposts[0]
    return None


def copy_item(item: RedditMediaItem, updates: dict[str, Any]) -> RedditMediaItem:
    if hasattr(item, "model_copy"):
        return item.model_copy(update=updates)
    return item.copy(update=updates)


def normalize_submission(submission: Any) -> RedditMediaItem | None:
    item = (
        extract_gallery_media(submission)
        or extract_video_media(submission)
        or extract_gif_media(submission)
        or extract_image_media(submission)
        or extract_external_media(submission)
    )
    if item:
        return item

    crosspost = crosspost_source(submission)
    if not crosspost:
        return None

    crosspost_item = normalize_submission(crosspost)
    if not crosspost_item:
        return None

    return copy_item(
        crosspost_item,
        {
            "id": str(get_value(submission, "id") or crosspost_item.id),
            "title": str(get_value(submission, "title") or crosspost_item.title),
            "subreddit": subreddit_name(submission) or crosspost_item.subreddit,
            "author": author_name(submission),
            "created_utc": get_value(submission, "created_utc"),
            "permalink": permalink(submission) or crosspost_item.permalink,
            "post_url": clean_url(get_value(submission, "url"))
            or permalink(submission)
            or crosspost_item.post_url,
            "is_nsfw": bool(get_value(submission, "over_18", crosspost_item.is_nsfw)),
        },
    )
