from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DownloadScope = Literal["single", "gallery_current", "gallery_all", "gallery_missing"]
DownloadStatus = Literal[
    "queued",
    "resolving",
    "downloading",
    "merging",
    "finalizing",
    "completed",
    "completed_with_errors",
    "failed",
    "cancelled",
]


class DownloadRequest(BaseModel):
    post_id: str = Field(min_length=1, max_length=80)
    media_type: str = "unknown"
    download_strategy: str | None = None
    media_url: str | None = None
    post_url: str | None = None
    subreddit: str | None = None
    author: str | None = None
    title: str | None = None
    thumbnail_url: str | None = None
    gallery_urls: list[str] = Field(default_factory=list)
    gallery_index: int | None = None
    download_scope: DownloadScope = "single"
    force_hydrate: bool = False
    force_download: bool = False


class DownloadStartResponse(BaseModel):
    job_id: str
    status: DownloadStatus
    duplicate: bool = False
    existing_download_id: str | None = None
    message: str | None = None


class DuplicateDownloadDetail(BaseModel):
    type: str
    existing_download_id: str | None = None
    availability: str | None = None


class JobWarning(BaseModel):
    code: str
    message: str


class DownloadedFile(BaseModel):
    id: str | None = None
    filename: str | None = None
    category: str | None = None
    index: int | None = None
    status: str = "completed"
    error: str | None = None
    size_bytes: int | None = None
    exists_on_disk: bool | None = None


class DownloadStatusResponse(BaseModel):
    job_id: str
    status: DownloadStatus
    progress: int | None = None
    message: str = ""
    filename: str | None = None
    files: list[DownloadedFile] = Field(default_factory=list)
    error: str | None = None
    error_code: str | None = None
    warnings: list[JobWarning] = Field(default_factory=list)
    succeeded_count: int | None = None
    failed_count: int | None = None
    retry_of_id: str | None = None
    bytes_downloaded: int | None = None
    total_bytes: int | None = None


DownloadJobFilter = Literal[
    "all",
    "active",
    "queued",
    "completed",
    "completed_with_errors",
    "failed",
    "cancelled",
]


class DownloadJobSummary(BaseModel):
    id: str | None = None
    job_id: str
    post_id: str
    status: DownloadStatus
    availability: str = "unknown"
    progress: int | None = None
    message: str = ""
    media_type: str
    title: str | None = None
    subreddit: str | None = None
    author: str | None = None
    thumbnail_url: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    files: list[DownloadedFile] = Field(default_factory=list)
    error: str | None = None
    error_code: str | None = None
    warnings: list[JobWarning] = Field(default_factory=list)
    succeeded_count: int | None = None
    failed_count: int | None = None
    retry_of_id: str | None = None
    bytes_downloaded: int | None = None
    total_bytes: int | None = None
    cancellable: bool = False
    retryable: bool = False


class DownloadJobListResponse(BaseModel):
    jobs: list[DownloadJobSummary] = Field(default_factory=list)


class ClearDownloadsRequest(BaseModel):
    statuses: list[Literal["completed", "completed_with_errors", "failed", "cancelled"]] = Field(
        default_factory=lambda: ["completed", "completed_with_errors", "failed", "cancelled"]
    )


class ClearDownloadsResponse(BaseModel):
    removed: int
