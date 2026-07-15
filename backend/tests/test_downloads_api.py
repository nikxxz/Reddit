import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.models.downloads import DownloadRequest
from backend.services.downloads.errors import DownloadError
from backend.services.downloads.manager import DownloadJob, DownloadJobManager, download_job_manager


def request(post_id="abc123", media_url="https://i.redd.it/example.jpg"):
    return DownloadRequest(
        post_id=post_id,
        media_type="image",
        media_url=media_url,
        subreddit="pics",
        author="user",
        title="Example",
        thumbnail_url="https://preview.redd.it/thumb.jpg?token=secret",
    )


class DownloadListApiTests(unittest.TestCase):
    def setUp(self):
        self.original_jobs = download_job_manager.jobs
        download_job_manager.jobs = {}

    def tearDown(self):
        download_job_manager.jobs = self.original_jobs

    def test_list_endpoint_returns_safe_summaries(self):
        download_job_manager.jobs["job-1"] = DownloadJob(
            job_id="job-1",
            request=request(),
            status="completed",
            files=[{"filename": "pics_user_example.jpg", "category": "images", "status": "completed"}],
        )
        client = TestClient(app)
        response = client.get("/api/downloads")
        self.assertEqual(response.status_code, 200)
        job = response.json()["jobs"][0]
        self.assertEqual(job["job_id"], "job-1")
        self.assertEqual(job["thumbnail_url"], "https://preview.redd.it/thumb.jpg")
        serialized = str(job)
        self.assertNotIn("cancel_event", serialized)
        self.assertNotIn("lock", serialized)
        self.assertNotIn("token=secret", serialized)
        self.assertNotIn(":\\", serialized)

    def test_active_filter_works(self):
        download_job_manager.jobs["active"] = DownloadJob(
            job_id="active",
            request=request("active"),
            status="downloading",
        )
        download_job_manager.jobs["done"] = DownloadJob(
            job_id="done",
            request=request("done"),
            status="completed",
        )
        client = TestClient(app)
        response = client.get("/api/downloads?status=active")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([job["job_id"] for job in response.json()["jobs"]], ["active"])

    def test_clear_terminal_removes_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            media = Path(tmpdir) / "downloaded.jpg"
            media.write_bytes(b"ok")
            download_job_manager.jobs["done"] = DownloadJob(
                job_id="done",
                request=request("done"),
                status="completed",
                files=[{"filename": media.name, "category": "images", "status": "completed"}],
            )
            download_job_manager.jobs["active"] = DownloadJob(
                job_id="active",
                request=request("active"),
                status="downloading",
            )
            client = TestClient(app)
            response = client.delete("/api/downloads/terminal")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["removed"], 1)
            self.assertTrue(media.exists())
            self.assertNotIn("done", download_job_manager.jobs)
            self.assertIn("active", download_job_manager.jobs)


class DownloadManagerVisibilityTests(unittest.IsolatedAsyncioTestCase):
    def test_jobs_ordered_consistently(self):
        manager = DownloadJobManager(max_concurrent=1)
        for index, status in enumerate(["cancelled", "completed", "failed", "queued", "downloading"]):
            manager.jobs[status] = DownloadJob(
                job_id=status,
                request=request(status),
                status=status,
                created_at=float(index),
            )
        self.assertEqual(
            [job.job_id for job in manager.list_jobs()],
            ["downloading", "queued", "failed", "completed", "cancelled"],
        )

    def test_active_jobs_cannot_be_cleared(self):
        manager = DownloadJobManager(max_concurrent=1)
        manager.jobs["active"] = DownloadJob(
            job_id="active",
            request=request("active"),
            status="downloading",
        )
        self.assertEqual(manager.clear_terminal_jobs(), 0)
        self.assertIn("active", manager.jobs)

    async def test_retry_creates_new_job_and_preserves_old(self):
        manager = DownloadJobManager(max_concurrent=1)
        old = DownloadJob(
            job_id="old",
            request=request("old"),
            status="failed",
            error="Download failed",
            message="Download failed",
        )
        manager.jobs[old.job_id] = old
        with patch("backend.services.downloads.manager.has_minimum_free_space", return_value=True), patch(
            "backend.services.downloads.resolver.validate_download_url"
        ), patch(
            "backend.services.downloads.manager.download_direct_url",
            return_value=Path("downloads/images/pics_user_example.jpg"),
        ):
            new_job = await manager.retry_job("old")
            for _ in range(30):
                status = manager.get_status(new_job.job_id)
                if status.status in {"completed", "failed", "cancelled"}:
                    break
                await asyncio.sleep(0.01)
        self.assertNotEqual(new_job.job_id, "old")
        self.assertEqual(manager.jobs["old"].status, "failed")

    async def test_retry_rejects_active_job(self):
        manager = DownloadJobManager(max_concurrent=1)
        manager.jobs["active"] = DownloadJob(
            job_id="active",
            request=request("active"),
            status="downloading",
        )
        with self.assertRaises(DownloadError):
            await manager.retry_job("active")

    async def test_retry_uses_trusted_stored_metadata(self):
        manager = DownloadJobManager(max_concurrent=1)
        trusted = request("trusted", "https://i.redd.it/trusted.jpg")
        manager.jobs["old"] = DownloadJob(
            job_id="old",
            request=trusted,
            status="failed",
        )
        captured = {}

        async def fake_create_job(download_request):
            captured["request"] = download_request
            return DownloadJob(job_id="new", request=download_request)

        with patch.object(manager, "create_job", side_effect=fake_create_job):
            new_job = await manager.retry_job("old")
        self.assertEqual(new_job.job_id, "new")
        self.assertEqual(captured["request"].media_url, "https://i.redd.it/trusted.jpg")


if __name__ == "__main__":
    unittest.main()
