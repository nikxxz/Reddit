from __future__ import annotations

import asyncio
from time import monotonic

from backend.config import settings
from backend.models.universal_search import (
    ProviderJobSummary,
    ProviderSearchRequest,
    UniversalMediaItem,
    UniversalSearchRequest,
)
from backend.services.universal.registry import universal_provider_registry
from backend.utils.logging import get_logger


logger = get_logger(__name__)


class UniversalSearchCoordinator:
    def __init__(self, registry=universal_provider_registry) -> None:
        self.registry = registry

    async def search(self, search_id: str, request: UniversalSearchRequest) -> tuple[str, dict[str, ProviderJobSummary], list[UniversalMediaItem]]:
        started = monotonic()
        logger.info(
            "universal.search.started search_id=%s query_length=%s selected_provider_count=%s selected_media_types=%s",
            search_id,
            len(request.query),
            len(request.providers),
            ",".join(request.media_types),
        )
        semaphore = asyncio.Semaphore(settings.universal_search_max_concurrency)

        async def run_provider(provider_name: str):
            provider = self.registry.get(provider_name)
            async with semaphore:
                provider_request = ProviderSearchRequest(
                    query=request.query,
                    media_types=request.media_types,
                    include_nsfw=request.include_nsfw,
                    limit=request.limit_per_provider,
                    sort=request.sort,
                    provider_filters=request.provider_filters,
                )
                try:
                    return await provider.search(provider_request)
                except Exception:
                    logger.exception(
                        "universal.provider.search.failed search_id=%s provider=%s error_code=provider_exception",
                        search_id,
                        provider_name,
                    )
                    return None

        results = await asyncio.gather(*(run_provider(provider_name) for provider_name in request.providers))
        provider_states: dict[str, ProviderJobSummary] = {}
        provider_items: dict[str, list[UniversalMediaItem]] = {}

        for provider_name, result in zip(request.providers, results, strict=False):
            if result is None:
                provider_states[provider_name] = ProviderJobSummary(
                    status="failed",
                    result_count=0,
                    error="provider_failed",
                )
                provider_items[provider_name] = []
                continue
            provider_states[provider_name] = ProviderJobSummary(
                status=result.status,
                result_count=len(result.items),
                error=result.error_code,
            )
            provider_items[provider_name] = result.items

        items = self.merge_results(provider_items, request.sort)
        status = self._overall_status(provider_states)
        logger.info(
            "universal.search.%s search_id=%s result_count=%s elapsed_ms=%s",
            status,
            search_id,
            len(items),
            int((monotonic() - started) * 1000),
        )
        return status, provider_states, items

    def merge_results(
        self,
        provider_items: dict[str, list[UniversalMediaItem]],
        sort: str = "source_balanced",
    ) -> list[UniversalMediaItem]:
        if sort == "grouped":
            merged = []
            for items in provider_items.values():
                merged.extend(items)
            return merged

        queues = {provider: list(items) for provider, items in provider_items.items()}
        merged = []
        while any(queues.values()):
            for provider in queues:
                if queues[provider]:
                    merged.append(queues[provider].pop(0))
        return merged

    def _overall_status(self, provider_states: dict[str, ProviderJobSummary]) -> str:
        successful = {"completed", "no_results"}
        errorish = {
            "failed",
            "not_implemented",
            "authentication_required",
            "session_required",
            "extractor_unavailable",
            "rate_limited",
            "unavailable",
        }
        statuses = {state.status for state in provider_states.values()}
        if statuses and statuses <= successful:
            return "completed"
        if statuses & successful:
            return "completed_with_errors" if statuses & errorish else "completed"
        return "failed"


universal_search_coordinator = UniversalSearchCoordinator()
