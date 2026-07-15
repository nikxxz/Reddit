from __future__ import annotations

import importlib.util
import shutil
import time
from pathlib import Path

from backend.config import settings
from backend.utils.logging import get_logger


logger = get_logger(__name__)
PART_SUFFIX = ".part"
DOWNLOAD_CATEGORIES = ("images", "videos", "gifs", "galleries", "external")


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def yt_dlp_available() -> bool:
    return importlib.util.find_spec("yt_dlp") is not None or shutil.which("yt-dlp") is not None


def disk_free_gb(path: Path | None = None) -> float:
    target = path or settings.download_dir_path
    existing = target if target.exists() else target.parent
    usage = shutil.disk_usage(existing)
    return round(usage.free / (1024**3), 1)


def ensure_download_directory() -> None:
    settings.download_dir_path.mkdir(parents=True, exist_ok=True)


def download_directory_ready(path: Path | None = None) -> bool:
    target = path or settings.download_dir_path
    return target.exists() and target.is_dir()


def download_directory_writable(path: Path | None = None) -> bool:
    target = path or settings.download_dir_path
    if not download_directory_ready(target):
        return False
    probe = target / ".write-test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def has_minimum_free_space(path: Path | None = None) -> bool:
    return disk_free_gb(path) >= settings.min_free_disk_gb


def configured_download_dirs(root: Path | None = None) -> list[Path]:
    base = (root or settings.download_dir_path).resolve()
    dirs = [base]
    dirs.extend(base / category for category in DOWNLOAD_CATEGORIES)
    return dirs


def cleanup_stale_part_files(
    *,
    root: Path | None = None,
    max_age_hours: float | None = None,
    active_part_paths: set[Path] | None = None,
) -> dict[str, int]:
    base = (root or settings.download_dir_path).resolve()
    threshold_hours = max_age_hours if max_age_hours is not None else settings.part_file_max_age_hours
    active = {path.resolve() for path in active_part_paths or set()}
    started = time.monotonic()
    files_examined = 0
    files_removed = 0

    logger.info("download.part_cleanup.start max_age_hours=%s", threshold_hours)
    if not base.exists():
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "download.part_cleanup.completed files_examined=0 files_removed=0 elapsed_ms=%s",
            elapsed_ms,
        )
        return {"files_examined": 0, "files_removed": 0, "elapsed_ms": elapsed_ms}

    cutoff = time.time() - (threshold_hours * 3600)
    for directory in configured_download_dirs(base):
        if not directory.exists() or not directory.is_dir():
            continue
        for path in directory.glob(f"*{PART_SUFFIX}"):
            resolved = path.resolve()
            files_examined += 1
            try:
                resolved.relative_to(base)
            except ValueError:
                continue
            if resolved in active:
                continue
            try:
                stat = path.stat()
            except OSError as exc:
                logger.warning(
                    "download.part_cleanup.failed filename=%s error_type=%s",
                    _relative_name(path, base),
                    exc.__class__.__name__,
                )
                continue
            age_hours = max(0.0, (time.time() - stat.st_mtime) / 3600)
            if stat.st_mtime > cutoff:
                continue
            try:
                path.unlink()
                files_removed += 1
                logger.info(
                    "download.part_cleanup.removed filename=%s age_hours=%.1f",
                    _relative_name(path, base),
                    age_hours,
                )
            except OSError as exc:
                logger.warning(
                    "download.part_cleanup.failed filename=%s age_hours=%.1f error_type=%s",
                    _relative_name(path, base),
                    age_hours,
                    exc.__class__.__name__,
                )

    elapsed_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "download.part_cleanup.completed files_examined=%s files_removed=%s elapsed_ms=%s",
        files_examined,
        files_removed,
        elapsed_ms,
    )
    return {
        "files_examined": files_examined,
        "files_removed": files_removed,
        "elapsed_ms": elapsed_ms,
    }


def startup_diagnostics() -> None:
    ensure_download_directory()
    ready = download_directory_ready()
    writable = download_directory_writable()
    free_space = disk_free_gb()
    logger.info(
        "system.dependencies.checked ffmpeg_available=%s yt_dlp_available=%s",
        ffmpeg_available(),
        yt_dlp_available(),
    )
    logger.info(
        "system.download_directory.checked download_directory_ready=%s download_directory_writable=%s",
        ready,
        writable,
    )
    logger.info("system.disk_space.checked free_space_gb=%s", free_space)


def _relative_name(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base).as_posix()
    except ValueError:
        return path.name
