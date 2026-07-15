from __future__ import annotations

from time import perf_counter

from praw.exceptions import PRAWException
from prawcore import exceptions as prawcore_exceptions

from backend.api.errors import ConfigurationError
from backend.models.reddit import RedditConnectionStatus
from backend.services.reddit.client import RedditClientProvider
from backend.utils.logging import get_logger


logger = get_logger(__name__)


class RedditConnectionService:
    def __init__(self, client_provider: RedditClientProvider | None = None) -> None:
        self.client_provider = client_provider or RedditClientProvider()

    def test_connection(self) -> RedditConnectionStatus:
        started_at = perf_counter()
        logger.info("reddit.connection.start subreddit=python limit=1")
        try:
            reddit = self.client_provider.get_client()
            client_type, username = self.client_provider.client_context()
            read_only = client_type != "authenticated"

            list(reddit.subreddit("python").new(limit=1))
            elapsed_ms = round((perf_counter() - started_at) * 1000)
            logger.info(
                "reddit.connection.success read_only=%s client_type=%s username=%s elapsed_ms=%s",
                read_only,
                client_type,
                username,
                elapsed_ms,
            )
            return RedditConnectionStatus(
                connected=True,
                read_only=read_only,
                authenticated_user=username,
            )
        except ConfigurationError as exc:
            elapsed_ms = round((perf_counter() - started_at) * 1000)
            logger.warning(
                "reddit.connection.configuration_error elapsed_ms=%s error=%s",
                elapsed_ms,
                exc,
            )
            return RedditConnectionStatus(
                connected=False,
                read_only=True,
                authenticated_user=None,
                error=str(exc),
            )
        except (
            PRAWException,
            prawcore_exceptions.PrawcoreException,
            ConnectionError,
            TimeoutError,
            ValueError,
            RuntimeError,
        ) as exc:
            message = self.client_provider.sanitize_error(exc)
            elapsed_ms = round((perf_counter() - started_at) * 1000)
            logger.warning(
                "reddit.connection.failure elapsed_ms=%s error_type=%s error=%s",
                elapsed_ms,
                exc.__class__.__name__,
                message,
            )
            return RedditConnectionStatus(
                connected=False,
                read_only=True,
                authenticated_user=None,
                error=f"Reddit API connection failed: {message}",
            )
