from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any

from praw.exceptions import PRAWException
from prawcore import exceptions as prawcore_exceptions

from backend.api.errors import (
    PrivateSubredditError,
    RedditEntityNotFoundError,
    RedditSearchError,
    RedditUserSuspendedError,
)
from backend.models.reddit import (
    RedditEntityMediaResponse,
    RedditEntitySearchResponse,
    RedditMediaEntity,
    RedditSubredditEntity,
    RedditUserEntity,
)
from backend.services.reddit.client import RedditClientProvider
from backend.services.reddit.media_detector import get_value
from backend.services.reddit.search import RedditSearchService
from backend.utils.logging import get_logger
from backend.utils.urls import clean_url


logger = get_logger(__name__)
ENTITY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{2,32}$")
SUBREDDIT_SORTS = {"hot", "new", "top", "rising"}
USER_SORTS = {"new", "top"}
MEDIA_TYPES = {"all", "image", "video", "gif", "gallery"}
TIME_FILTERS = {"hour", "day", "week", "month", "year", "all"}


@dataclass
class CacheEntry:
    expires_at: float
    value: object


class TtlCache:
    def __init__(self, ttl_seconds: int, max_size: int = 128) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._values: OrderedDict[tuple[object, ...], CacheEntry] = OrderedDict()
        self._lock = Lock()

    def get(self, key: tuple[object, ...]) -> object | None:
        now = monotonic()
        with self._lock:
            entry = self._values.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._values.pop(key, None)
                return None
            self._values.move_to_end(key)
            return entry.value

    def set(self, key: tuple[object, ...], value: object) -> None:
        with self._lock:
            self._values[key] = CacheEntry(monotonic() + self.ttl_seconds, value)
            self._values.move_to_end(key)
            while len(self._values) > self.max_size:
                self._values.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


class RedditEntityService:
    def __init__(self, client_provider: RedditClientProvider | None = None) -> None:
        self.client_provider = client_provider or RedditClientProvider()
        self.search_service = RedditSearchService(self.client_provider)
        self.search_cache = TtlCache(ttl_seconds=180, max_size=128)
        self.entity_cache = TtlCache(ttl_seconds=600, max_size=256)

    def search_entities(self, query: str, limit: int = 20) -> RedditEntitySearchResponse:
        clean_query = normalize_entity_query(query)
        if len(clean_query) < 2:
            raise ValueError("Search must be at least 2 characters.")
        limit = max(1, min(limit, 20))
        cache_key = ("search", clean_query.lower(), limit)
        cached = self.search_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        reddit = self.client_provider.get_client()
        try:
            subreddits = [
                normalize_subreddit_entity(item)
                for item in list(reddit.subreddits.search(clean_query, limit=limit))[:limit]
            ]
            users = self._search_users(reddit, clean_query, limit)
            response = RedditEntitySearchResponse(
                query=clean_query,
                subreddits=[item for item in subreddits if item is not None],
                users=users,
            )
            self.search_cache.set(cache_key, response)
            return response
        except (PRAWException, prawcore_exceptions.PrawcoreException, ConnectionError, TimeoutError, RuntimeError) as exc:
            logger.warning(
                "reddit.entities.search.failure query=%r error_type=%s error=%s",
                clean_query,
                exc.__class__.__name__,
                self.client_provider.sanitize_error(exc),
            )
            raise RedditSearchError("Reddit entity search is temporarily unavailable.") from exc

    def browse_media(
        self,
        *,
        entity_type: str,
        entity_name: str,
        sort: str = "hot",
        time_filter: str = "all",
        media_type: str = "all",
        include_nsfw: bool = False,
        cursor: str | None = None,
        limit: int = 24,
    ) -> RedditEntityMediaResponse:
        clean_type = entity_type.strip().lower()
        clean_name = normalize_entity_name(entity_name)
        if clean_type not in {"subreddit", "user"}:
            raise ValueError("Invalid entity type.")
        if media_type not in MEDIA_TYPES:
            raise ValueError("Invalid media_type.")
        if time_filter not in TIME_FILTERS:
            raise ValueError("Invalid time_filter.")
        allowed_sorts = SUBREDDIT_SORTS if clean_type == "subreddit" else USER_SORTS
        if sort not in allowed_sorts:
            raise ValueError("Invalid sort for this entity.")
        limit = max(1, min(limit, 50))

        try:
            entity, listing = self._listing_for_entity(
                clean_type,
                clean_name,
                sort,
                time_filter,
                cursor,
                min(limit * 3, 100),
            )
            if entity.over_18 and not include_nsfw:
                return RedditEntityMediaResponse(
                    entity=entity,
                    items=[],
                    count=0,
                    next_cursor=None,
                    has_more=False,
                    media_type=media_type,
                    sort=sort,
                    time_filter=time_filter,
                    message="NSFW media is hidden for this community.",
                )
            items, next_cursor, stats = self.search_service._collect_media_items(
                listing,
                media_type,
                limit,
                include_nsfw,
            )
            return RedditEntityMediaResponse(
                entity=entity,
                items=items,
                count=len(items),
                next_cursor=next_cursor,
                has_more=bool(next_cursor),
                media_type=media_type,
                sort=sort,
                time_filter=time_filter,
                message=self.search_service._result_message(stats),
            )
        except PrivateSubredditError:
            raise
        except RedditEntityNotFoundError:
            raise
        except (
            prawcore_exceptions.Redirect,
            prawcore_exceptions.NotFound,
        ) as exc:
            if clean_type == "subreddit":
                raise RedditEntityNotFoundError("This Reddit community or user does not exist or is unavailable.") from exc
            raise RedditEntityNotFoundError("This Reddit community or user does not exist or is unavailable.") from exc
        except prawcore_exceptions.Forbidden as exc:
            if clean_type == "subreddit":
                raise PrivateSubredditError("This subreddit is private.") from exc
            raise RedditEntityNotFoundError("This Reddit community or user does not exist or is unavailable.") from exc
        except (PRAWException, prawcore_exceptions.PrawcoreException, ConnectionError, TimeoutError, RuntimeError) as exc:
            logger.warning(
                "reddit.entities.media.failure entity_type=%s entity_name=%s error_type=%s error=%s",
                clean_type,
                clean_name,
                exc.__class__.__name__,
                self.client_provider.sanitize_error(exc),
            )
            raise RedditSearchError("Reddit media browsing is temporarily unavailable.") from exc

    def _search_users(self, reddit: Any, query: str, limit: int) -> list[RedditUserEntity]:
        users: list[RedditUserEntity] = []
        search = getattr(getattr(reddit, "redditors", None), "search", None)
        if callable(search):
            users.extend(
                item
                for item in (normalize_user_entity(user) for user in list(search(query, limit=limit))[:limit])
                if item is not None
            )
        if len(users) < limit:
            exact = self._exact_user(reddit, query)
            if exact and all(user.username.lower() != exact.username.lower() for user in users):
                users.append(exact)
        return users[:limit]

    def _exact_user(self, reddit: Any, username: str) -> RedditUserEntity | None:
        try:
            redditor = reddit.redditor(username)
            _ = get_value(redditor, "id")
            normalized = normalize_user_entity(redditor)
            if normalized and normalized.suspended:
                return None
            return normalized
        except (
            prawcore_exceptions.NotFound,
            prawcore_exceptions.Redirect,
            prawcore_exceptions.Forbidden,
        ):
            return None

    def _listing_for_entity(
        self,
        entity_type: str,
        entity_name: str,
        sort: str,
        time_filter: str,
        cursor: str | None,
        limit: int,
    ) -> tuple[RedditMediaEntity, Any]:
        reddit = self.client_provider.get_client()
        params = {"after": cursor} if cursor else None
        kwargs: dict[str, Any] = {"limit": limit}
        if params:
            kwargs["params"] = params
        if entity_type == "subreddit":
            target = reddit.subreddit(entity_name)
            entity = self._subreddit_media_entity(target)
            listing = _call_listing(
                target,
                sort,
                time_filter,
                kwargs,
            )
            return entity, listing
        target = reddit.redditor(entity_name)
        entity = self._user_media_entity(target)
        submissions = target.submissions
        listing = _call_listing(submissions, sort, time_filter, kwargs)
        return entity, listing

    def _subreddit_media_entity(self, subreddit: Any) -> RedditMediaEntity:
        cache_key = ("subreddit", str(get_value(subreddit, "display_name") or subreddit).lower())
        cached = self.entity_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        normalized = normalize_subreddit_entity(subreddit)
        if normalized is None:
            raise RedditEntityNotFoundError("This Reddit community or user does not exist or is unavailable.")
        if normalized.private:
            raise PrivateSubredditError("This subreddit is private.")
        entity = RedditMediaEntity(
            type="subreddit",
            name=normalized.name,
            title=normalized.title,
            description=normalized.description,
            icon_url=normalized.icon_url,
            subscribers=normalized.subscribers,
            over_18=normalized.over_18,
            restricted=normalized.restricted,
            private=normalized.private,
        )
        self.entity_cache.set(cache_key, entity)
        return entity

    def _user_media_entity(self, user: Any) -> RedditMediaEntity:
        cache_key = ("user", str(get_value(user, "name") or user).lower())
        cached = self.entity_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        normalized = normalize_user_entity(user)
        if normalized is None or normalized.suspended:
            raise RedditUserSuspendedError("This Reddit user is suspended or unavailable.")
        entity = RedditMediaEntity(
            type="user",
            name=normalized.username,
            title=normalized.display_name,
            avatar_url=normalized.avatar_url,
            link_karma=normalized.link_karma,
            comment_karma=normalized.comment_karma,
            over_18=normalized.over_18,
            suspended=normalized.suspended,
        )
        self.entity_cache.set(cache_key, entity)
        return entity


def normalize_entity_query(value: str) -> str:
    text = value.strip()
    text = re.sub(r"^/?[ru]/", "", text, flags=re.IGNORECASE)
    return text.strip()


def normalize_entity_name(value: str) -> str:
    text = normalize_entity_query(value)
    if not ENTITY_NAME_PATTERN.match(text):
        raise ValueError("Invalid entity name.")
    return text


def normalize_subreddit_entity(item: Any) -> RedditSubredditEntity | None:
    name = get_value(item, "display_name") or get_value(item, "display_name_prefixed")
    if not name:
        return None
    name = str(name).removeprefix("r/")
    icon = clean_url(
        get_value(item, "community_icon")
        or get_value(item, "icon_img")
        or get_value(item, "header_img")
    )
    return RedditSubredditEntity(
        name=name,
        display_name=name,
        title=get_value(item, "title") or get_value(item, "public_description"),
        description=get_value(item, "public_description") or get_value(item, "description"),
        icon_url=icon,
        subscribers=_safe_int(get_value(item, "subscribers")),
        over_18=bool(get_value(item, "over18", False) or get_value(item, "over_18", False)),
        restricted=str(get_value(item, "subreddit_type") or "").lower() == "restricted",
        private=str(get_value(item, "subreddit_type") or "").lower() == "private",
    )


def normalize_user_entity(item: Any) -> RedditUserEntity | None:
    username = get_value(item, "name")
    if not username:
        return None
    user_subreddit = get_value(item, "subreddit") or {}
    icon = clean_url(get_value(item, "icon_img") or get_value(user_subreddit, "icon_img"))
    return RedditUserEntity(
        username=str(username),
        display_name=get_value(user_subreddit, "display_name") or get_value(item, "name"),
        avatar_url=icon,
        link_karma=_safe_int(get_value(item, "link_karma")),
        comment_karma=_safe_int(get_value(item, "comment_karma")),
        over_18=bool(get_value(user_subreddit, "over_18", False)),
        suspended=bool(get_value(item, "is_suspended", False)),
    )


def _call_listing(target: Any, sort: str, time_filter: str, kwargs: dict[str, Any]) -> Any:
    if sort == "new":
        return target.new(**kwargs)
    if sort == "top":
        return target.top(time_filter=time_filter, **kwargs)
    if sort == "rising":
        return target.rising(**kwargs)
    return target.hot(**kwargs)


def _safe_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
