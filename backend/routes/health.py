from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.models import AppConfigResponse, HealthResponse, ReadinessResponse
from backend.services.lifecycle import application_lifecycle

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name)


@router.get("/ready", response_model=ReadinessResponse)
def ready() -> ReadinessResponse:
    snapshot = application_lifecycle.snapshot()
    response = ReadinessResponse(
        ready=snapshot.ready and not snapshot.shutting_down,
        database_ready=snapshot.database_ready,
        download_manager_ready=snapshot.download_manager_ready,
        shutting_down=snapshot.shutting_down,
    )
    if not response.ready:
        raise HTTPException(status_code=503, detail=response.model_dump())
    return response


@router.get("/app-config", response_model=AppConfigResponse)
def app_config() -> AppConfigResponse:
    return AppConfigResponse(
        app_name=settings.app_name,
    )
