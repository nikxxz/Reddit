from __future__ import annotations

import secrets
from dataclasses import dataclass
from time import time
from typing import Any

import praw

from backend.config import settings, validate_reddit_settings_values
from backend.services.reddit.session import RedditSessionData, RedditSessionStore
from backend.utils.logging import get_logger


logger = get_logger(__name__)
OAUTH_SCOPES = ["identity", "read"]
STATE_TTL_SECONDS = 600


@dataclass
class AuthStatus:
    connected: bool
    username: str | None = None
    read_only: bool | None = None


class RedditOAuthManager:
    def __init__(self, store: RedditSessionStore | None = None) -> None:
        self.store = store or RedditSessionStore()
        self._authenticated_client: praw.Reddit | None = None
        self._username: str | None = None
        self._states: dict[str, float] = {}

    @property
    def username(self) -> str | None:
        return self._username

    def create_authorization_url(self) -> str:
        logger.info("reddit.oauth.login.start")
        state = secrets.token_urlsafe(32)
        self._states[state] = time() + STATE_TTL_SECONDS
        self._prune_states()
        reddit = self._new_reddit_client()
        url = reddit.auth.url(scopes=OAUTH_SCOPES, state=state, duration="permanent")
        logger.info("reddit.oauth.redirect.created scopes=%s", ",".join(OAUTH_SCOPES))
        return url

    def handle_callback(self, code: str | None, state: str | None, error: str | None = None) -> AuthStatus:
        logger.info("reddit.oauth.callback.received has_code=%s has_error=%s", bool(code), bool(error))
        if error:
            raise ValueError("Authorization cancelled.")
        if not code:
            raise ValueError("Unable to connect Reddit account.")
        if not state or not self._consume_state(state):
            logger.warning("reddit.oauth.callback.invalid_state")
            raise ValueError("Invalid state.")

        logger.info("reddit.oauth.token.exchange.start")
        reddit = self._new_reddit_client()
        refresh_token = reddit.auth.authorize(code)
        logger.info("reddit.oauth.token.exchange.success")
        username = self._load_username(reddit)
        self.store.save(RedditSessionData(refresh_token=refresh_token, username=username))
        self._authenticated_client = self._new_reddit_client(refresh_token=refresh_token)
        self._username = username
        logger.info("reddit.oauth.username.loaded username=%s", username)
        return self.status()

    def restore_session(self) -> AuthStatus:
        logger.info("reddit.oauth.restore.start")
        session = self.store.load()
        if not session:
            logger.info("reddit.oauth.restore.failed reason=no_session")
            return self.status()
        try:
            reddit = self._new_reddit_client(refresh_token=session.refresh_token)
            username = self._load_username(reddit)
            self._authenticated_client = reddit
            self._username = username
            if username != session.username:
                self.store.save(RedditSessionData(refresh_token=session.refresh_token, username=username))
            logger.info("reddit.oauth.restore.success username=%s", username)
            return self.status()
        except Exception as exc:
            self._authenticated_client = None
            self._username = None
            self.store.delete()
            logger.warning("reddit.oauth.restore.failed error_type=%s", exc.__class__.__name__)
            return self.status()

    def logout(self) -> None:
        logger.info("reddit.oauth.logout.start username=%s", self._username)
        self._authenticated_client = None
        self._username = None
        self.store.delete()
        logger.info("reddit.oauth.logout.success")

    def status(self) -> AuthStatus:
        if self._authenticated_client is not None:
            logger.info("reddit.oauth.status.connected username=%s", self._username)
            return AuthStatus(connected=True, username=self._username, read_only=False)
        logger.info("reddit.oauth.status.disconnected")
        return AuthStatus(connected=False)

    def get_authenticated_client(self) -> praw.Reddit | None:
        return self._authenticated_client

    def client_context(self) -> tuple[str, str | None]:
        if self._authenticated_client is not None:
            return "authenticated", self._username
        return "anonymous", None

    def _new_reddit_client(self, refresh_token: str | None = None) -> praw.Reddit:
        validate_reddit_settings_values(
            settings.reddit_client_id,
            settings.reddit_client_secret,
            settings.reddit_user_agent,
        )
        return praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
            redirect_uri=settings.reddit_redirect_uri,
            refresh_token=refresh_token,
            check_for_updates=False,
            requestor_kwargs={
                "timeout": (
                    settings.reddit_connect_timeout,
                    settings.reddit_read_timeout,
                )
            },
        )

    def _load_username(self, reddit: praw.Reddit) -> str:
        user: Any = reddit.user.me()
        username = str(user) if user else ""
        if not username:
            raise ValueError("Unable to load Reddit username.")
        return username

    def _consume_state(self, state: str) -> bool:
        self._prune_states()
        expires_at = self._states.pop(state, None)
        return bool(expires_at and expires_at >= time())

    def _prune_states(self) -> None:
        now = time()
        expired = [state for state, expires_at in self._states.items() if expires_at < now]
        for state in expired:
            self._states.pop(state, None)


reddit_oauth_manager = RedditOAuthManager()
