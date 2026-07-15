from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.database.repositories import downloads as downloads_repo
from backend.models import ReconciliationStartResponse, ReconciliationStatusResponse
from backend.services.library.reconciliation import library_reconciliation_service
from backend.services.library.thumbnails import dummy_thumbnail_response, thumbnail_response


router = APIRouter(tags=["library"])


@router.get("/library/thumbnails/dummy")
def dummy_thumbnail() -> Response:
    return dummy_thumbnail_response()


@router.get("/library/thumbnails/{download_id}")
def get_thumbnail(download_id: str) -> Response:
    return thumbnail_response(download_id)


@router.post("/library/reconcile", response_model=ReconciliationStartResponse, status_code=202)
async def start_reconciliation() -> ReconciliationStartResponse:
    started, already_running = await library_reconciliation_service.start()
    return ReconciliationStartResponse(started=started, already_running=already_running)


@router.get("/library/reconcile/status", response_model=ReconciliationStatusResponse)
def reconciliation_status() -> ReconciliationStatusResponse:
    return ReconciliationStatusResponse(**library_reconciliation_service.snapshot())


@router.delete("/library/downloads/{download_id}")
def delete_download_record(download_id: str) -> dict[str, int]:
    removed = downloads_repo.delete_download(download_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Download record not found.")
    return {"removed": removed}
