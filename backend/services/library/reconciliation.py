from __future__ import annotations

from time import monotonic

from backend.config import settings
from backend.database.repositories import downloads as downloads_repo
from backend.services.library.thumbnails import regenerate_missing_thumbnails
from backend.utils.logging import get_logger


logger = get_logger(__name__)


def reconcile_library() -> dict[str, int]:
    started = monotonic()
    stats = {
        "downloads_examined": 0,
        "files_examined": 0,
        "files_missing": 0,
        "downloads_available": 0,
        "downloads_partial": 0,
        "downloads_missing": 0,
        "thumbnails_regenerated": 0,
    }
    logger.info("library.reconciliation.start")
    try:
        for download_id in downloads_repo.all_download_ids():
            stats["downloads_examined"] += 1
            checked, missing = downloads_repo.refresh_file_existence(download_id)
            availability = downloads_repo.update_availability(download_id)
            stats["files_examined"] += checked
            stats["files_missing"] += missing
            if availability == "available":
                stats["downloads_available"] += 1
            elif availability == "partially_available":
                stats["downloads_partial"] += 1
            elif availability == "missing":
                stats["downloads_missing"] += 1
            logger.info("library.reconciliation.download.checked download_id=%s availability=%s", download_id, availability)
        if settings.generate_missing_thumbnails_on_startup:
            stats["thumbnails_regenerated"] = regenerate_missing_thumbnails()
        logger.info(
            "library.reconciliation.completed downloads_examined=%s files_examined=%s files_missing=%s downloads_available=%s downloads_partial=%s downloads_missing=%s thumbnails_regenerated=%s elapsed_ms=%s",
            stats["downloads_examined"],
            stats["files_examined"],
            stats["files_missing"],
            stats["downloads_available"],
            stats["downloads_partial"],
            stats["downloads_missing"],
            stats["thumbnails_regenerated"],
            int((monotonic() - started) * 1000),
        )
        return stats
    except Exception:
        logger.exception("library.reconciliation.failed elapsed_ms=%s", int((monotonic() - started) * 1000))
        raise
