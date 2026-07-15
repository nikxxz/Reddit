from __future__ import annotations

import asyncio
from time import monotonic

from backend.config import settings
from backend.services.downloads.manager import download_job_manager
from backend.services.lifecycle import application_lifecycle
from backend.services.library.backups import create_routine_backup_if_due
from backend.utils.logging import get_logger


logger = get_logger(__name__)


class MaintenanceScheduler:
    def __init__(self) -> None:
        self._stop_event = asyncio.Event()
        self._running = False
        self._operation_lock = asyncio.Lock()

    async def run(self) -> None:
        self._running = True
        self._stop_event.clear()
        application_lifecycle.set_maintenance_running(True)
        logger.info("maintenance.loop.started")
        try:
            while not self._stop_event.is_set():
                await self.run_once()
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=settings.maintenance_interval_minutes * 60,
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            self._running = False
            application_lifecycle.set_maintenance_running(False)
            logger.info("maintenance.loop.stopped")

    async def stop(self) -> None:
        self._stop_event.set()

    async def run_once(self) -> None:
        if self._operation_lock.locked():
            return
        async with self._operation_lock:
            await self._run_operation("job_cleanup", lambda: download_job_manager.cleanup_jobs())
            await self._run_operation("routine_backup", create_routine_backup_if_due)
            await self._run_operation("part_cleanup", lambda: download_job_manager.cleanup_stale_part_files())

    async def _run_operation(self, name: str, operation) -> None:
        started = monotonic()
        logger.info("maintenance.operation.started operation=%s", name)
        try:
            await asyncio.to_thread(operation)
            logger.info(
                "maintenance.operation.completed operation=%s elapsed_ms=%s",
                name,
                int((monotonic() - started) * 1000),
            )
        except Exception:
            logger.exception(
                "maintenance.operation.failed operation=%s elapsed_ms=%s",
                name,
                int((monotonic() - started) * 1000),
            )


maintenance_scheduler = MaintenanceScheduler()
