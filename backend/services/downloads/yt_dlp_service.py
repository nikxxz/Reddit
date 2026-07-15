from __future__ import annotations

from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL

from backend.services.downloads.errors import DownloadError
from backend.services.downloads.direct import validate_download_url


def download_with_yt_dlp(url: str, output_dir: Path, options: dict[str, Any] | None = None) -> Path:
    validate_download_url(url)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(title).200B-%(id)s.%(ext)s")
    ydl_options = {
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if options:
        ydl_options.update(options)
    try:
        with YoutubeDL(ydl_options) as ydl:
            result = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(result)
    except Exception as exc:
        raise DownloadError("The selected media could not be resolved.") from exc
    return Path(filename)
