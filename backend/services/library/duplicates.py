from __future__ import annotations

from backend.models.downloads import DownloadRequest
from backend.database.repositories.downloads import find_duplicate


def duplicate_for_request(request: DownloadRequest):
    try:
        return find_duplicate(
            request.post_id,
            request.media_type,
            request.download_scope,
            request.gallery_index if request.download_scope == "gallery_current" else None,
        )
    except Exception:
        return None
