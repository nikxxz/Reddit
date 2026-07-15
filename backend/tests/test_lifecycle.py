import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app
from backend.models.downloads import DownloadRequest
from backend.services.background import BackgroundTaskRegistry
from backend.services.downloads.manager import DownloadJob, DownloadJobManager
from backend.services.lifecycle import ApplicationLifecycle, application_lifecycle
from backend.services.library.reconciliation import LibraryReconciliationService


class LifecycleEndpointTests(unittest.TestCase):
    def test_readiness_returns_503_when_shutting_down(self):
        original = application_lifecycle.snapshot()
        application_lifecycle.mark_ready(database_ready=True, download_manager_ready=True, reddit_ready=True)
        application_lifecycle.mark_shutdown()
        try:
            response = TestClient(app).get("/api/ready")
            self.assertEqual(response.status_code, 503)
            detail = response.json()["detail"]
            self.assertFalse(detail["ready"])
            self.assertTrue(detail["shutting_down"])
        finally:
            application_lifecycle.starting = original.starting
            application_lifecycle.ready = original.ready
            application_lifecycle.shutting_down = original.shutting_down
            application_lifecycle.database_ready = original.database_ready
            application_lifecycle.download_manager_ready = original.download_manager_ready
            application_lifecycle.reddit_ready = original.reddit_ready

    def test_system_status_includes_lifecycle_fields(self):
        application_lifecycle.mark_ready(database_ready=True, download_manager_ready=True, reddit_ready=True)
        with patch("backend.routes.system.library_counts", return_value={"downloads": 0, "files": 0, "missing_files": 0}):
            response = TestClient(app).get("/api/system/status")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("application_ready", body)
        self.assertIn("maintenance_tasks_running", body)


class BackgroundTaskRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_registry_retains_and_removes_completed_tasks(self):
        registry = BackgroundTaskRegistry()

        async def work():
            await asyncio.sleep(0)
            return "ok"

        task = await registry.create(work(), name="unit-task", group="maintenance")
        self.assertEqual(registry.counts()["total"], 1)
        await task
        await asyncio.sleep(0)
        self.assertEqual(registry.counts()["total"], 0)

    async def test_registry_cancels_group(self):
        registry = BackgroundTaskRegistry()
        started = asyncio.Event()

        async def work():
            started.set()
            await asyncio.sleep(30)

        task = await registry.create(work(), name="cancel-task", group="reconciliation")
        await started.wait()
        await registry.cancel_group("reconciliation")
        with self.assertRaises(asyncio.CancelledError):
            await task


class ReconciliationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_reconciliation_request_is_rejected(self):
        service = LibraryReconciliationService()

        async def slow_run(_cancel_event):
            await asyncio.sleep(30)

        with patch.object(service, "_run", side_effect=slow_run):
            started, already = await service.start()
            second_started, second_already = await service.start()
            self.assertTrue(started)
            self.assertFalse(already)
            self.assertFalse(second_started)
            self.assertTrue(second_already)
            await service.cancel()


class DownloadManagerShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_downloads_rejected_during_shutdown(self):
        manager = DownloadJobManager(max_concurrent=1)
        manager.shutting_down = True
        with self.assertRaises(Exception) as context:
            await manager.create_job(DownloadRequest(post_id="abc123", media_type="image"))
        self.assertEqual(getattr(context.exception, "error_code", None), "application_shutting_down")

    async def test_shutdown_marks_queued_jobs_cancelled(self):
        manager = DownloadJobManager(max_concurrent=1)
        job = DownloadJob(job_id="queued", request=DownloadRequest(post_id="abc123"), status="queued")
        manager.jobs[job.job_id] = job
        result = await manager.shutdown(0.01)
        self.assertEqual(result.jobs_cancelled, 1)
        self.assertEqual(job.status, "cancelled")
        self.assertEqual(job.error_code, "application_shutdown")

    async def test_shutdown_marks_active_jobs_interrupted(self):
        manager = DownloadJobManager(max_concurrent=1)
        job = DownloadJob(job_id="active", request=DownloadRequest(post_id="abc123"), status="downloading")
        manager.jobs[job.job_id] = job
        result = await manager.shutdown(0.01)
        self.assertEqual(result.jobs_interrupted, 1)
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.error_code, "interrupted_by_shutdown")


class DirectDownloadCancellationTests(unittest.TestCase):
    def test_cancelled_direct_download_removes_part_file(self):
        from backend.services.downloads.direct import DownloadCancelled, download_direct_url

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir)
            part = output / "example.jpg.part"
            part.write_bytes(b"partial")
            event = __import__("threading").Event()
            event.set()
            with patch("backend.services.downloads.direct.validate_download_url"), patch(
                "backend.services.downloads.direct.unique_path",
                return_value=output / "example.jpg",
            ):
                with self.assertRaises(DownloadCancelled):
                    download_direct_url("https://i.redd.it/example.jpg", output, filename="example.jpg", cancel_event=event)
            self.assertFalse(part.exists())


if __name__ == "__main__":
    unittest.main()
