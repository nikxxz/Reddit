from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.models.universal_search import (
    UniversalProviderListResponse,
    UniversalSearchRequest,
    UniversalSearchStartResponse,
    UniversalSearchStatusResponse,
)
from backend.models.downloads import DownloadRequest, DownloadStartResponse
from backend.services.downloads.errors import ApplicationShuttingDownError, DuplicateDownloadError, DownloadError
from backend.services.downloads.manager import download_job_manager
from backend.services.universal.jobs import universal_search_jobs
from backend.services.universal.registry import universal_provider_registry


router = APIRouter(tags=["universal-search"])


@router.get("/universal/providers", response_model=UniversalProviderListResponse)
async def list_universal_providers() -> UniversalProviderListResponse:
    return UniversalProviderListResponse(
        providers=await universal_provider_registry.list_summaries()
    )


@router.post("/universal/search", response_model=UniversalSearchStartResponse)
async def create_universal_search(request: UniversalSearchRequest) -> UniversalSearchStartResponse:
    unknown = sorted(set(request.providers) - universal_provider_registry.known_names())
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {', '.join(unknown)}")
    if request.limit_per_provider > settings.universal_search_max_limit:
        raise HTTPException(status_code=400, detail="limit_per_provider exceeds configured maximum.")
    return await universal_search_jobs.create(request)


@router.get("/universal/search/{search_id}", response_model=UniversalSearchStatusResponse)
def get_universal_search(search_id: str) -> UniversalSearchStatusResponse:
    response = universal_search_jobs.get(search_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Search job not found.")
    return response


@router.post("/universal/downloads", response_model=DownloadStartResponse)
async def start_universal_download(request: DownloadRequest) -> DownloadStartResponse:
    if request.provider not in universal_provider_registry.known_names():
        raise HTTPException(status_code=400, detail="Unknown provider.")
    try:
        job = await download_job_manager.create_job(request)
    except ApplicationShuttingDownError as exc:
        raise HTTPException(status_code=503, detail={"detail": str(exc), "error_code": exc.error_code}) from exc
    except DuplicateDownloadError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "This media already exists in your library.",
                "error_code": exc.error_code,
                "duplicate": exc.duplicate,
            },
        ) from exc
    except DownloadError as exc:
        raise HTTPException(status_code=507, detail=str(exc)) from exc
    return DownloadStartResponse(job_id=job.job_id, status="queued")
