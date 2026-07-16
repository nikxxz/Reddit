from backend.config import ConfigurationError


class RedditConnectionError(RuntimeError):
    pass


class RedditSearchError(RuntimeError):
    pass


class InvalidSubredditError(RedditSearchError):
    pass


class RedditEntityNotFoundError(RedditSearchError):
    pass


class RedditUserSuspendedError(RedditEntityNotFoundError):
    pass


class PrivateSubredditError(RedditSearchError):
    pass


class MediaNormalizationError(RuntimeError):
    pass


__all__ = [
    "ConfigurationError",
    "InvalidSubredditError",
    "MediaNormalizationError",
    "PrivateSubredditError",
    "RedditConnectionError",
    "RedditEntityNotFoundError",
    "RedditSearchError",
    "RedditUserSuspendedError",
]
