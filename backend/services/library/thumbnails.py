from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response

from backend.config import settings
from backend.core.paths import get_thumbnail_root, resolve_app_data_path, resolve_download_path, to_relative_app_data_path
from backend.database.repositories import downloads as downloads_repo
from backend.utils.logging import get_logger


logger = get_logger(__name__)
DUMMY_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360"><rect width="480" height="360" fill="#f1f3f5"/><path d="M170 220h140l-42-55-32 39-22-28z" fill="#adb5bd"/><circle cx="190" cy="145" r="24" fill="#ced4da"/></svg>"""
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
GIF_EXTENSIONS = {".gif"}
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".webm", ".mkv"}


def generate_thumbnail_for_download(download_id: str) -> None:
    files = downloads_repo.files_for_download(download_id)
    source = _first_existing_file(files)
    if not source:
        downloads_repo.set_thumbnail(
            download_id=download_id,
            source_file_id=None,
            relative_path=None,
            source_type="dummy",
            exists_on_disk=False,
        )
        return
    path = resolve_download_path(str(source["relative_path"]))
    ext = path.suffix.lower()
    if ext in IMAGE_EXTENSIONS or ext in GIF_EXTENSIONS:
        if _generate_image_thumbnail(download_id, path):
            return
        source_type = "downloaded_gallery_item" if source["gallery_index"] is not None else "downloaded_image"
        downloads_repo.set_thumbnail(
            download_id=download_id,
            source_file_id=str(source["id"]),
            relative_path=str(source["relative_path"]),
            source_type=source_type,
            exists_on_disk=True,
        )
        return
    if ext in VIDEO_EXTENSIONS and _generate_video_thumbnail(download_id, path):
        return
    downloads_repo.set_thumbnail(
        download_id=download_id,
        source_file_id=str(source["id"]),
        relative_path=None,
        source_type="dummy",
        exists_on_disk=False,
    )


def thumbnail_response(download_id: str) -> Response:
    row = downloads_repo.thumbnail_for_download(download_id)
    if not row or row["source_type"] == "dummy" or not row["relative_path"]:
        return dummy_thumbnail_response()
    relative_path = str(row["relative_path"])
    try:
        if row["source_type"].startswith("generated"):
            path = resolve_app_data_path(relative_path)
        else:
            path = resolve_download_path(relative_path)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Thumbnail not found.") from exc
    if not path.exists():
        return dummy_thumbnail_response()
    return FileResponse(path)


def dummy_thumbnail_response() -> Response:
    return Response(content=DUMMY_SVG, media_type="image/svg+xml")


def regenerate_missing_thumbnails() -> int:
    regenerated = 0
    for download_id in downloads_repo.all_download_ids():
        row = downloads_repo.thumbnail_for_download(download_id)
        missing = not row or (
            row["relative_path"]
            and row["source_type"].startswith("generated")
            and not resolve_app_data_path(str(row["relative_path"])).exists()
        )
        if missing:
            generate_thumbnail_for_download(download_id)
            regenerated += 1
            logger.info("library.reconciliation.thumbnail_regenerated download_id=%s", download_id)
    return regenerated


def _first_existing_file(files: Iterable[object]):
    for file in files:
        try:
            if file["exists_on_disk"] and resolve_download_path(str(file["relative_path"])).exists():
                return file
        except Exception:
            continue
    return None


def _thumbnail_path(download_id: str) -> Path:
    suffix = ".webp" if settings.thumbnail_format == "webp" else ".jpg"
    return get_thumbnail_root() / f"{download_id}{suffix}"


def _generate_image_thumbnail(download_id: str, source: Path) -> bool:
    try:
        from PIL import Image, ImageOps
    except Exception:
        return False
    target = _thumbnail_path(download_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((settings.thumbnail_max_width, settings.thumbnail_max_height))
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGB")
            image.save(target, format=settings.thumbnail_format.upper())
            width, height = image.size
        downloads_repo.set_thumbnail(
            download_id=download_id,
            source_file_id=None,
            relative_path=to_relative_app_data_path(target),
            source_type="generated_image",
            width=width,
            height=height,
            exists_on_disk=True,
        )
        return True
    except Exception:
        logger.exception("library.thumbnail.image.failed download_id=%s", download_id)
        return False


def _generate_video_thumbnail(download_id: str, source: Path) -> bool:
    if shutil.which("ffmpeg") is None:
        return False
    target = _thumbnail_path(download_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        "00:00:01",
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        f"scale='min({settings.thumbnail_max_width},iw)':-2",
        str(target),
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        downloads_repo.set_thumbnail(
            download_id=download_id,
            source_file_id=None,
            relative_path=to_relative_app_data_path(target),
            source_type="generated_video_frame",
            exists_on_disk=target.exists(),
        )
        return target.exists()
    except Exception:
        logger.warning("library.thumbnail.video.failed download_id=%s", download_id)
        return False
