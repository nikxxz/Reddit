import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.models.downloads import DownloadRequest
from backend.services.downloads.errors import DownloadError
from backend.services.downloads.manager import DownloadJobManager


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


if __name__ == "__main__":
    unittest.main()
