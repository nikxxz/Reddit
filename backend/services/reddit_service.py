from __future__ import annotations

from typing import Any

import praw
from praw.exceptions import PRAWException
from prawcore import exceptions as prawcore_exceptions

from backend.config import ConfigurationError, settings, validate_reddit_settings_values


class RedditService:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.client_id = client_id or settings.reddit_client_id
        self.client_secret = client_secret or settings.reddit_client_secret
        self.user_agent = user_agent or settings.reddit_user_agent

    def _build_client(self) -> praw.Reddit:
        validate_reddit_settings_values(
            self.client_id,
            self.client_secret,
            self.user_agent,
        )
        reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
            check_for_updates=False,
        )
        try:
            reddit.read_only = True
        except Exception:
            pass
        return reddit

    def _sanitize_error(self, error: Exception) -> str:
        message = str(error).strip() or error.__class__.__name__
        if self.client_secret:
            message = message.replace(self.client_secret, "[REDACTED]")
        return message

    def test_connection(self) -> dict[str, Any]:
        try:
            reddit = self._build_client()
            read_only = bool(getattr(reddit, "read_only", False))

            if not read_only:
                try:
                    reddit.read_only = True
                except Exception:
                    pass
                read_only = bool(getattr(reddit, "read_only", False))

            list(reddit.subreddit("python").new(limit=1))

            return {
                "connected": True,
                "read_only": read_only,
                "authenticated_user": None,
            }
        except ConfigurationError as exc:
            return {
                "connected": False,
                "read_only": True,
                "authenticated_user": None,
                "error": str(exc),
            }
        except (
            PRAWException,
            prawcore_exceptions.PrawcoreException,
            ConnectionError,
            TimeoutError,
            ValueError,
            RuntimeError,
        ) as exc:
            return {
                "connected": False,
                "read_only": True,
                "authenticated_user": None,
                "error": f"Reddit API connection failed: {self._sanitize_error(exc)}",
            }
