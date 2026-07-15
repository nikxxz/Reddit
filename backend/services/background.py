from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable

from backend.services.lifecycle import application_lifecycle
from backend.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class TaskRecord:
    name: str
    group: str
    task: asyncio.Task
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, object] = field(default_factory=dict)


class BackgroundTaskRegistry:
    def __init__(self) -> None:
        self._records: dict[asyncio.Task, TaskRecord] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        awaitable: Awaitable[object],
        *,
        name: str,
        group: str,
        metadata: dict[str, object] | None = None,
    ) -> asyncio.Task:
        task = asyncio.create_task(awaitable, name=name)
        record = TaskRecord(name=name, group=group, task=task, metadata=metadata or {})
        async with self._lock:
            self._records[task] = record
            self._publish_count()
        task.add_done_callback(self._done)
        logger.info(
            "background.task.created task_name=%s task_group=%s active_task_count=%s",
            name,
            group,
            len(self._records),
        )
        return task

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self._records.values():
            counts[record.group] = counts.get(record.group, 0) + 1
        counts["total"] = len(self._records)
        return counts

    async def cancel_group(self, group: str) -> None:
        async with self._lock:
            tasks = [record.task for record in self._records.values() if record.group == group]
        for task in tasks:
            task.cancel()

    async def cancel_all(self) -> None:
        async with self._lock:
            tasks = list(self._records)
        for task in tasks:
            task.cancel()

    async def wait_for_group(self, group: str, timeout: float) -> None:
        async with self._lock:
            tasks = [record.task for record in self._records.values() if record.group == group]
        if not tasks:
            return
        await asyncio.wait(tasks, timeout=timeout)

    async def wait_all(self, timeout: float) -> None:
        async with self._lock:
            tasks = list(self._records)
        if not tasks:
            return
        await asyncio.wait(tasks, timeout=timeout)

    def _done(self, task: asyncio.Task) -> None:
        record = self._records.pop(task, None)
        self._publish_count()
        if not record:
            return
        if task.cancelled():
            logger.info("background.task.cancelled task_name=%s task_group=%s", record.name, record.group)
            return
        try:
            task.result()
        except Exception:
            logger.exception("background.task.failed task_name=%s task_group=%s", record.name, record.group)
            return
        logger.info("background.task.completed task_name=%s task_group=%s", record.name, record.group)

    def _publish_count(self) -> None:
        application_lifecycle.set_active_background_tasks(len(self._records))


background_task_registry = BackgroundTaskRegistry()
