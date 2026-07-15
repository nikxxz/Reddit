from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from praw.exceptions import PRAWException
from prawcore import exceptions as prawcore_exceptions

from backend.api.errors import InvalidSubredditError, RedditSearchError
from backend.models.reddit import RedditMediaItem, RedditSearchResponse
from backend.services.reddit.client import RedditClientProvider
from backend.services.reddit.media_detector import get_value
from backend.services.reddit.normalizer import normalize_submission
from backend.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class SearchCollectionStats:
    inspected: int = 0
    accepted: int = 0
    skipped_unsupported: int = 0
    skipped_missing_id: int = 0
    skipped_duplicate: int = 0
    skipped_media_filter: int = 0


class RedditSearchService:
    def __init__(self, client_provider: RedditClientProvider | None = None) -> None:
        self.client_provider = client_provider or RedditClientProvider()

    def search_media(
        self,
        query: str,
        subreddit: str | None = None,
        media_type: str = "all",
        sort: str = "relevance",
        time_filter: str = "all",
        limit: int = 24,
        after: str | None = None,
    ) -> RedditSearchResponse:
        query = query.strip()
        subreddit = subreddit.strip() if subreddit else None
        if subreddit and subreddit.startswith("r/"):
            subreddit = subreddit[2:]

        started_at = perf_counter()
        inspect_limit = min(max(limit * 3, 60), 100)
        logger.info(
            "reddit.search.start query=%r subreddit=%s media_type=%s sort=%s "
            "time_filter=%s limit=%s inspect_limit=%s after=%s",
            query,
            subreddit or "all",
            media_type,
            sort,
            time_filter,
            limit,
            inspect_limit,
            bool(after),
        )

        try:
            listing = self._search_listing(
                query=query,
                subreddit=subreddit,
                sort=sort,
                time_filter=time_filter,
                limit=limit,
                after=after,
            )
            items, next_after, stats = self._collect_media_items(
                listing, media_type, limit
            )
            elapsed_ms = round((perf_counter() - started_at) * 1000)
            logger.info(
                "reddit.search.success query=%r subreddit=%s inspected=%s accepted=%s "
                "skipped_unsupported=%s skipped_missing_id=%s skipped_duplicate=%s "
                "skipped_media_filter=%s next_after=%s elapsed_ms=%s",
                query,
                subreddit or "all",
                stats.inspected,
                stats.accepted,
                stats.skipped_unsupported,
                stats.skipped_missing_id,
                stats.skipped_duplicate,
                stats.skipped_media_filter,
                bool(next_after),
                elapsed_ms,
            )
            return RedditSearchResponse(
                query=query,
                subreddit=subreddit,
                media_type=media_type,
                sort=sort,
                time_filter=time_filter,
                count=len(items),
                next_after=next_after,
                items=items,
            )
        except (
            prawcore_exceptions.Redirect,
            prawcore_exceptions.NotFound,
            prawcore_exceptions.Forbidden,
        ):
            elapsed_ms = round((perf_counter() - started_at) * 1000)
            logger.warning(
                "reddit.search.invalid_subreddit query=%r subreddit=%s elapsed_ms=%s",
                query,
                subreddit or "all",
                elapsed_ms,
            )
            raise InvalidSubredditError("Invalid subreddit") from None
        except (
            PRAWException,
            prawcore_exceptions.PrawcoreException,
            ConnectionError,
            TimeoutError,
            ValueError,
            RuntimeError,
        ) as exc:
            elapsed_ms = round((perf_counter() - started_at) * 1000)
            message = self.client_provider.sanitize_error(exc)
            logger.warning(
                "reddit.search.failure query=%r subreddit=%s elapsed_ms=%s "
                "error_type=%s error=%s",
                query,
                subreddit or "all",
                elapsed_ms,
                exc.__class__.__name__,
                message,
            )
            raise RedditSearchError(message) from exc

    def _search_listing(
        self,
        query: str,
        subreddit: str | None,
        sort: str,
        time_filter: str,
        limit: int,
        after: str | None,
    ) -> Any:
        inspect_limit = min(max(limit * 3, 60), 100)
        reddit = self.client_provider.get_client()
        target = reddit.subreddit(subreddit or "all")
        search_kwargs: dict[str, Any] = {
            "sort": sort,
            "time_filter": time_filter,
            "limit": inspect_limit,
        }
        if after:
            search_kwargs["params"] = {"after": after}
        logger.info(
            "reddit.search.praw_request subreddit=%s sort=%s time_filter=%s "
            "inspect_limit=%s after=%s",
            subreddit or "all",
            sort,
            time_filter,
            inspect_limit,
            bool(after),
        )
        return target.search(query, **search_kwargs)

    def _collect_media_items(
        self,
        listing: Any,
        media_type: str,
        limit: int,
    ) -> tuple[list[RedditMediaItem], str | None, SearchCollectionStats]:
        items: list[RedditMediaItem] = []
        seen_ids: set[str] = set()
        last_fullname: str | None = None
        stats = SearchCollectionStats()

        try:
            for submission in listing:
                stats.inspected += 1
                last_fullname = get_value(submission, "fullname", None) or (
                    f"t3_{get_value(submission, 'id')}"
                    if get_value(submission, "id")
                    else None
                )
                item = normalize_submission(submission)
                if not item:
                    stats.skipped_unsupported += 1
                    continue
                if not item.id:
                    stats.skipped_missing_id += 1
                    continue
                if item.id in seen_ids:
                    stats.skipped_duplicate += 1
                    continue
                if media_type != "all" and item.media_type != media_type:
                    stats.skipped_media_filter += 1
                    continue
                seen_ids.add(item.id)
                items.append(item)
                stats.accepted += 1
                if len(items) >= limit:
                    break
        except Exception as exc:
            logger.warning(
                "reddit.search.collect_failure inspected=%s accepted=%s "
                "skipped_unsupported=%s skipped_missing_id=%s skipped_duplicate=%s "
                "skipped_media_filter=%s error_type=%s error=%s",
                stats.inspected,
                stats.accepted,
                stats.skipped_unsupported,
                stats.skipped_missing_id,
                stats.skipped_duplicate,
                stats.skipped_media_filter,
                exc.__class__.__name__,
                self.client_provider.sanitize_error(exc),
            )
            raise

        next_after = None
        if len(items) >= limit:
            next_after = get_value(listing, "params", {}).get("after") or last_fullname
        return items, next_after, stats
