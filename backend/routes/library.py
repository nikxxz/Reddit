from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.database.repositories import downloads as downloads_repo
from backend.services.library.thumbnails import dummy_thumbnail_response, thumbnail_response


router = APIRouter(tags=["library"])


@router.get("/library/thumbnails/dummy")
def dummy_thumbnail() -> Response:
    return dummy_thumbnail_response()


@router.get("/library/thumbnails/{download_id}")
def get_thumbnail(download_id: str) -> Response:
    return thumbnail_response(download_id)


@router.delete("/library/downloads/{download_id}")
def delete_download_record(download_id: str) -> dict[str, int]:
    removed = downloads_repo.delete_download(download_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Download record not found.")
    return {"removed": removed}
