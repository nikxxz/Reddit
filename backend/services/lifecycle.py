from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class LifecycleSnapshot:
    starting: bool
    ready: bool
    shutting_down: bool
    database_ready: bool
    download_manager_ready: bool
    reddit_ready: bool
    library_reconciliation_in_progress: bool
    last_reconciliation_at: str | None
    last_reconciliation_error: str | None
    maintenance_tasks_running: bool
    active_background_tasks: int


class ApplicationLifecycle:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.starting = False
        self.ready = False
        self.shutting_down = False
        self.database_ready = False
        self.download_manager_ready = False
        self.reddit_ready = False
        self.library_reconciliation_in_progress = False
        self.last_reconciliation_at: str | None = None
        self.last_reconciliation_error: str | None = None
        self.maintenance_tasks_running = False
        self.active_background_tasks = 0

    def mark_starting(self) -> None:
        with self._lock:
            self.starting = True
            self.ready = False
            self.shutting_down = False

    def mark_ready(self, *, database_ready: bool, download_manager_ready: bool, reddit_ready: bool) -> None:
        with self._lock:
            self.starting = False
            self.ready = database_ready and download_manager_ready
            self.database_ready = database_ready
            self.download_manager_ready = download_manager_ready
            self.reddit_ready = reddit_ready

    def mark_shutdown(self) -> None:
        with self._lock:
            self.shutting_down = True
            self.ready = False

    def set_reconciliation(
        self,
        *,
        running: bool,
        completed: bool = False,
        error: str | None = None,
    ) -> None:
        with self._lock:
            self.library_reconciliation_in_progress = running
            if completed:
                self.last_reconciliation_at = datetime.now(timezone.utc).isoformat()
            self.last_reconciliation_error = error

    def set_maintenance_running(self, running: bool) -> None:
        with self._lock:
            self.maintenance_tasks_running = running

    def set_active_background_tasks(self, count: int) -> None:
        with self._lock:
            self.active_background_tasks = count

    def snapshot(self) -> LifecycleSnapshot:
        with self._lock:
            return LifecycleSnapshot(
                starting=self.starting,
                ready=self.ready,
                shutting_down=self.shutting_down,
                database_ready=self.database_ready,
                download_manager_ready=self.download_manager_ready,
                reddit_ready=self.reddit_ready,
                library_reconciliation_in_progress=self.library_reconciliation_in_progress,
                last_reconciliation_at=self.last_reconciliation_at,
                last_reconciliation_error=self.last_reconciliation_error,
                maintenance_tasks_running=self.maintenance_tasks_running,
                active_background_tasks=self.active_background_tasks,
            )


application_lifecycle = ApplicationLifecycle()
