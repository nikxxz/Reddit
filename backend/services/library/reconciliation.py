from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import monotonic

from backend.config import settings
from backend.database.repositories import downloads as downloads_repo
from backend.services.background import background_task_registry
from backend.services.lifecycle import application_lifecycle
from backend.services.library.thumbnails import regenerate_missing_thumbnails
from backend.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class ReconciliationStatus:
    running: bool = False
    started_at: str | None = None
    downloads_examined: int = 0
    files_examined: int = 0
    files_missing: int = 0
    downloads_available: int = 0
    downloads_partial: int = 0
    downloads_missing: int = 0
    thumbnails_regenerated: int = 0
    last_error: str | None = None
    _cancel_event: asyncio.Event | None = field(default=None, repr=False)


class LibraryReconciliationService:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._status = ReconciliationStatus()

    async def start(self) -> tuple[bool, bool]:
        async with self._lock:
            if self._task and not self._task.done():
                return False, True
            self._status = ReconciliationStatus(
                running=True,
                started_at=datetime.now(timezone.utc).isoformat(),
                _cancel_event=asyncio.Event(),
            )
            application_lifecycle.set_reconciliation(running=True)
            self._task = await background_task_registry.create(
                self._run(self._status._cancel_event),
                name="library-reconciliation",
                group="reconciliation",
            )
            logger.info("library.reconciliation.scheduled")
            return True, False

    async def cancel(self) -> None:
        async with self._lock:
            if self._status._cancel_event:
                self._status._cancel_event.set()
            task = self._task
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    def snapshot(self) -> dict[str, object]:
        return {
            "running": self._status.running,
            "started_at": self._status.started_at,
            "downloads_examined": self._status.downloads_examined,
            "files_examined": self._status.files_examined,
            "files_missing": self._status.files_missing,
            "thumbnails_regenerated": self._status.thumbnails_regenerated,
            "last_error": self._status.last_error,
        }

    async def _run(self, cancel_event: asyncio.Event | None) -> None:
        started = monotonic()
        logger.info("library.reconciliation.started")
        try:
            download_ids = await asyncio.to_thread(downloads_repo.all_download_ids)
            batch_size = settings.library_reconcile_batch_size
            for offset in range(0, len(download_ids), batch_size):
                if cancel_event and cancel_event.is_set():
                    logger.info("library.reconciliation.cancelled records_examined=%s", self._status.downloads_examined)
                    return
                batch = download_ids[offset : offset + batch_size]
                await self._process_batch(batch)
                await asyncio.sleep(0)
            if settings.generate_missing_thumbnails_on_startup and not (cancel_event and cancel_event.is_set()):
                self._status.thumbnails_regenerated = await asyncio.to_thread(regenerate_missing_thumbnails)
            logger.info(
                "library.reconciliation.completed records_examined=%s files_examined=%s files_missing=%s thumbnails_regenerated=%s elapsed_ms=%s",
                self._status.downloads_examined,
                self._status.files_examined,
                self._status.files_missing,
                self._status.thumbnails_regenerated,
                int((monotonic() - started) * 1000),
            )
            application_lifecycle.set_reconciliation(running=False, completed=True)
        except asyncio.CancelledError:
            logger.info("library.reconciliation.cancelled records_examined=%s", self._status.downloads_examined)
            application_lifecycle.set_reconciliation(running=False)
            raise
        except Exception:
            logger.exception("library.reconciliation.failed elapsed_ms=%s", int((monotonic() - started) * 1000))
            self._status.last_error = "reconciliation_failed"
            application_lifecycle.set_reconciliation(running=False, error="reconciliation_failed")
        finally:
            self._status.running = False

    async def _process_batch(self, download_ids: list[str]) -> None:
        semaphore = asyncio.Semaphore(settings.library_reconcile_max_concurrency)

        async def process(download_id: str) -> tuple[int, int, str]:
            async with semaphore:
                checked, missing = await asyncio.to_thread(downloads_repo.refresh_file_existence, download_id)
                availability = await asyncio.to_thread(downloads_repo.update_availability, download_id)
                return checked, missing, availability

        for checked, missing, availability in await asyncio.gather(*(process(download_id) for download_id in download_ids)):
            self._status.downloads_examined += 1
            self._status.files_examined += checked
            self._status.files_missing += missing
            if availability == "available":
                self._status.downloads_available += 1
            elif availability == "partially_available":
                self._status.downloads_partial += 1
            elif availability == "missing":
                self._status.downloads_missing += 1


library_reconciliation_service = LibraryReconciliationService()


def reconcile_library() -> dict[str, int]:
    stats = {
        "downloads_examined": 0,
        "files_examined": 0,
        "files_missing": 0,
        "downloads_available": 0,
        "downloads_partial": 0,
        "downloads_missing": 0,
        "thumbnails_regenerated": 0,
    }
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
    if settings.generate_missing_thumbnails_on_startup:
        stats["thumbnails_regenerated"] = regenerate_missing_thumbnails()
    return stats
