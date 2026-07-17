from __future__ import annotations

from typing import Protocol

from backend.models.universal_search import (
    ProviderCapabilities,
    ProviderHealth,
    ProviderSearchRequest,
    ProviderSearchResult,
)


class UniversalMediaProvider(Protocol):
    provider_name: str
    display_name: str
    implementation_status: str

    async def search(self, request: ProviderSearchRequest) -> ProviderSearchResult:
        ...

    async def health(self) -> ProviderHealth:
        ...

    def capabilities(self) -> ProviderCapabilities:
        ...

