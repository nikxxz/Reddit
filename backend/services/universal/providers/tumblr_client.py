from __future__ import annotations

import asyncio
from time import monotonic
from urllib.parse import quote, urlparse

import httpx

from backend.config import settings
from backend.services.universal.providers.tumblr_models import (
    TumblrBlogInfo,
    TumblrBlogPostsResponse,
    TumblrRateLimitState,
    TumblrTaggedResponse,
)
from backend.utils.logging import get_logger


logger = get_logger(__name__)


class TumblrApiError(RuntimeError):
    def __init__(
        self,
        code: str,
        safe_message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


class TumblrClient:
    def __init__(
        self,
        *,
        consumer_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.consumer_key = consumer_key or settings.tumblr_consumer_key
        self.base_url = (base_url or settings.tumblr_api_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.tumblr_request_timeout_seconds
        self.max_retries = settings.tumblr_max_retries if max_retries is None else max_retries
        self.rate_limit = TumblrRateLimitState()

        parsed = urlparse(self.base_url)
        if parsed.scheme != "https":
            raise TumblrApiError("tumblr_invalid_configuration", "Tumblr API must use HTTPS.")
        if not self.consumer_key:
            raise TumblrApiError("tumblr_configuration_required", "Tumblr consumer key is required.")

    async def get_tagged_posts(
        self,
        tag: str,
        *,
        before: int | None = None,
        limit: int = 20,
    ) -> TumblrTaggedResponse:
        params: dict[str, object] = {"tag": tag, "limit": self._limit(limit)}
        if before is not None:
            params["before"] = before
        payload, headers = await self._request("GET", "/tagged", params=params)
        posts = _as_list(payload)
        next_before = _oldest_timestamp(posts)
        self._capture_rate_limit(headers)
        return TumblrTaggedResponse(posts=posts, next_before=next_before)

    async def get_blog_posts(
        self,
        blog_identifier: str,
        *,
        before: int | None = None,
        offset: int | None = None,
        limit: int = 20,
        tag: str | None = None,
    ) -> TumblrBlogPostsResponse:
        params: dict[str, object] = {"limit": self._limit(limit)}
        if before is not None:
            params["before"] = before
        if offset is not None:
            params["offset"] = offset
        if tag:
            params["tag"] = tag
        payload, headers = await self._request("GET", f"/blog/{quote(blog_identifier, safe='')}/posts", params=params)
        response = _as_dict(payload)
        posts = _as_list(response.get("posts"))
        total = _safe_int(response.get("total_posts"))
        next_offset = (offset or 0) + len(posts) if total is None or (offset or 0) + len(posts) < total else None
        self._capture_rate_limit(headers)
        return TumblrBlogPostsResponse(posts=posts, next_offset=next_offset, next_before=_oldest_timestamp(posts))

    async def get_blog_info(self, blog_identifier: str) -> TumblrBlogInfo:
        payload, headers = await self._request("GET", f"/blog/{quote(blog_identifier, safe='')}/info")
        response = _as_dict(payload)
        blog = _as_dict(response.get("blog"))
        self._capture_rate_limit(headers)
        name = str(blog.get("name") or blog_identifier)
        return TumblrBlogInfo(name=name, title=_safe_str(blog.get("title")), url=_safe_str(blog.get("url")))

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
    ) -> tuple[object, httpx.Headers]:
        started = monotonic()
        safe_params = dict(params or {})
        safe_params["api_key"] = self.consumer_key
        url = f"{self.base_url}{path}"
        timeout = httpx.Timeout(self.timeout_seconds)

        for attempt in range(self.max_retries + 1):
            try:
                logger.info("tumblr.client.request.started method=%s path=%s attempt=%s", method, path, attempt + 1)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(method, url, params=safe_params)
                if response.status_code == 429:
                    retry_after = _retry_after(response.headers)
                    self.rate_limit = TumblrRateLimitState(True, retry_after)
                    logger.warning("tumblr.client.rate_limited status_code=429 retry_after_seconds=%s", retry_after)
                    raise TumblrApiError(
                        "tumblr_rate_limited",
                        "Tumblr temporarily limited further searches.",
                        status_code=429,
                        retry_after_seconds=retry_after,
                    )
                if response.status_code in {500, 502, 503, 504} and attempt < self.max_retries:
                    await asyncio.sleep(_backoff(attempt))
                    continue
                if response.status_code >= 400:
                    raise self._http_error(response)
                data = response.json()
                payload = self._response_payload(data, response.status_code)
                logger.info(
                    "tumblr.client.request.completed path=%s status_code=%s elapsed_ms=%s",
                    path,
                    response.status_code,
                    int((monotonic() - started) * 1000),
                )
                return payload, response.headers
            except TumblrApiError:
                raise
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError):
                if attempt >= self.max_retries:
                    raise TumblrApiError("tumblr_network_error", "Tumblr could not be reached.")
                await asyncio.sleep(_backoff(attempt))
            except asyncio.CancelledError:
                raise
            except ValueError as exc:
                raise TumblrApiError("tumblr_malformed_response", "Tumblr returned an invalid response.") from exc

        raise TumblrApiError("tumblr_network_error", "Tumblr could not be reached.")

    def _response_payload(self, data: object, http_status: int) -> object:
        envelope = _as_dict(data)
        meta = _as_dict(envelope.get("meta"))
        status = _safe_int(meta.get("status")) or http_status
        if status >= 400:
            raise TumblrApiError(_code_for_status(status), _message_for_status(status), status_code=status)
        if "response" not in envelope:
            raise TumblrApiError("tumblr_malformed_response", "Tumblr returned an invalid response.")
        return envelope["response"]

    def _http_error(self, response: httpx.Response) -> TumblrApiError:
        return TumblrApiError(_code_for_status(response.status_code), _message_for_status(response.status_code), status_code=response.status_code)

    def _capture_rate_limit(self, headers: httpx.Headers) -> None:
        retry_after = _retry_after(headers)
        self.rate_limit = TumblrRateLimitState(False, retry_after)

    def _limit(self, value: int) -> int:
        return max(1, min(int(value), settings.tumblr_max_limit))


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _safe_str(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value else None


def _safe_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _oldest_timestamp(posts: list[dict[str, object]]) -> int | None:
    timestamps = [_safe_int(post.get("timestamp")) for post in posts]
    timestamps = [timestamp for timestamp in timestamps if timestamp is not None]
    return min(timestamps) if timestamps else None


def _retry_after(headers: httpx.Headers) -> int | None:
    raw = headers.get("retry-after") or headers.get("x-ratelimit-reset")
    try:
        value = int(float(raw)) if raw is not None else None
    except (TypeError, ValueError):
        return None
    return value if value and value > 0 else None


def _backoff(attempt: int) -> float:
    return [0.5, 1.5][attempt] if attempt < 2 else 1.5


def _code_for_status(status: int) -> str:
    if status == 401:
        return "tumblr_unauthorized"
    if status == 403:
        return "tumblr_forbidden"
    if status == 404:
        return "tumblr_not_found"
    return "tumblr_api_error"


def _message_for_status(status: int) -> str:
    if status in {401, 403}:
        return "Tumblr credentials were rejected."
    if status == 404:
        return "The requested Tumblr resource was not found."
    return "Tumblr could not complete the request."
