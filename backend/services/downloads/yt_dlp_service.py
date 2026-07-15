from __future__ import annotations

import shutil
import threading
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL

from backend.services.downloads.errors import DownloadCancelled, DownloadError
from backend.services.downloads.direct import validate_download_url
from backend.services.downloads.filenames import unique_path

YT_DLP_ALLOWED_HOSTS = {
    "reddit.com",
    "www.reddit.com",
    "old.reddit.com",
    "v.redd.it",
    "imgur.com",
    "i.imgur.com",
    "redgifs.com",
    "www.redgifs.com",
    "streamable.com",
    "www.streamable.com",
}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def download_with_yt_dlp(
    url: str,
    output_dir: Path,
    filename: str,
    options: dict[str, Any] | None = None,
    progress_callback: Any | None = None,
    cancel_event: threading.Event | None = None,
) -> Path:
    validate_download_url(url, allowed_hosts=YT_DLP_ALLOWED_HOSTS)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = unique_path(output_dir, filename)
    output_template = str(target.with_suffix(".%(ext)s"))

    def hook(progress: dict[str, Any]) -> None:
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelled("The download was cancelled.")
        if progress_callback:
            progress_callback(progress)

    ydl_options = {
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
    }
    if options:
        ydl_options.update(options)
    try:
        with YoutubeDL(ydl_options) as ydl:
            result = ydl.extract_info(url, download=True)
            downloaded_filename = ydl.prepare_filename(result)
    except Exception as exc:
        if isinstance(exc, DownloadCancelled):
            raise
        raise DownloadError("The selected media could not be resolved.") from exc
    return Path(downloaded_filename)
