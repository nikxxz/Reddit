from __future__ import annotations

from backend.models.universal_search import (
    ProviderCapabilities,
    ProviderHealth,
    ProviderSearchRequest,
    ProviderSearchResult,
)
from backend.utils.logging import get_logger


logger = get_logger(__name__)


class PlaceholderProvider:
    provider_name = ""
    display_name = ""
    implementation_status = "planned"

    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        logger.info(
            "universal.provider.not_implemented provider=%s query_length=%s selected_media_types=%s",
            self.provider_name,
            len(request.query),
            ",".join(request.media_types),
        )
        return ProviderSearchResult(
            provider=self.provider_name,
            status="not_implemented",
            items=[],
        )

    async def health(self) -> ProviderHealth:
        return ProviderHealth(state="not_implemented", authenticated=False)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            keyword_search=True,
            account_browse=True,
            collection_browse=True,
            image_results=True,
            gif_results=True,
            video_results=True,
            gallery_results=True,
            single_download=False,
            gallery_download=False,
        )

