from backend.config import ConfigurationError


class RedditConnectionError(RuntimeError):
    pass


class RedditSearchError(RuntimeError):
    pass


class InvalidSubredditError(RedditSearchError):
    pass


class MediaNormalizationError(RuntimeError):
    pass


__all__ = [
    "ConfigurationError",
    "InvalidSubredditError",
    "MediaNormalizationError",
    "RedditConnectionError",
    "RedditSearchError",
]
