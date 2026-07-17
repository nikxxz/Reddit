from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import quote, urlparse, urlunparse


PINTEREST_HOSTS = {"pinterest.com", "www.pinterest.com", "pin.it"}
PINTEREST_CDN_SUFFIXES = (
    ".pinimg.com",
    ".pinterest.com",
)
USERNAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,29}$")
SLUG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_. -]{0,80}$")


def search_url(query: str) -> str:
    clean = query.strip()[:160]
    return f"https://www.pinterest.com/search/pins/?q={quote(clean)}"


def normalize_pin_url(value: str | None) -> str | None:
    parsed = _safe_pinterest_url(value)
    if not parsed:
        return None
    if parsed.hostname == "pin.it":
        return urlunparse(parsed._replace(query="", fragment=""))
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "pin" and parts[1].isdigit():
        return f"https://www.pinterest.com/pin/{parts[1]}/"
    return None


def normalize_profile_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme:
        parsed = _safe_pinterest_url(value)
        if not parsed:
            return None
        parts = [part for part in parsed.path.split("/") if part]
        username = parts[0] if parts else ""
    else:
        username = value.strip().strip("@/")
    if not USERNAME_RE.fullmatch(username):
        return None
    return f"https://www.pinterest.com/{username}/"


def normalize_board_url(value: str | None, section: str | None = None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme:
        parsed = _safe_pinterest_url(value)
        if not parsed:
            return None
        parts = [part for part in parsed.path.split("/") if part]
    else:
        parts = [part for part in value.strip("/").split("/") if part]
    if len(parts) < 2:
        return None
    username, board = parts[0], parts[1]
    selected_section = section or (parts[2] if len(parts) > 2 else None)
    if not USERNAME_RE.fullmatch(username) or not SLUG_RE.fullmatch(board):
        return None
    path = f"/{username}/{quote(board.strip(), safe='')}/"
    if selected_section:
        if not SLUG_RE.fullmatch(selected_section):
            return None
        path += f"{quote(selected_section.strip(), safe='')}/"
    return f"https://www.pinterest.com{path}"


def is_safe_preview_url(value: str | None) -> bool:
    parsed = urlparse(value or "")
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        return False
    if parsed.port not in {None, 80, 443}:
        return False
    host = parsed.hostname.lower()
    if not any(host == suffix.lstrip(".") or host.endswith(suffix) for suffix in PINTEREST_CDN_SUFFIXES):
        return False
    return not _private_host(host)


def _safe_pinterest_url(value: str | None):
    if not value:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    if parsed.port not in {None, 443}:
        return None
    host = parsed.hostname.lower()
    if host not in PINTEREST_HOSTS and not host.endswith(".pinterest.com"):
        return None
    if _private_host(host):
        return None
    return parsed


def _private_host(host: str) -> bool:
    try:
        addresses = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
    return False
