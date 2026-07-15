SAFE_RESOLUTION_MESSAGES = {
    "missing_media_url": "The original media URL is unavailable.",
    "missing_post_url": "The Reddit post URL is unavailable.",
    "missing_gallery_urls": "Gallery media could not be loaded.",
    "invalid_gallery_index": "The selected gallery item is no longer available.",
    "missing_cached_item": "The selected post is no longer available. Search for it again.",
    "unsupported_media_type": "This media type is not supported for downloading.",
    "unsupported_download_strategy": "This media cannot currently be downloaded.",
    "unsafe_url": "The media URL was rejected for safety reasons.",
    "unsupported_host": "Downloads from this media host are not supported.",
    "invalid_url": "The media URL is invalid.",
    "hydration_failed": "Reddit could not provide full media details for this post.",
    "hydration_returned_no_media": "No downloadable media was found in this post.",
    "external_media_unsupported": "This external media provider is not supported.",
    "reddit_video_metadata_missing": "Reddit video details were incomplete.",
}


class DownloadError(RuntimeError):
    error_code: str | None = None


class DuplicateDownloadError(DownloadError):
    error_code = "duplicate_download"

    def __init__(self, duplicate: dict[str, object]) -> None:
        self.duplicate = duplicate
        super().__init__("This media already exists in your library.")


class MediaResolutionError(DownloadError):
    def __init__(
        self,
        code: str,
        safe_message: str | None = None,
        debug_context: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.error_code = code
        self.safe_message = safe_message or SAFE_RESOLUTION_MESSAGES.get(
            code,
            "Selected media could not be resolved.",
        )
        self.debug_context = debug_context or {}
        super().__init__(self.safe_message)


class UrlSafetyError(MediaResolutionError):
    def __init__(self, code: str = "unsafe_url", safe_message: str | None = None) -> None:
        super().__init__(code, safe_message)


class DownloadCancelled(DownloadError):
    pass
