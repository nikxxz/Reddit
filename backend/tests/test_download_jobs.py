import asyncio
import unittest
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from backend.models.downloads import DownloadRequest
from backend.services.downloads.errors import DownloadError
from backend.services.downloads.manager import DownloadJob, DownloadJobManager


async def wait_for_terminal(manager, job_id):
    for _ in range(30):
        status = manager.get_status(job_id)
        if status.status in {"completed", "failed", "cancelled"}:
            return status
        await asyncio.sleep(0.01)
    raise AssertionError("job did not finish")


class DownloadJobTests(unittest.IsolatedAsyncioTestCase):
    async def test_queued_to_completed(self):
        manager = DownloadJobManager(max_concurrent=1)
        request = DownloadRequest(
            post_id="abc123",
            media_type="image",
            media_url="https://i.redd.it/example.jpg",
            subreddit="pics",
            author="user",
            title="Example",
        )
        with patch("backend.services.downloads.resolver.validate_download_url"), patch(
            "backend.services.downloads.manager.download_direct_url",
            return_value=Path("downloads/images/pics_user_example.jpg"),
        ):
            job = await manager.create_job(request)
            status = await wait_for_terminal(manager, job.job_id)
        self.assertEqual(status.status, "completed")
        self.assertEqual(status.files[0].filename, "pics_user_example.jpg")

    async def test_queued_to_failed(self):
        manager = DownloadJobManager(max_concurrent=1)
        request = DownloadRequest(
            post_id="abc123",
            media_type="image",
            media_url="https://i.redd.it/example.jpg",
        )
        with patch("backend.services.downloads.resolver.validate_download_url"), patch(
            "backend.services.downloads.manager.download_direct_url",
            side_effect=DownloadError("The media is no longer available."),
        ):
            job = await manager.create_job(request)
            status = await wait_for_terminal(manager, job.job_id)
        self.assertEqual(status.status, "failed")
        self.assertEqual(status.error, "The media is no longer available.")

    async def test_unknown_job_id(self):
        manager = DownloadJobManager(max_concurrent=1)
        self.assertIsNone(manager.get_status("missing"))

    async def test_cancellation(self):
        manager = DownloadJobManager(max_concurrent=1)
        request = DownloadRequest(
            post_id="abc123",
            media_type="image",
            media_url="https://i.redd.it/example.jpg",
        )
        with patch("backend.services.downloads.resolver.validate_download_url"), patch(
            "backend.services.downloads.manager.download_direct_url",
            side_effect=lambda *args, **kwargs: (_ for _ in ()).throw(
                DownloadError("should not complete")
            ),
        ):
            job = await manager.create_job(request)
            status = manager.cancel_job(job.job_id)
        self.assertEqual(status.status, "cancelled")

    async def test_completed_job_removed_after_retention(self):
        manager = DownloadJobManager(max_concurrent=1)
        job = DownloadJob(
            job_id="old",
            request=DownloadRequest(post_id="abc123", media_type="image", media_url="https://i.redd.it/example.jpg"),
            status="completed",
            updated_at=monotonic() - 7200,
        )
        manager.jobs[job.job_id] = job
        with patch("backend.services.downloads.manager.settings.download_job_retention_hours", 1):
            stats = manager.cleanup_jobs()
        self.assertEqual(stats["completed_removed"], 1)
        self.assertNotIn("old", manager.jobs)

    async def test_recent_completed_job_preserved(self):
        manager = DownloadJobManager(max_concurrent=1)
        job = DownloadJob(
            job_id="recent",
            request=DownloadRequest(post_id="abc123", media_type="image", media_url="https://i.redd.it/example.jpg"),
            status="completed",
        )
        manager.jobs[job.job_id] = job
        with patch("backend.services.downloads.manager.settings.download_job_retention_hours", 1):
            stats = manager.cleanup_jobs()
        self.assertEqual(stats["jobs_removed"], 0)
        self.assertIn("recent", manager.jobs)

    async def test_active_job_never_removed(self):
        manager = DownloadJobManager(max_concurrent=1)
        job = DownloadJob(
            job_id="active",
            request=DownloadRequest(post_id="abc123", media_type="image", media_url="https://i.redd.it/example.jpg"),
            status="downloading",
            updated_at=monotonic() - 7200,
        )
        manager.jobs[job.job_id] = job
        with patch("backend.services.downloads.manager.settings.download_job_retention_hours", 1):
            stats = manager.cleanup_jobs()
        self.assertEqual(stats["jobs_removed"], 0)
        self.assertIn("active", manager.jobs)

    async def test_failed_and_cancelled_retention(self):
        manager = DownloadJobManager(max_concurrent=1)
        request = DownloadRequest(post_id="abc123", media_type="image", media_url="https://i.redd.it/example.jpg")
        manager.jobs["failed"] = DownloadJob(
            job_id="failed",
            request=request,
            status="failed",
            updated_at=monotonic() - 7200,
        )
        manager.jobs["cancelled"] = DownloadJob(
            job_id="cancelled",
            request=request,
            status="cancelled",
            updated_at=monotonic() - 7200,
        )
        with patch("backend.services.downloads.manager.settings.failed_job_retention_hours", 1):
            stats = manager.cleanup_jobs()
        self.assertEqual(stats["failed_removed"], 1)
        self.assertEqual(stats["cancelled_removed"], 1)

    async def test_cancelled_job_cannot_become_completed(self):
        manager = DownloadJobManager(max_concurrent=1)
        job = DownloadJob(
            job_id="cancelled",
            request=DownloadRequest(post_id="abc123", media_type="image", media_url="https://i.redd.it/example.jpg"),
            status="cancelled",
        )
        self.assertFalse(manager.transition_job(job, "completed"))
        self.assertEqual(job.status, "cancelled")

    async def test_repeated_cancel_is_safe(self):
        manager = DownloadJobManager(max_concurrent=1)
        job = DownloadJob(
            job_id="cancel",
            request=DownloadRequest(post_id="abc123", media_type="image", media_url="https://i.redd.it/example.jpg"),
        )
        manager.jobs[job.job_id] = job
        first = manager.cancel_job(job.job_id)
        second = manager.cancel_job(job.job_id)
        self.assertEqual(first.status, "cancelled")
        self.assertEqual(second.status, "cancelled")

    async def test_late_progress_callback_does_not_change_terminal_state(self):
        manager = DownloadJobManager(max_concurrent=1)
        job = DownloadJob(
            job_id="done",
            request=DownloadRequest(post_id="abc123", media_type="image", media_url="https://i.redd.it/example.jpg"),
            status="cancelled",
            progress=None,
            message="Download cancelled",
        )
        manager._update_progress(job, 50, 100)
        self.assertEqual(job.status, "cancelled")
        self.assertIsNone(job.progress)

    async def test_sufficient_disk_permits_download(self):
        manager = DownloadJobManager(max_concurrent=1)
        request = DownloadRequest(
            post_id="abc123",
            media_type="image",
            media_url="https://i.redd.it/example.jpg",
        )
        with patch("backend.services.downloads.manager.has_minimum_free_space", return_value=True), patch(
            "backend.services.downloads.resolver.validate_download_url"
        ), patch(
            "backend.services.downloads.manager.download_direct_url",
            return_value=Path("downloads/images/example.jpg"),
        ):
            job = await manager.create_job(request)
            status = await wait_for_terminal(manager, job.job_id)
        self.assertEqual(status.status, "completed")

    async def test_insufficient_disk_rejects_download(self):
        manager = DownloadJobManager(max_concurrent=1)
        request = DownloadRequest(
            post_id="abc123",
            media_type="image",
            media_url="https://i.redd.it/example.jpg",
        )
        with patch("backend.services.downloads.manager.has_minimum_free_space", return_value=False):
            with self.assertRaises(DownloadError) as context:
                await manager.create_job(request)
        self.assertEqual(str(context.exception), "Not enough free disk space to start this download.")


if __name__ == "__main__":
    unittest.main()
