from __future__ import annotations

import asyncio
import re
from time import monotonic

from praw.exceptions import PRAWException
from prawcore import exceptions as prawcore_exceptions

from backend.config import settings
from backend.models.reddit import RedditMediaItem
from backend.services.downloads.errors import MediaResolutionError
from backend.services.reddit.client import RedditClientProvider
from backend.services.reddit.media_cache import normalized_media_cache
from backend.services.reddit.normalizer import normalize_submission
from backend.utils.logging import get_logger


POST_ID_RE = re.compile(r"^[a-z0-9]{3,12}$", re.IGNORECASE)
logger = get_logger(__name__)


def validate_post_id(post_id: str | None) -> str:
    if not post_id or not POST_ID_RE.fullmatch(post_id):
        raise MediaResolutionError(
            "invalid_url",
            "The selected Reddit post identifier is invalid.",
            {"post_id_present": bool(post_id)},
        )
    return post_id


async def hydrate_submission_media(
    post_id: str,
    *,
    client_provider: RedditClientProvider | None = None,
) -> RedditMediaItem:
    post_id = validate_post_id(post_id)
    provider = client_provider or RedditClientProvider()
    started = monotonic()
    logger.info("download.resolve.hydration.start post_id=%s", post_id)
    try:
        item = await asyncio.wait_for(
            asyncio.to_thread(_hydrate_sync, provider, post_id),
            timeout=settings.reddit_hydration_timeout,
        )
    except asyncio.TimeoutError as exc:
        logger.warning(
            "download.resolve.hydration.failed post_id=%s reason_code=hydration_failed elapsed_ms=%s",
            post_id,
            int((monotonic() - started) * 1000),
        )
        raise MediaResolutionError("hydration_failed", debug_context={"post_id": post_id}) from exc
    except MediaResolutionError:
        raise
    except (
        PRAWException,
        prawcore_exceptions.PrawcoreException,
        ConnectionError,
        TimeoutError,
        ValueError,
        RuntimeError,
    ) as exc:
        logger.warning(
            "download.resolve.hydration.failed post_id=%s reason_code=hydration_failed error_type=%s elapsed_ms=%s",
            post_id,
            exc.__class__.__name__,
            int((monotonic() - started) * 1000),
        )
        raise MediaResolutionError("hydration_failed", debug_context={"post_id": post_id}) from exc

    normalized_media_cache.set(item)
    logger.info(
        "download.resolve.hydration.success post_id=%s media_type=%s gallery_item_count=%s elapsed_ms=%s",
        item.id,
        item.media_type,
        len(item.gallery_items),
        int((monotonic() - started) * 1000),
    )
    return item


def _hydrate_sync(provider: RedditClientProvider, post_id: str) -> RedditMediaItem:
    reddit = provider.get_client()
    submission = reddit.submission(id=post_id)
    fetch = getattr(submission, "_fetch", None)
    if callable(fetch):
        fetch()
    item = normalize_submission(submission)
    if not item:
        raise MediaResolutionError("hydration_returned_no_media", debug_context={"post_id": post_id})
    return item
