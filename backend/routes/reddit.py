from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import (
    get_reddit_connection_service,
    get_reddit_search_service,
)
from backend.api.errors import InvalidSubredditError, RedditSearchError
from backend.api.responses import GENERIC_REDDIT_SEARCH_ERROR
from backend.models.reddit import RedditSearchResponse
from backend.services.reddit import (
    ALLOWED_MEDIA_TYPES,
    ALLOWED_SORTS,
    ALLOWED_TIME_FILTERS,
    SUBREDDIT_NAME_RE,
    RedditConnectionService,
    RedditSearchService,
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
                "authenticated_user": None,
            },
        }
    logger.warning("api.reddit.test.failure detail=%s", result.error)
    raise HTTPException(status_code=502, detail=result.error or "Reddit API connection failed")


@router.get("/reddit/search", response_model=RedditSearchResponse)
def search_reddit_media(
    q: str = Query(...),
    subreddit: str | None = Query(default=None),
    media_type: str = Query(default="all"),
    sort: str = Query(default="relevance"),
    time_filter: str = Query(default="all"),
    limit: int = Query(default=24),
    after: str | None = Query(default=None),
    service: RedditSearchService = Depends(get_reddit_search_service),
) -> RedditSearchResponse:
    query, clean_subreddit = validate_search_params(
        q, subreddit, media_type, sort, time_filter, limit
    )
    logger.info(
        "api.reddit.search.start query=%r subreddit=%s media_type=%s sort=%s "
        "time_filter=%s limit=%s after=%s",
        query,
        clean_subreddit or "all",
        media_type,
        sort,
        time_filter,
        limit,
        bool(after),
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
        raise HTTPException(status_code=400, detail="Invalid subreddit name.") from None
    except RedditSearchError:
        logger.warning(
            "api.reddit.search.failure query=%r subreddit=%s",
            query,
            clean_subreddit or "all",
        )
        raise HTTPException(status_code=502, detail=GENERIC_REDDIT_SEARCH_ERROR) from None


def validate_search_params(
    query: str,
    subreddit: str | None,
    media_type: str,
    sort: str,
    time_filter: str,
    limit: int,
) -> tuple[str, str | None]:
    clean_query = query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Search query is required.")

    clean_subreddit = subreddit.strip() if subreddit else None
    if clean_subreddit and clean_subreddit.startswith("r/"):
        clean_subreddit = clean_subreddit[2:]
    if clean_subreddit and not SUBREDDIT_NAME_RE.fullmatch(clean_subreddit):
        raise HTTPException(status_code=400, detail="Invalid subreddit name.")

    if media_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(status_code=400, detail="Invalid media_type.")
    if sort not in ALLOWED_SORTS:
        raise HTTPException(status_code=400, detail="Invalid sort.")
    if time_filter not in ALLOWED_TIME_FILTERS:
        raise HTTPException(status_code=400, detail="Invalid time_filter.")
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50.")
    return clean_query, clean_subreddit
