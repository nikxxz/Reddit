from __future__ import annotations

import praw

from backend.config import settings, validate_reddit_settings_values


class RedditClientProvider:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.client_id = client_id or settings.reddit_client_id
        self.client_secret = client_secret or settings.reddit_client_secret
        self.user_agent = user_agent or settings.reddit_user_agent
        self._client: praw.Reddit | None = None

    def get_client(self) -> praw.Reddit:
        if self._client is None:
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
            self._client = reddit
        return self._client

    def sanitize_error(self, error: Exception) -> str:
        message = str(error).strip() or error.__class__.__name__
        if self.client_secret:
            message = message.replace(self.client_secret, "[REDACTED]")
        return message
