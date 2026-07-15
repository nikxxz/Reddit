from backend.api.errors import InvalidSubredditError, RedditSearchError
from backend.services.reddit import (
    ALLOWED_MEDIA_TYPES,
    ALLOWED_SORTS,
    ALLOWED_TIME_FILTERS,
    SUBREDDIT_NAME_RE,
    RedditConnectionService,
    RedditSearchService,
    detect_media_type,
    normalize_submission,
)
from backend.services.reddit.client import RedditClientProvider


class RedditService:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        client_provider = RedditClientProvider(client_id, client_secret, user_agent)
        self.connection = RedditConnectionService(client_provider)
        self.search = RedditSearchService(client_provider)

    def test_connection(self):
        result = self.connection.test_connection()
        data = result.dict() if hasattr(result, "dict") else result.model_dump()
        return {key: value for key, value in data.items() if value is not None}

    def search_media(self, *args, **kwargs):
        return self.search.search_media(*args, **kwargs)


__all__ = [
    "ALLOWED_MEDIA_TYPES",
    "ALLOWED_SORTS",
    "ALLOWED_TIME_FILTERS",
    "SUBREDDIT_NAME_RE",
    "InvalidSubredditError",
    "RedditSearchError",
    "RedditService",
    "detect_media_type",
    "normalize_submission",
]
