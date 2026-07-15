from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DownloadScope = Literal["single", "gallery_current", "gallery_all"]
DownloadStatus = Literal[
    "queued",
    "resolving",
    "downloading",
    "merging",
    "completed",
    "failed",
    "cancelled",
]


class DownloadRequest(BaseModel):
    post_id: str = Field(min_length=1, max_length=80)
    media_type: str
    download_strategy: str | None = None
    media_url: str | None = None
    post_url: str | None = None
    subreddit: str | None = None
    author: str | None = None
    title: str | None = None
    gallery_urls: list[str] = Field(default_factory=list)
    gallery_index: int | None = None
    download_scope: DownloadScope = "single"


class DownloadStartResponse(BaseModel):
    job_id: str
    status: DownloadStatus


class DownloadedFile(BaseModel):
    filename: str | None = None
    category: str | None = None
    index: int | None = None
    status: str = "completed"
    error: str | None = None


class DownloadStatusResponse(BaseModel):
    job_id: str
    status: DownloadStatus
    progress: int | None = None
    message: str = ""
    filename: str | None = None
    files: list[DownloadedFile] = Field(default_factory=list)
    error: str | None = None
    bytes_downloaded: int | None = None
    total_bytes: int | None = None
