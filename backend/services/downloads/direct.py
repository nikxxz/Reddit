from __future__ import annotations

import ipaddress
import socket
import threading
from pathlib import Path
from time import monotonic
from time import sleep
from typing import Callable
from urllib.parse import urljoin, urlparse

import httpx

from backend.config import settings
from backend.services.downloads.errors import DownloadCancelled, DownloadError, MediaResolutionError, UrlSafetyError
from backend.services.downloads.filenames import safe_filename_from_url, unique_path


ProgressCallback = Callable[[int, int | None], None]

ALLOWED_DIRECT_HOSTS = {
    "i.redd.it",
    "preview.redd.it",
    "v.redd.it",
    "redditmedia.com",
    "www.redditmedia.com",
    "imgur.com",
    "i.imgur.com",
    "redgifs.com",
    "www.redgifs.com",
    "streamable.com",
    "www.streamable.com",
}
ALLOWED_CONTENT_PREFIXES = ("image/", "video/")
ALLOWED_CONTENT_TYPES = {"application/octet-stream"}


def validate_download_url(url: str, allowed_hosts: set[str] | None = None) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UrlSafetyError("invalid_url", "The media URL is invalid.")
    if parsed.username or parsed.password:
        raise UrlSafetyError("unsafe_url", "The media URL was rejected for safety reasons.")

    hostname = parsed.hostname.lower()
    hosts = allowed_hosts or ALLOWED_DIRECT_HOSTS
    if hosts and not any(hostname == host or hostname.endswith(f".{host}") for host in hosts):
        raise UrlSafetyError("unsupported_host", "Downloads from this media host are not supported.")

    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UrlSafetyError("invalid_url", "The media URL is invalid.") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise UrlSafetyError("unsafe_url", "The media URL was rejected for safety reasons.")


def download_direct_url(
    url: str,
    output_dir: Path,
    filename: str | None = None,
    max_size_bytes: int | None = None,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> Path:
    validate_download_url(url)
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = unique_path(output_dir, filename or safe_filename_from_url(url))
    part_path = final_path.with_suffix(final_path.suffix + ".part")
    deadline = monotonic() + settings.download_total_timeout
    timeout = httpx.Timeout(
        connect=settings.media_connect_timeout,
        read=settings.media_read_timeout,
        write=settings.media_read_timeout,
        pool=settings.media_connect_timeout,
    )

    try:
        for attempt in range(settings.max_download_retries + 1):
            try:
                return _stream_to_file(
                    url,
                    final_path,
                    part_path,
                    timeout,
                    max_size_bytes,
                    deadline,
                    progress_callback,
                    cancel_event,
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in {429, 500, 502, 503, 504} or attempt >= settings.max_download_retries:
                    raise
                sleep(_retry_delay(exc, attempt))
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError):
                if attempt >= settings.max_download_retries:
                    raise
                sleep(float(2**attempt))
    except httpx.TimeoutException as exc:
        _cleanup_part(part_path)
        raise DownloadError("The download exceeded the configured timeout.") from exc
    except httpx.HTTPStatusError as exc:
        _cleanup_part(part_path)
        if exc.response.status_code == 404:
            raise DownloadError("The media URL is no longer available.") from exc
        if exc.response.status_code == 429:
            raise DownloadError("The download host rejected the request.") from exc
        raise DownloadError("The download host rejected the request.") from exc
    except DownloadCancelled:
        _cleanup_part(part_path)
        raise
    except Exception:
        _cleanup_part(part_path)
        raise

    raise DownloadError("The selected media could not be resolved.")


def _stream_to_file(
    url: str,
    final_path: Path,
    part_path: Path,
    timeout: httpx.Timeout,
    max_size_bytes: int | None,
    deadline: float,
    progress_callback: ProgressCallback | None,
    cancel_event: threading.Event | None,
) -> Path:
    bytes_written = 0
    current_url = url
    for _ in range(6):
        validate_download_url(current_url)
        with httpx.stream("GET", current_url, timeout=timeout, follow_redirects=False) as response:
            status_code = getattr(response, "status_code", getattr(getattr(response, "response", None), "status_code", 200))
            if status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise UrlSafetyError("invalid_url", "The media URL is invalid.")
                current_url = urljoin(current_url, location)
                continue
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if not _valid_content_type(content_type):
                raise MediaResolutionError("unsupported_media_type")
            content_length = _safe_int(response.headers.get("content-length"))
            if max_size_bytes is not None and content_length and content_length > max_size_bytes:
                raise DownloadError("The selected media is too large.")
            with part_path.open("wb") as file:
                for chunk in response.iter_bytes():
                    if cancel_event and cancel_event.is_set():
                        raise DownloadCancelled("The download was cancelled.")
                    if monotonic() > deadline:
                        raise httpx.TimeoutException("download total timeout exceeded")
                    if not chunk:
                        continue
                    bytes_written += len(chunk)
                    if max_size_bytes is not None and bytes_written > max_size_bytes:
                        raise DownloadError("The selected media is too large.")
                    file.write(chunk)
                    if progress_callback:
                        progress_callback(bytes_written, content_length)
            part_path.replace(final_path)
            return final_path
    raise UrlSafetyError("unsafe_url", "The media URL was rejected for safety reasons.")


def _valid_content_type(content_type: str) -> bool:
    return content_type in ALLOWED_CONTENT_TYPES or content_type.startswith(ALLOWED_CONTENT_PREFIXES)


def _retry_delay(error: httpx.HTTPStatusError, attempt: int) -> float:
    retry_after = error.response.headers.get("Retry-After")
    try:
        return min(float(retry_after), 30.0)
    except (TypeError, ValueError):
        return float(2**attempt)


def _cleanup_part(part_path: Path) -> None:
    try:
        part_path.unlink(missing_ok=True)
    except OSError:
        pass


def _safe_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None
