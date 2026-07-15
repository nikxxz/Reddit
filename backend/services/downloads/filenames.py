from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse


SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
WINDOWS_INVALID_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
WHITESPACE_RE = re.compile(r"\s+")
RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *{f"COM{index}" for index in range(1, 10)},
    *{f"LPT{index}" for index in range(1, 10)},
}
MAX_BASE_LENGTH = 140


def safe_filename_from_url(url: str, fallback: str = "download") -> str:
    name = Path(urlparse(url).path).name or fallback
    name = SAFE_FILENAME_RE.sub("_", name).strip("._")
    return name or fallback


def build_download_filename(
    *,
    subreddit: str | None,
    author: str | None,
    title: str | None,
    post_id: str,
    source_url: str | None,
    extension: str | None = None,
    gallery_index: int | None = None,
) -> str:
    clean_subreddit = sanitize_filename_part(subreddit or "reddit")
    clean_author = sanitize_filename_part(author or "deleted")
    if clean_author.lower() in {"none", "null", "[deleted]", "deleted"}:
        clean_author = "deleted"

    clean_title = sanitize_filename_part(title or "")
    if not clean_title:
        clean_title = sanitize_filename_part(original_stem(source_url) or f"reddit_media_{post_id}")

    suffix = f"_{gallery_index:02d}" if gallery_index is not None else ""
    ext = normalize_extension(extension or extension_from_url(source_url) or ".bin")
    base = f"{clean_subreddit}_{clean_author}_{clean_title}{suffix}"
    base = base[:MAX_BASE_LENGTH].rstrip("._ ")
    base = avoid_reserved_name(base or f"reddit_media_{post_id}")
    return f"{base}{ext}"


def sanitize_filename_part(value: str) -> str:
    value = unquote(str(value)).strip()
    value = value.replace("..", " ")
    value = WINDOWS_INVALID_RE.sub(" ", value)
    value = WHITESPACE_RE.sub("_", value)
    value = SAFE_FILENAME_RE.sub("_", value)
    value = re.sub(r"_+", "_", value)
    value = value.strip("._ ")
    value = value.lower()
    return avoid_reserved_name(value) if value else ""


def avoid_reserved_name(value: str) -> str:
    if value.upper() in RESERVED_WINDOWS_NAMES:
        return f"{value}_file"
    return value


def original_stem(url: str | None) -> str | None:
    if not url:
        return None
    stem = Path(urlparse(url).path).stem
    return stem or None


def extension_from_url(url: str | None) -> str | None:
    if not url:
        return None
    suffix = Path(urlparse(url).path).suffix
    return normalize_extension(suffix) if suffix else None


def normalize_extension(extension: str) -> str:
    extension = (extension or ".bin").split("?")[0].split("#")[0].strip().lower()
    if not extension.startswith("."):
        extension = f".{extension}"
    extension = WINDOWS_INVALID_RE.sub("", extension)
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", extension):
        return ".bin"
    return extension


def unique_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists() and not candidate.with_suffix(candidate.suffix + ".part").exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        next_candidate = directory / f"{stem}_{counter}{suffix}"
        if not next_candidate.exists() and not next_candidate.with_suffix(suffix + ".part").exists():
            return next_candidate
        counter += 1
