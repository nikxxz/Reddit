from fastapi import APIRouter

from backend.config import settings
from backend.models import AppConfigResponse, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name)


@router.get("/app-config", response_model=AppConfigResponse)
def app_config() -> AppConfigResponse:
    return AppConfigResponse(
        app_name=settings.app_name,
    )
