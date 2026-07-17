from __future__ import annotations

from backend.models.universal_search import UniversalProviderSummary
from backend.services.universal.base import UniversalMediaProvider
from backend.services.universal.errors import DuplicateProviderError, UnknownProviderError
from backend.services.universal.providers.instagram_placeholder import InstagramPlaceholderProvider
from backend.services.universal.providers.pinterest import pinterest_provider
from backend.services.universal.providers.reddit_adapter import RedditUniversalProvider
from backend.services.universal.providers.tumblr import TumblrUniversalProvider


class UniversalProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, UniversalMediaProvider] = {}

    def register(self, provider: UniversalMediaProvider) -> None:
        if provider.provider_name in self._providers:
            raise DuplicateProviderError(f"Provider already registered: {provider.provider_name}")
        self._providers[provider.provider_name] = provider

    def get(self, provider_name: str) -> UniversalMediaProvider:
        try:
            return self._providers[provider_name]
        except KeyError:
            raise UnknownProviderError(f"Unknown provider: {provider_name}") from None

    def known_names(self) -> set[str]:
        return set(self._providers)

    async def list_summaries(self) -> list[UniversalProviderSummary]:
        summaries = []
        for provider in self._providers.values():
            health = await provider.health()
            summaries.append(
                UniversalProviderSummary(
                    name=provider.provider_name,
                    display_name=provider.display_name,
                    implementation_status=provider.implementation_status,
                    health=health.state,
                    authenticated=health.authenticated,
                    capabilities=provider.capabilities(),
                    rate_limit=health.rate_limit,
                )
            )
        return summaries


def create_default_registry() -> UniversalProviderRegistry:
    registry = UniversalProviderRegistry()
    registry.register(RedditUniversalProvider())
    registry.register(TumblrUniversalProvider())
    registry.register(pinterest_provider)
    registry.register(InstagramPlaceholderProvider())
    return registry


universal_provider_registry = create_default_registry()
