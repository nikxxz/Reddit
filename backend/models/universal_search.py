from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


ProviderName = Literal["reddit", "tumblr", "pinterest", "instagram"]
UniversalMediaType = Literal["image", "gif", "video", "gallery", "external", "unknown"]
UniversalSort = Literal["source_balanced", "grouped", "relevance", "new", "top"]
ProviderHealthState = Literal[
    "ready",
    "unavailable",
    "not_implemented",
    "authentication_required",
    "rate_limited",
    "degraded",
    "failed",
]
ProviderJobStatus = Literal[
    "queued",
    "searching",
    "completed",
    "no_results",
    "not_implemented",
    "authentication_required",
    "rate_limited",
    "unavailable",
    "failed",
]
UniversalSearchStatus = Literal[
    "queued",
    "searching",
    "completed",
    "completed_with_errors",
    "failed",
    "cancelled",
]


class ProviderCapabilities(BaseModel):
    keyword_search: bool = False
    account_browse: bool = False
    collection_browse: bool = False
    image_results: bool = False
    gif_results: bool = False
    video_results: bool = False
    gallery_results: bool = False
    single_download: bool = False
    gallery_download: bool = False


class ProviderHealth(BaseModel):
    state: ProviderHealthState
    authenticated: bool = False
    error_code: str | None = None
    rate_limit: dict[str, object] | None = None


class TumblrProviderFilter(BaseModel):
    mode: Literal["tag", "blog", "blog_tag"] = "tag"
    blog: str | None = None
    tag: str | None = None


class ProviderFilters(BaseModel):
    tumblr: TumblrProviderFilter | None = None


class ProviderSearchRequest(BaseModel):
    query: str
    media_types: list[UniversalMediaType]
    include_nsfw: bool = False
    limit: int = Field(default=24, ge=1, le=100)
    sort: UniversalSort = "source_balanced"
    provider_filters: ProviderFilters = Field(default_factory=ProviderFilters)


class UniversalItemCapabilities(BaseModel):
    preview: bool = True
    download_single: bool = False
    download_all: bool = False


class UniversalMediaItem(BaseModel):
    provider: ProviderName
    provider_item_id: str
    canonical_url: str | None = None
    title: str
    description: str | None = None
    author: str | None = None
    collection: str | None = None
    media_type: UniversalMediaType
    thumbnail_url: str | None = None
    preview_url: str | None = None
    media_urls: list[str] = []
    media_count: int | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None
    created_at: datetime | None = None
    nsfw: bool = False
    source_metadata: dict[str, object] = {}
    capabilities: UniversalItemCapabilities = Field(default_factory=UniversalItemCapabilities)


class ProviderSearchResult(BaseModel):
    provider: ProviderName
    status: ProviderJobStatus
    items: list[UniversalMediaItem] = []
    next_cursor: str | None = None
    error_code: str | None = None


class UniversalProviderSummary(BaseModel):
    name: ProviderName
    display_name: str
    implementation_status: Literal["available", "planned", "configuration_required"]
    health: ProviderHealthState
    authenticated: bool
    capabilities: ProviderCapabilities
    rate_limit: dict[str, object] | None = None


class UniversalProviderListResponse(BaseModel):
    providers: list[UniversalProviderSummary]


class UniversalSearchRequest(BaseModel):
    query: str
    providers: list[ProviderName]
    media_types: list[UniversalMediaType] = ["image", "gif", "video", "gallery"]
    sort: UniversalSort = "source_balanced"
    include_nsfw: bool = False
    limit_per_provider: int = Field(default=24, ge=1, le=100)
    provider_filters: ProviderFilters = Field(default_factory=ProviderFilters)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("query must not be blank")
        return clean

    @field_validator("providers")
    @classmethod
    def validate_providers(cls, value: list[ProviderName]) -> list[ProviderName]:
        if not value:
            raise ValueError("at least one provider must be selected")
        return list(dict.fromkeys(value))

    @field_validator("media_types")
    @classmethod
    def validate_media_types(cls, value: list[UniversalMediaType]) -> list[UniversalMediaType]:
        if not value:
            raise ValueError("at least one media type must be selected")
        return list(dict.fromkeys(value))


class ProviderJobSummary(BaseModel):
    status: ProviderJobStatus
    result_count: int = 0
    error: str | None = None


class UniversalSearchStartResponse(BaseModel):
    search_id: str
    status: UniversalSearchStatus
    providers: dict[str, ProviderJobSummary]


class UniversalSearchStatusResponse(UniversalSearchStartResponse):
    items: list[UniversalMediaItem] = []
    created_at: datetime
    updated_at: datetime
