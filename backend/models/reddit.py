from pydantic import BaseModel


class RedditGalleryItem(BaseModel):
    index: int
    media_id: str | None = None
    media_type: str = "image"
    url: str
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None


class RedditConnectionStatus(BaseModel):
    connected: bool
    read_only: bool = True
    authenticated_user: str | None = None
    error: str | None = None


class RedditMediaItem(BaseModel):
    id: str
    title: str
    subreddit: str | None = None
    author: str | None = None
    created_utc: float | None = None
    permalink: str | None = None
    post_url: str | None = None
    media_type: str
    thumbnail_url: str | None = None
    media_url: str | None = None
    media_urls: list[str] = []
    gallery_items: list[RedditGalleryItem] = []
    reddit_video: dict[str, str | int | None] | None = None
    provider: str | None = None
    width: int | None = None
    height: int | None = None
    duration: int | None = None
    is_gallery: bool = False
    gallery_count: int = 0
    is_nsfw: bool = False
    download_strategy: str = "unsupported"


class RedditSearchResponse(BaseModel):
    mode: str | None = None
    query: str
    subreddit: str | None = None
    requested_sort: str | None = None
    effective_sort: str | None = None
    media_type: str
    sort: str
    time_filter: str
    count: int
    next_after: str | None = None
    message: str | None = None
    items: list[RedditMediaItem]
