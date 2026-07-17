from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
import re
from urllib.parse import urlparse

from backend.models.reddit import RedditGalleryItem, RedditMediaItem
from backend.models.universal_search import UniversalItemCapabilities, UniversalMediaItem, UniversalMediaType
from backend.services.reddit.media_cache import normalized_media_cache
from backend.services.universal.providers.tumblr_models import TumblrMediaAsset
from backend.utils.urls import clean_url


HTML_RE = re.compile(r"<[^>]+>")


def normalize_tumblr_posts(
    posts: list[dict[str, object]],
    *,
    media_types: list[UniversalMediaType],
    include_nsfw: bool,
) -> list[UniversalMediaItem]:
    items = []
    for post in posts:
        item = normalize_tumblr_post(post)
        if not item:
            continue
        if item.nsfw and not include_nsfw:
            continue
        if item.media_type not in media_types:
            continue
        items.append(item)
    return items


def normalize_tumblr_post(post: dict[str, object]) -> UniversalMediaItem | None:
    post_id = str(post.get("id_string") or post.get("id") or "").strip()
    if not post_id:
        return None
    assets = _npf_assets(post) or _legacy_assets(post)
    if not assets:
        return None
    title = _title(post)
    blog_name = _safe_str(post.get("blog_name")) or _blog_name_from_url(_safe_str(post.get("post_url")))
    canonical_url = _safe_url(_safe_str(post.get("post_url")))
    media_type = _item_media_type(assets)
    media_urls = [asset.download_url for asset in assets if asset.download_url]
    thumbnail = next((asset.thumbnail_url or asset.preview_url for asset in assets if asset.thumbnail_url or asset.preview_url), None)
    preview = assets[0].preview_url or assets[0].download_url
    item = UniversalMediaItem(
        provider="tumblr",
        provider_item_id=post_id,
        canonical_url=canonical_url,
        title=title,
        description=_caption(post),
        author=blog_name,
        collection=blog_name,
        media_type=media_type,
        thumbnail_url=thumbnail,
        preview_url=preview,
        media_urls=media_urls,
        media_count=len(assets) if len(assets) > 1 else None,
        width=assets[0].width,
        height=assets[0].height,
        duration_seconds=assets[0].duration_seconds,
        created_at=_created_at(post),
        nsfw=_is_nsfw(post),
        source_metadata={
            "blog_name": blog_name,
            "assets": [
                {
                    "index": asset.index,
                    "media_type": asset.media_type,
                    "download_url": asset.download_url,
                    "preview_url": asset.preview_url,
                    "thumbnail_url": asset.thumbnail_url,
                    "mime_type": asset.mime_type,
                    "width": asset.width,
                    "height": asset.height,
                    "duration_seconds": asset.duration_seconds,
                }
                for asset in assets
            ],
        },
        capabilities=UniversalItemCapabilities(
            preview=True,
            download_single=bool(media_urls),
            download_all=len(media_urls) > 1,
        ),
    )
    normalized_media_cache.set(_download_cache_item(item, assets))
    return item


def _npf_assets(post: dict[str, object]) -> list[TumblrMediaAsset]:
    blocks = post.get("content")
    if not isinstance(blocks, list):
        return []
    assets: list[TumblrMediaAsset] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "image":
            media = _variants(block.get("media"))
            best = _largest_variant(media)
            thumb = _smallest_variant(media) or best
            if best:
                assets.append(
                    TumblrMediaAsset(
                        index=len(assets),
                        media_type=_image_type(best),
                        preview_url=_safe_url(best.get("url")),
                        download_url=_safe_url(best.get("url")),
                        thumbnail_url=_safe_url(thumb.get("url")) if thumb else None,
                        width=_safe_int(best.get("width")),
                        height=_safe_int(best.get("height")),
                        mime_type=_safe_str(best.get("type")),
                    )
                )
        elif block_type == "video":
            media = _as_dict(block.get("media"))
            url = _safe_url(_safe_str(media.get("url")) or _safe_str(block.get("url")))
            poster = _safe_url(_safe_str(block.get("poster")) or _safe_str(media.get("poster")))
            if url or poster:
                assets.append(
                    TumblrMediaAsset(
                        index=len(assets),
                        media_type="video",
                        preview_url=url,
                        download_url=url,
                        thumbnail_url=poster,
                        width=_safe_int(media.get("width") or block.get("width")),
                        height=_safe_int(media.get("height") or block.get("height")),
                        duration_seconds=_safe_int(media.get("duration") or block.get("duration")),
                        mime_type=_safe_str(media.get("type")),
                    )
                )
    return assets


def _legacy_assets(post: dict[str, object]) -> list[TumblrMediaAsset]:
    assets: list[TumblrMediaAsset] = []
    photos = post.get("photos")
    if isinstance(photos, list):
        for photo in photos:
            if not isinstance(photo, dict):
                continue
            variants = [_as_dict(photo.get("original_size")), *_alt_sizes(photo)]
            best = _largest_variant(variants)
            thumb = _smallest_variant(variants) or best
            if not best:
                continue
            assets.append(
                TumblrMediaAsset(
                    index=len(assets),
                    media_type=_image_type(best),
                    preview_url=_safe_url(best.get("url")),
                    download_url=_safe_url(best.get("url")),
                    thumbnail_url=_safe_url(thumb.get("url")) if thumb else None,
                    width=_safe_int(best.get("width")),
                    height=_safe_int(best.get("height")),
                )
            )
    if assets:
        return assets
    video_url = _safe_url(_safe_str(post.get("video_url")) or _safe_str(post.get("permalink_url")))
    if video_url:
        assets.append(
            TumblrMediaAsset(
                index=0,
                media_type="video",
                preview_url=video_url,
                download_url=video_url if _is_tumblr_media_url(video_url) else None,
                thumbnail_url=_safe_url(_safe_str(post.get("thumbnail_url"))),
                width=_safe_int(post.get("thumbnail_width")),
                height=_safe_int(post.get("thumbnail_height")),
            )
        )
    return assets


def _download_cache_item(item: UniversalMediaItem, assets: list[TumblrMediaAsset]) -> RedditMediaItem:
    gallery_items = [
        RedditGalleryItem(
            index=asset.index,
            media_type=asset.media_type,
            url=asset.download_url,
            mime_type=asset.mime_type,
            width=asset.width,
            height=asset.height,
        )
        for asset in assets
        if asset.download_url
    ]
    return RedditMediaItem(
        id=item.provider_item_id,
        title=item.title,
        subreddit="tumblr",
        author=item.author,
        created_utc=item.created_at.timestamp() if item.created_at else None,
        permalink=item.canonical_url,
        post_url=item.canonical_url,
        media_type=item.media_type,
        thumbnail_url=item.thumbnail_url,
        media_url=assets[0].download_url if assets else None,
        media_urls=[asset.download_url for asset in assets if asset.download_url],
        gallery_items=gallery_items,
        provider="tumblr",
        width=item.width,
        height=item.height,
        duration=item.duration_seconds,
        is_gallery=item.media_type == "gallery",
        gallery_count=len(gallery_items),
        is_nsfw=item.nsfw,
        download_strategy="direct" if item.media_type in {"image", "gif", "gallery", "video"} else "unsupported",
    )


def _item_media_type(assets: list[TumblrMediaAsset]) -> UniversalMediaType:
    if len(assets) > 1:
        return "gallery"
    return assets[0].media_type


def _image_type(variant: dict[str, object]) -> UniversalMediaType:
    url = str(variant.get("url") or "")
    mime_type = str(variant.get("type") or "").lower()
    return "gif" if mime_type == "image/gif" or urlparse(url).path.lower().endswith(".gif") else "image"


def _title(post: dict[str, object]) -> str:
    for key in ("title", "summary", "slug"):
        value = _safe_str(post.get(key))
        if value:
            return _plain(value)[:180]
    blocks = post.get("content")
    if isinstance(blocks, list):
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text = _plain(_safe_str(block.get("text")) or "")
                if text:
                    return text[:180]
    return "Untitled Tumblr post"


def _caption(post: dict[str, object]) -> str | None:
    value = _safe_str(post.get("caption") or post.get("summary"))
    return _plain(value) if value else None


def _plain(value: str) -> str:
    return unescape(HTML_RE.sub(" ", value)).strip()


def _created_at(post: dict[str, object]) -> datetime | None:
    timestamp = _safe_int(post.get("timestamp"))
    return datetime.fromtimestamp(timestamp, timezone.utc) if timestamp else None


def _is_nsfw(post: dict[str, object]) -> bool:
    state = str(post.get("state") or "").lower()
    tags = [str(tag).lower() for tag in post.get("tags", [])] if isinstance(post.get("tags"), list) else []
    return state == "private" or any(tag in {"nsfw", "adult"} for tag in tags)


def _variants(value: object) -> list[dict[str, object]]:
    if isinstance(value, list):
        return [_as_dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _alt_sizes(photo: dict[str, object]) -> list[dict[str, object]]:
    sizes = photo.get("alt_sizes")
    return [_as_dict(size) for size in sizes] if isinstance(sizes, list) else []


def _largest_variant(variants: list[dict[str, object]]) -> dict[str, object] | None:
    candidates = [variant for variant in variants if _safe_url(variant.get("url"))]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (_safe_int(item.get("width")) or 0) * (_safe_int(item.get("height")) or 0))


def _smallest_variant(variants: list[dict[str, object]]) -> dict[str, object] | None:
    candidates = [variant for variant in variants if _safe_url(variant.get("url"))]
    if not candidates:
        return None
    return min(candidates, key=lambda item: abs((_safe_int(item.get("width")) or 0) - 320))


def _safe_url(value: object) -> str | None:
    return clean_url(str(value)) if isinstance(value, str) else None


def _safe_str(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value.strip() else None


def _safe_int(value: object) -> int | None:
    try:
        return int(float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _blog_name_from_url(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url).hostname or ""
    if host.endswith(".tumblr.com"):
        return host.removesuffix(".tumblr.com")
    path = urlparse(url).path.strip("/").split("/")
    return path[0] if host in {"www.tumblr.com", "tumblr.com"} and path else None


def _is_tumblr_media_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "media.tumblr.com" or host.endswith(".media.tumblr.com") or host.endswith(".tumblr.com")
