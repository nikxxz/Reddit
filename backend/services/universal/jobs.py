from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.config import settings
from backend.models.universal_search import (
    ProviderJobSummary,
    UniversalMediaItem,
    UniversalSearchRequest,
    UniversalSearchStartResponse,
    UniversalSearchStatusResponse,
)
from backend.services.background import background_task_registry
from backend.services.universal.coordinator import universal_search_coordinator
from backend.services.universal.registry import universal_provider_registry
from backend.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class UniversalSearchJob:
    search_id: str
    request: UniversalSearchRequest
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "queued"
    providers: dict[str, ProviderJobSummary] = field(default_factory=dict)
    items: list[UniversalMediaItem] = field(default_factory=list)


class UniversalSearchJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, UniversalSearchJob] = {}

    async def create(self, request: UniversalSearchRequest) -> UniversalSearchStartResponse:
        self.cleanup_jobs()
        search_id = str(uuid4())
        providers = {
            provider_name: ProviderJobSummary(
                status=(
                    "not_implemented"
                    if universal_provider_registry.get(provider_name).implementation_status == "planned"
                    else "searching"
                ),
                result_count=0,
            )
            for provider_name in request.providers
        }
        job = UniversalSearchJob(
            search_id=search_id,
            request=request,
            status="searching",
            providers=providers,
        )
        self._jobs[search_id] = job
        logger.info(
            "universal.search.created search_id=%s query_length=%s selected_provider_count=%s selected_media_types=%s",
            search_id,
            len(request.query),
            len(request.providers),
            ",".join(request.media_types),
        )
        await background_task_registry.create(
            self._run(job),
            name=f"universal-search-{search_id}",
            group="universal-search",
            metadata={"search_id": search_id},
        )
        return self._start_response(job)

    def get(self, search_id: str) -> UniversalSearchStatusResponse | None:
        job = self._jobs.get(search_id)
        if not job:
            return None
        return UniversalSearchStatusResponse(
            search_id=job.search_id,
            status=job.status,
            providers=job.providers,
            items=job.items,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def cleanup_jobs(self) -> int:
        now = datetime.now(timezone.utc)
        retention = timedelta(minutes=settings.universal_search_retention_minutes)
        terminal = {"completed", "completed_with_errors", "failed", "cancelled"}
        removable = [
            search_id
            for search_id, job in self._jobs.items()
            if job.status in terminal and now - job.updated_at > retention
        ]
        overflow = max(len(self._jobs) - settings.universal_search_max_jobs, 0)
        if overflow:
            terminal_jobs = [
                job
                for job in self._jobs.values()
                if job.status in terminal and job.search_id not in removable
            ]
            terminal_jobs.sort(key=lambda job: job.updated_at)
            removable.extend(job.search_id for job in terminal_jobs[:overflow])
        for search_id in set(removable):
            self._jobs.pop(search_id, None)
        if removable:
            logger.info("universal.search.cleaned removed=%s", len(set(removable)))
        return len(set(removable))

    async def _run(self, job: UniversalSearchJob) -> None:
        try:
            status, providers, items = await universal_search_coordinator.search(job.search_id, job.request)
            job.status = status
            job.providers = providers
            job.items = items
            job.updated_at = datetime.now(timezone.utc)
        except Exception:
            logger.exception("universal.search.failed search_id=%s error_code=coordinator_failed", job.search_id)
            job.status = "failed"
            job.updated_at = datetime.now(timezone.utc)

    def _start_response(self, job: UniversalSearchJob) -> UniversalSearchStartResponse:
        return UniversalSearchStartResponse(
            search_id=job.search_id,
            status=job.status,
            providers=job.providers,
        )


universal_search_jobs = UniversalSearchJobManager()
