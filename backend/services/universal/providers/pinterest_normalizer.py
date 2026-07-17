from __future__ import annotations

from html import unescape
import re

from backend.models.universal_search import UniversalItemCapabilities, UniversalMediaItem, UniversalMediaType
from backend.services.universal.providers.pinterest_models import PinterestExtractedAsset, PinterestExtractedPin
from backend.services.universal.providers.pinterest_urls import is_safe_preview_url


HTML_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def normalize_pinterest_records(
    records: list[dict[str, object]],
    *,
    media_types: list[UniversalMediaType],
    collection_label: str | None = None,
) -> list[UniversalMediaItem]:
    items = []
    seen = set()
    for record in records:
        pin = _pin_from_record(record, collection_label=collection_label)
        if not pin or pin.pin_id in seen:
            continue
        seen.add(pin.pin_id)
        item = _item_from_pin(pin)
        if item and item.media_type in media_types:
            items.append(item)
    return items


def _pin_from_record(record: dict[str, object], *, collection_label: str | None) -> PinterestExtractedPin | None:
    pin_id = _safe_str(record.get("pin_id") or record.get("id") or record.get("pinId"))
    url = _safe_str(record.get("webpage_url") or record.get("url") or record.get("pin_url"))
    if not pin_id and url:
        pin_id = _pin_id_from_url(url)
    if not pin_id:
        return None
    canonical = f"https://www.pinterest.com/pin/{pin_id}/"
    assets = _assets_from_record(record)
    if not assets:
        return None
    board = _plain(_safe_str(record.get("board") or record.get("board_name") or record.get("collection")) or "")
    author = _plain(_safe_str(record.get("creator") or record.get("author") or record.get("username") or record.get("uploader")) or "")
    description = _plain(_safe_str(record.get("description") or record.get("summary") or record.get("alt")) or "")
    title = _title(record, description, board, author)
    return PinterestExtractedPin(
        pin_id=pin_id,
        canonical_url=canonical,
        title=title,
        description=description or None,
        author=author or None,
        collection=board or None,
        collection_label=collection_label or ("Board" if board else "Profile"),
        assets=assets,
    )


def _assets_from_record(record: dict[str, object]) -> list[PinterestExtractedAsset]:
    candidates = []
    for key in ("story_pages", "story", "assets", "media"):
        value = record.get(key)
        if isinstance(value, list):
            candidates.extend(item for item in value if isinstance(item, dict))
    if not candidates:
        candidates = [record]
    assets = []
    for candidate in candidates:
        asset = _asset_from_candidate(candidate, len(assets))
        if asset:
            assets.append(asset)
    return assets


def _asset_from_candidate(candidate: dict[str, object], index: int) -> PinterestExtractedAsset | None:
    video_url = _first_safe(candidate, ["video_url", "video", "mp4", "duration_url"])
    image_url = _largest_image(candidate)
    thumbnail = _first_safe(candidate, ["thumbnail", "thumbnail_url", "thumb", "poster"]) or image_url
    if video_url:
        return PinterestExtractedAsset(
            index=index,
            media_type="video",
            thumbnail_url=thumbnail,
            preview_url=video_url,
            width=_safe_int(candidate.get("width")),
            height=_safe_int(candidate.get("height")),
            duration_seconds=_safe_int(candidate.get("duration") or candidate.get("duration_seconds")),
        )
    if image_url:
        return PinterestExtractedAsset(
            index=index,
            media_type="image",
            thumbnail_url=thumbnail,
            preview_url=image_url,
            width=_safe_int(candidate.get("width")),
            height=_safe_int(candidate.get("height")),
        )
    return None


def _item_from_pin(pin: PinterestExtractedPin) -> UniversalMediaItem | None:
    if not pin.assets:
        return None
    media_type: UniversalMediaType = "gallery" if len(pin.assets) > 1 else pin.assets[0].media_type
    return UniversalMediaItem(
        provider="pinterest",
        provider_item_id=pin.pin_id,
        canonical_url=pin.canonical_url,
        title=(pin.title or "Untitled Pinterest Pin")[:180],
        description=(pin.description or "")[:500] or None,
        author=pin.author,
        collection=pin.collection,
        media_type=media_type,
        thumbnail_url=next((asset.thumbnail_url for asset in pin.assets if asset.thumbnail_url), None),
        preview_url=pin.assets[0].preview_url,
        media_urls=[asset.preview_url for asset in pin.assets if asset.preview_url],
        media_count=len(pin.assets) if len(pin.assets) > 1 else 1,
        width=pin.assets[0].width,
        height=pin.assets[0].height,
        duration_seconds=pin.assets[0].duration_seconds,
        nsfw=False,
        safety_unknown=True,
        source_metadata={
            "collection_label": pin.collection_label,
            "assets": [
                {
                    "index": asset.index,
                    "media_type": asset.media_type,
                    "thumbnail_url": asset.thumbnail_url,
                    "preview_url": asset.preview_url,
                    "width": asset.width,
                    "height": asset.height,
                    "duration_seconds": asset.duration_seconds,
                }
                for asset in pin.assets
            ],
        },
        capabilities=UniversalItemCapabilities(preview=True, download_single=False, download_all=False),
    )


def _largest_image(record: dict[str, object]) -> str | None:
    direct = _first_safe(record, ["image", "image_url", "url", "src"])
    images = record.get("images") or record.get("thumbnails")
    variants = []
    if isinstance(images, dict):
        variants.extend(value for value in images.values() if isinstance(value, dict))
    elif isinstance(images, list):
        variants.extend(value for value in images if isinstance(value, dict))
    best = None
    best_area = -1
    for variant in variants:
        url = _safe_url(_safe_str(variant.get("url") or variant.get("src")))
        if not url:
            continue
        area = (_safe_int(variant.get("width")) or 0) * (_safe_int(variant.get("height")) or 0)
        if area >= best_area:
            best = url
            best_area = area
    return best or direct


def _first_safe(record: dict[str, object], keys: list[str]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, dict):
            value = value.get("url") or value.get("src")
        url = _safe_url(_safe_str(value))
        if url:
            return url
    return None


def _title(record: dict[str, object], description: str, board: str, author: str) -> str:
    for key in ("title", "name"):
        value = _plain(_safe_str(record.get(key)) or "")
        if value:
            return value[:180]
    if description:
        return description[:180]
    if board:
        return board[:180]
    if author:
        return f"Pinterest Pin by {author}"[:180]
    return "Untitled Pinterest Pin"


def _pin_id_from_url(url: str) -> str | None:
    parts = [part for part in url.split("/") if part]
    if "pin" in parts:
        index = parts.index("pin")
        if index + 1 < len(parts) and parts[index + 1].isdigit():
            return parts[index + 1]
    return None


def _safe_url(value: str | None) -> str | None:
    return value if value and is_safe_preview_url(value) else None


def _plain(value: str) -> str:
    return SPACE_RE.sub(" ", unescape(HTML_RE.sub(" ", value))).strip()


def _safe_str(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value.strip() else None


def _safe_int(value: object) -> int | None:
    try:
        return int(float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None
