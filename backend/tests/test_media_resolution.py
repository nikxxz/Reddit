import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from backend.models.downloads import DownloadRequest
from backend.models.reddit import RedditGalleryItem, RedditMediaItem
from backend.services.downloads.errors import MediaResolutionError
from backend.services.downloads.manager import DownloadJob, DownloadJobManager
from backend.services.downloads.resolver import resolve_download_request
from backend.services.reddit.media_cache import normalized_media_cache


def media_item(**updates):
    data = {
        "id": "abc123",
        "title": "Example",
        "subreddit": "pics",
        "author": "user",
        "permalink": "https://www.reddit.com/r/pics/comments/abc123/example/",
        "post_url": "https://www.reddit.com/r/pics/comments/abc123/example/",
        "media_type": "image",
        "media_url": "https://i.redd.it/example.jpg",
        "media_urls": ["https://i.redd.it/example.jpg"],
        "download_strategy": "direct",
    }
    data.update(updates)
    return RedditMediaItem(**data)


class MediaResolutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        normalized_media_cache.clear()

    def tearDown(self):
        normalized_media_cache.clear()

    async def test_cached_direct_image_resolves_without_hydration(self):
        normalized_media_cache.set(media_item())
        with patch("backend.services.downloads.resolver.validate_download_url") as validate, patch(
            "backend.services.downloads.resolver.hydrate_submission_media", new_callable=AsyncMock
        ) as hydrate:
            resolved = await resolve_download_request(DownloadRequest(post_id="abc123"))
        self.assertEqual(resolved.strategy, "direct")
        self.assertEqual(resolved.urls, ["https://i.redd.it/example.jpg"])
        validate.assert_called_once()
        hydrate.assert_not_called()

    async def test_cache_miss_triggers_selected_post_hydration(self):
        hydrated = media_item(media_url="https://i.redd.it/hydrated.jpg", media_urls=["https://i.redd.it/hydrated.jpg"])
        with patch("backend.services.downloads.resolver.validate_download_url"), patch(
            "backend.services.downloads.resolver.hydrate_submission_media",
            new=AsyncMock(return_value=hydrated),
        ) as hydrate:
            resolved = await resolve_download_request(DownloadRequest(post_id="abc123"))
        self.assertEqual(resolved.urls, ["https://i.redd.it/hydrated.jpg"])
        hydrate.assert_awaited_once_with("abc123")

    async def test_invalid_gallery_index_has_code(self):
        item = media_item(
            media_type="gallery",
            media_url="https://i.redd.it/one.jpg",
            media_urls=["https://i.redd.it/one.jpg"],
            gallery_items=[RedditGalleryItem(index=0, media_id="one", url="https://i.redd.it/one.jpg")],
        )
        normalized_media_cache.set(item)
        with self.assertRaises(MediaResolutionError) as context:
            await resolve_download_request(
                DownloadRequest(post_id="abc123", download_scope="gallery_current", gallery_index=4)
            )
        self.assertEqual(context.exception.code, "invalid_gallery_index")

    async def test_gallery_all_preserves_order(self):
        item = media_item(
            media_type="gallery",
            media_url="https://i.redd.it/one.jpg",
            media_urls=["https://i.redd.it/one.jpg", "https://i.redd.it/two.jpg"],
            gallery_items=[
                RedditGalleryItem(index=0, media_id="one", url="https://i.redd.it/one.jpg"),
                RedditGalleryItem(index=1, media_id="two", url="https://i.redd.it/two.jpg"),
            ],
        )
        normalized_media_cache.set(item)
        with patch("backend.services.downloads.resolver.validate_download_url"):
            resolved = await resolve_download_request(DownloadRequest(post_id="abc123", download_scope="gallery_all"))
        self.assertEqual(resolved.urls, ["https://i.redd.it/one.jpg", "https://i.redd.it/two.jpg"])

    async def test_reddit_video_uses_post_url_for_ytdlp(self):
        normalized_media_cache.set(
            media_item(
                media_type="video",
                media_url="https://v.redd.it/abc123/DASH_720.mp4",
                media_urls=["https://v.redd.it/abc123/DASH_720.mp4"],
                reddit_video={"fallback_url": "https://v.redd.it/abc123/DASH_720.mp4"},
                download_strategy="yt_dlp",
            )
        )
        with patch("backend.services.downloads.resolver.validate_download_url"):
            resolved = await resolve_download_request(DownloadRequest(post_id="abc123"))
        self.assertEqual(resolved.strategy, "yt_dlp")
        self.assertIn("/comments/abc123/", resolved.urls[0])

    async def test_unsupported_external_provider_fails_safely(self):
        normalized_media_cache.set(
            media_item(
                media_type="external",
                media_url="https://example.com/watch/1",
                post_url="https://example.com/watch/1",
                download_strategy="yt_dlp",
            )
        )
        with self.assertRaises(MediaResolutionError) as context:
            await resolve_download_request(DownloadRequest(post_id="abc123"))
        self.assertEqual(context.exception.code, "external_media_unsupported")

    async def test_cancel_during_hydration_remains_cancelled(self):
        manager = DownloadJobManager(max_concurrent=1)
        request = DownloadRequest(post_id="abc123")
        hydration_started = asyncio.Event()

        async def slow_hydrate(post_id):
            hydration_started.set()
            await asyncio.sleep(0.05)
            return media_item()

        with patch("backend.services.downloads.resolver.hydrate_submission_media", side_effect=slow_hydrate), patch(
            "backend.services.downloads.resolver.validate_download_url"
        ), patch("backend.services.downloads.manager.download_direct_url") as download:
            job = await manager.create_job(request)
            await hydration_started.wait()
            manager.cancel_job(job.job_id)
            for _ in range(30):
                status = manager.get_status(job.job_id)
                if status.status == "cancelled":
                    break
                await asyncio.sleep(0.01)
        self.assertEqual(manager.get_status(job.job_id).status, "cancelled")
        download.assert_not_called()

    async def test_retry_after_hydration_failure_forces_hydration(self):
        manager = DownloadJobManager(max_concurrent=1)
        old_request = DownloadRequest(post_id="abc123")
        manager.jobs["old"] = DownloadJob(
            job_id="old",
            request=old_request,
            status="failed",
            error="Reddit could not provide full media details for this post.",
            error_code="hydration_failed",
        )
        captured = {}

        async def fake_create_job(download_request):
            captured["request"] = download_request
            return DownloadJob(job_id="new", request=download_request)

        with patch.object(manager, "create_job", side_effect=fake_create_job):
            await manager.retry_job("old")
        self.assertTrue(captured["request"].force_hydrate)


if __name__ == "__main__":
    unittest.main()
