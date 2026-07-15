from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from time import perf_counter
from typing import Any

from praw.exceptions import PRAWException
from prawcore import exceptions as prawcore_exceptions

from backend.api.errors import InvalidSubredditError, RedditSearchError
from backend.config import settings
from backend.models.reddit import RedditMediaItem, RedditSearchResponse
from backend.services.reddit.client import RedditClientProvider
from backend.services.reddit.media_detector import get_value, normalize_subreddit_input
from backend.services.reddit.media_cache import normalized_media_cache
from backend.services.reddit.normalizer import normalize_submission
from backend.utils.urls import (
    is_direct_gif,
    is_direct_image,
    is_direct_video,
    is_gifv,
    is_known_external_media_url,
    is_reddit_video_url,
)
from backend.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class SearchCollectionStats:
    inspected: int = 0
    accepted: int = 0
    media_detected: int = 0
    skipped_text_only: int = 0
    skipped_missing_loaded_metadata: int = 0
    skipped_unsupported: int = 0
    skipped_missing_id: int = 0
    skipped_duplicate: int = 0
    skipped_media_filter: int = 0
    skipped_nsfw: int = 0


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
        include_nsfw: bool = False,
    ) -> RedditSearchResponse:
        query = query.strip()
        try:
            subreddit = normalize_subreddit_input(subreddit)
        except ValueError:
            raise InvalidSubredditError("Invalid subreddit") from None

        started_at = perf_counter()
        inspect_limit = min(limit * settings.search_fetch_multiplier, 100)
        mode = self._search_mode(query, subreddit)
        effective_sort = self._effective_sort(mode, sort)
        client_type, username = self.client_provider.client_context()
        logger.info(
            "reddit.search.start mode=%s query=%r subreddit=%s media_type=%s requested_sort=%s "
            "time_filter=%s limit=%s inspect_limit=%s after=%s include_nsfw=%s "
            "effective_sort=%s client_type=%s username=%s",
            mode,
            query,
            subreddit or "all",
            media_type,
            sort,
            time_filter,
            limit,
            inspect_limit,
            bool(after),
            include_nsfw,
            effective_sort,
            client_type,
            username,
        )

        try:
            listing = self._search_listing(
                query=query,
                subreddit=subreddit,
                sort=sort,
                time_filter=time_filter,
                limit=limit,
                after=after,
                syntax=settings.search_syntax,
                mode=mode,
                effective_sort=effective_sort,
            )
            items, next_after, stats = self._collect_media_items(
                listing, media_type, limit, include_nsfw
            )
            elapsed_ms = round((perf_counter() - started_at) * 1000)
            logger.info(
                "reddit.search.success mode=%s query=%r subreddit=%s raw_submissions_received=%s "
                "media_detected=%s skipped_text_only=%s skipped_missing_loaded_metadata=%s "
                "skipped_unsupported=%s skipped_missing_id=%s skipped_duplicate=%s "
                "skipped_media_filter=%s skipped_nsfw=%s returned_items=%s "
                "detail_hydration_requests=%s next_after=%s elapsed_ms=%s "
                "client_type=%s username=%s",
                mode,
                query,
                subreddit or "all",
                stats.inspected,
                stats.media_detected,
                stats.skipped_text_only,
                stats.skipped_missing_loaded_metadata,
                stats.skipped_unsupported,
                stats.skipped_missing_id,
                stats.skipped_duplicate,
                stats.skipped_media_filter,
                stats.skipped_nsfw,
                stats.accepted,
                0,
                bool(next_after),
                elapsed_ms,
                client_type,
                username,
            )
            return RedditSearchResponse(
                mode=mode,
                query=query,
                subreddit=subreddit,
                requested_sort=sort,
                effective_sort=effective_sort,
                media_type=media_type,
                sort=sort,
                time_filter=time_filter,
                count=len(items),
                next_after=next_after,
                message=self._result_message(stats),
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
        syntax: str | None = None,
        mode: str | None = None,
        effective_sort: str | None = None,
    ) -> Any:
        inspect_limit = min(limit * settings.search_fetch_multiplier, 100)
        search_syntax = syntax or settings.search_syntax
        mode = mode or self._search_mode(query, subreddit)
        effective_sort = effective_sort or self._effective_sort(mode, sort)
        reddit = self.client_provider.get_client()
        client_type, username = self.client_provider.client_context()
        target_name = subreddit if subreddit else "all"
        target = reddit.subreddit(target_name)
        scope = "subreddit" if subreddit else "all"
        if after:
            params = {"after": after}
        else:
            params = None
        logger.info(
            "reddit.search.praw_request mode=%s query=%r scope=%s subreddit=%s "
            "requested_sort=%s effective_sort=%s time_filter=%s syntax=%s "
            "fetch_limit=%s after=%s client_type=%s username=%s",
            mode,
            query,
            scope,
            target_name,
            sort,
            effective_sort,
            time_filter,
            search_syntax,
            inspect_limit,
            bool(after),
            client_type,
            username,
        )
        if query:
            search_kwargs: dict[str, Any] = {
                "sort": sort,
                "time_filter": time_filter,
                "syntax": search_syntax,
                "limit": inspect_limit,
            }
            if params:
                search_kwargs["params"] = params
            search_callable = lambda: target.search(query, **search_kwargs)
        else:
            search_callable = lambda: self._browse_listing(
                target, effective_sort, time_filter, inspect_limit, params
            )

        last_error: Exception | None = None
        for attempt in range(settings.max_api_retries + 1):
            try:
                return search_callable()
            except Exception as exc:
                if not self._is_retryable_error(exc) or attempt >= settings.max_api_retries:
                    raise
                last_error = exc
                delay = self._retry_delay(exc, attempt)
                logger.warning(
                    "reddit.search.retry attempt=%s delay_seconds=%s error_type=%s",
                    attempt + 1,
                    delay,
                    exc.__class__.__name__,
                )
                sleep(delay)
        if last_error:
            raise last_error
        return search_callable()

    def _browse_listing(
        self,
        target: Any,
        sort: str,
        time_filter: str,
        limit: int,
        params: dict[str, str] | None,
    ) -> Any:
        kwargs: dict[str, Any] = {"limit": limit}
        if params:
            kwargs["params"] = params
        if sort == "new":
            return target.new(**kwargs)
        if sort == "top":
            return target.top(time_filter=time_filter, **kwargs)
        return target.hot(**kwargs)

    def _search_mode(self, query: str, subreddit: str | None) -> str:
        if query and subreddit:
            return "subreddit_search"
        if query:
            return "global_search"
        return "subreddit_browse"

    def _effective_sort(self, mode: str, requested_sort: str) -> str:
        if mode != "subreddit_browse":
            return requested_sort
        if requested_sort == "top":
            return "top"
        if requested_sort in {"new", "comments"}:
            return "new"
        return "hot"

    def _collect_media_items(
        self,
        listing: Any,
        media_type: str,
        limit: int,
        include_nsfw: bool,
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
                    reason = self._skip_reason(submission)
                    if reason == "text_only":
                        stats.skipped_text_only += 1
                    elif reason == "missing_loaded_metadata":
                        stats.skipped_missing_loaded_metadata += 1
                    else:
                        stats.skipped_unsupported += 1
                    continue
                stats.media_detected += 1
                if item.is_nsfw and not include_nsfw:
                    stats.skipped_nsfw += 1
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
                normalized_media_cache.set(item)
                items.append(item)
                stats.accepted += 1
                if len(items) >= limit:
                    break
        except Exception as exc:
            logger.warning(
                "reddit.search.collect_failure inspected=%s accepted=%s "
                "media_detected=%s skipped_text_only=%s skipped_missing_loaded_metadata=%s "
                "skipped_unsupported=%s skipped_missing_id=%s skipped_duplicate=%s "
                "skipped_media_filter=%s skipped_nsfw=%s error_type=%s error=%s",
                stats.inspected,
                stats.accepted,
                stats.media_detected,
                stats.skipped_text_only,
                stats.skipped_missing_loaded_metadata,
                stats.skipped_unsupported,
                stats.skipped_missing_id,
                stats.skipped_duplicate,
                stats.skipped_media_filter,
                stats.skipped_nsfw,
                exc.__class__.__name__,
                self.client_provider.sanitize_error(exc),
            )
            raise

        next_after = None
        if len(items) >= limit:
            next_after = get_value(listing, "params", {}).get("after") or last_fullname
        return items, next_after, stats

    def debug_raw_search(
        self,
        query: str,
        subreddit: str | None = None,
        sort: str = "relevance",
        time_filter: str = "all",
        limit: int = 10,
        syntax: str | None = None,
    ) -> dict[str, Any]:
        query = query.strip()
        try:
            clean_subreddit = normalize_subreddit_input(subreddit)
        except ValueError:
            raise InvalidSubredditError("Invalid subreddit") from None
        listing = self._search_listing(
            query=query,
            subreddit=clean_subreddit,
            sort=sort,
            time_filter=time_filter,
            limit=limit,
            after=None,
            syntax=syntax or settings.search_syntax,
        )
        posts = []
        for index, submission in enumerate(listing):
            if index >= limit:
                break
            data = vars(submission)
            posts.append(
                {
                    "id": data.get("id"),
                    "title": data.get("title"),
                    "subreddit": str(get_value(data.get("subreddit"), "display_name", data.get("subreddit"))),
                    "url": data.get("url"),
                    "is_video": data.get("is_video"),
                    "is_gallery": data.get("is_gallery"),
                    "over_18": data.get("over_18"),
                    "loaded_keys": sorted(str(key) for key in data.keys()),
                }
            )
        return {
            "target_subreddit": clean_subreddit or "all",
            "query": query,
            "raw_count": len(posts),
            "posts": posts,
        }

    def _skip_reason(self, submission: Any) -> str:
        data = vars(submission)
        if data.get("is_poll") or data.get("poll_data"):
            return "unsupported"
        url = get_value(submission, "url")
        if (
            is_direct_image(url)
            or is_direct_gif(url)
            or is_gifv(url)
            or is_direct_video(url)
            or is_reddit_video_url(url)
            or is_known_external_media_url(url)
        ):
            return "missing_loaded_metadata"
        if data.get("is_video") or data.get("is_gallery"):
            return "missing_loaded_metadata"
        if url and "reddit.com/r/" in str(url) and "/comments/" in str(url):
            return "text_only"
        return "unsupported"

    def _result_message(self, stats: SearchCollectionStats) -> str | None:
        if stats.accepted:
            return None
        if stats.inspected == 0:
            return "No Reddit posts matched this query in the selected subreddit."
        if stats.media_detected and stats.skipped_nsfw == stats.media_detected:
            return "Matching media was found, but it is hidden by the NSFW filter."
        if stats.skipped_text_only or stats.skipped_unsupported or stats.skipped_missing_loaded_metadata:
            return "Matching posts were found, but none contained supported media."
        return "No matching media found."

    def _is_retryable_error(self, error: Exception) -> bool:
        status = getattr(getattr(error, "response", None), "status_code", None)
        if status in {429, 500, 502, 503, 504}:
            return True
        if status in {400, 401, 403, 404}:
            return False
        return isinstance(error, (TimeoutError, ConnectionError, prawcore_exceptions.RequestException))

    def _retry_delay(self, error: Exception, attempt: int) -> float:
        headers = getattr(getattr(error, "response", None), "headers", {}) or {}
        retry_after = headers.get("Retry-After") if hasattr(headers, "get") else None
        try:
            return min(float(retry_after), 30.0)
        except (TypeError, ValueError):
            return float(2**attempt)
