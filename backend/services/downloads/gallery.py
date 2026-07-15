from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from backend.services.downloads.direct import download_direct_url
from backend.services.downloads.errors import DownloadError


GalleryProgressCallback = Callable[[int, int, int, int | None], None]


def download_gallery_urls(
    *,
    urls: list[str],
    output_dir: Path,
    filenames: list[str],
    max_size_bytes: int,
    progress_callback: GalleryProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    completed: list[dict[str, object]] = []
    failed: list[dict[str, object]] = []
    total = len(urls)

    for index, (url, filename) in enumerate(zip(urls, filenames), start=1):
        try:
            path = download_direct_url(
                url,
                output_dir,
                filename=filename,
                max_size_bytes=max_size_bytes,
                progress_callback=(
                    lambda bytes_written, total_bytes, item_index=index: progress_callback(
                        item_index, bytes_written, total_bytes, total
                    )
                    if progress_callback
                    else None
                ),
                cancel_event=cancel_event,
            )
            completed.append({"index": index, "filename": path.name, "status": "completed"})
        except Exception as exc:
            failed.append(
                {
                    "index": index,
                    "filename": filename,
                    "status": "failed",
                    "error": _safe_gallery_error(exc),
                }
            )

    if not completed:
        raise DownloadError("One or more gallery items could not be downloaded.")

    return completed, failed


def _safe_gallery_error(error: Exception) -> str:
    message = str(error)
    if message:
        return message
    return "Media unavailable"
