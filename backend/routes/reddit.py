from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import (
    get_reddit_connection_service,
    get_reddit_search_service,
)
from backend.api.errors import InvalidSubredditError, RedditSearchError
from backend.config import settings
from backend.models.reddit import RedditSearchResponse
from backend.services.reddit import (
    ALLOWED_MEDIA_TYPES,
    ALLOWED_SORTS,
    ALLOWED_TIME_FILTERS,
    RedditConnectionService,
    RedditSearchService,
    normalize_subreddit_input,
)
from backend.utils.logging import get_logger

router = APIRouter(tags=["reddit"])
logger = get_logger(__name__)


@router.get("/reddit/test")
def test_reddit_connection(
    service: RedditConnectionService = Depends(get_reddit_connection_service),
) -> dict[str, object]:
    logger.info("api.reddit.test.start")
    result = service.test_connection()
    if result.connected:
        logger.info("api.reddit.test.success read_only=%s", result.read_only)
        return {
            "status": "ok",
            "reddit": {
                "connected": True,
                "read_only": result.read_only,
                "authenticated_user": result.authenticated_user,
            },
        }
    logger.warning("api.reddit.test.failure detail=%s", result.error)
    raise HTTPException(status_code=502, detail=result.error or "Reddit API connection failed")


@router.get("/reddit/search", response_model=RedditSearchResponse)
def search_reddit_media(
    q: str = Query(default=""),
    subreddit: str | None = Query(default=None),
    media_type: str = Query(default="all"),
    sort: str = Query(default="relevance"),
    time_filter: str = Query(default="all"),
    limit: int = Query(default=24),
    after: str | None = Query(default=None),
    include_nsfw: bool = Query(default=False),
    service: RedditSearchService = Depends(get_reddit_search_service),
) -> RedditSearchResponse:
    query, clean_subreddit = validate_search_params(
        q, subreddit, media_type, sort, time_filter, limit
    )
    logger.info(
        "api.reddit.search.start query=%r subreddit=%s media_type=%s sort=%s "
        "time_filter=%s limit=%s after=%s include_nsfw=%s",
        query,
        clean_subreddit or "all",
        media_type,
        sort,
        time_filter,
        limit,
        bool(after),
        include_nsfw,
    )
    try:
        response = service.search_media(
            query=query,
            subreddit=clean_subreddit,
            media_type=media_type,
            sort=sort,
            time_filter=time_filter,
            limit=limit,
            after=after,
            include_nsfw=include_nsfw,
        )
        logger.info(
            "api.reddit.search.success query=%r count=%s next_after=%s",
            query,
            response.count,
            bool(response.next_after),
        )
        return response
    except InvalidSubredditError:
        logger.warning(
            "api.reddit.search.invalid_subreddit query=%r subreddit=%s",
            query,
            clean_subreddit or "all",
        )
        raise HTTPException(
            status_code=400,
            detail="That subreddit could not be found or is unavailable.",
        ) from None
    except RedditSearchError:
        logger.warning(
            "api.reddit.search.failure query=%r subreddit=%s",
            query,
            clean_subreddit or "all",
        )
        raise HTTPException(status_code=502, detail="Reddit search is temporarily unavailable.") from None


@router.get("/reddit/search/debug")
def debug_reddit_search(
    q: str = Query(default=""),
    subreddit: str | None = Query(default=None),
    sort: str = Query(default="relevance"),
    time_filter: str = Query(default="all"),
    limit: int = Query(default=10),
    syntax: str = Query(default="lucene"),
    service: RedditSearchService = Depends(get_reddit_search_service),
) -> dict[str, object]:
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found.")
    query, clean_subreddit = validate_search_params(
        q, subreddit, "all", sort, time_filter, limit
    )
    if syntax not in {"lucene", "plain", "cloudsearch"}:
        raise HTTPException(status_code=400, detail="Invalid syntax.")
    try:
        return service.debug_raw_search(
            query=query,
            subreddit=clean_subreddit,
            sort=sort,
            time_filter=time_filter,
            limit=limit,
            syntax=syntax,
        )
    except InvalidSubredditError:
        raise HTTPException(
            status_code=400,
            detail="That subreddit could not be found or is unavailable.",
        ) from None
    except RedditSearchError:
        raise HTTPException(status_code=502, detail="Reddit search is temporarily unavailable.") from None


def validate_search_params(
    query: str,
    subreddit: str | None,
    media_type: str,
    sort: str,
    time_filter: str,
    limit: int,
) -> tuple[str, str | None]:
    clean_query = query.strip()
    try:
        clean_subreddit = normalize_subreddit_input(subreddit)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="That subreddit could not be found or is unavailable.",
        ) from None
    if not clean_query and not clean_subreddit:
        raise HTTPException(status_code=400, detail="Search query or subreddit is required.")

    if media_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(status_code=400, detail="Invalid media_type.")
    if sort not in ALLOWED_SORTS:
        raise HTTPException(status_code=400, detail="Invalid sort.")
    if time_filter not in ALLOWED_TIME_FILTERS:
        raise HTTPException(status_code=400, detail="Invalid time_filter.")
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50.")
    return clean_query, clean_subreddit
