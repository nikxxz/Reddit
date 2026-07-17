import unittest
from unittest.mock import patch

import httpx

from backend.models.downloads import DownloadRequest
from backend.models.universal_search import ProviderSearchRequest
from backend.services.library.duplicates import duplicate_for_request
from backend.services.universal.providers.tumblr import TumblrUniversalProvider, normalize_blog_identifier
from backend.services.universal.providers.tumblr_client import TumblrApiError, TumblrClient
from backend.services.universal.providers.tumblr_models import TumblrTaggedResponse
from backend.services.universal.providers.tumblr_normalizer import normalize_tumblr_post


class TumblrNormalizerTests(unittest.TestCase):
    def test_npf_single_image_maps_to_downloadable_item(self):
        item = normalize_tumblr_post(
            {
                "id": 123,
                "id_string": "123",
                "blog_name": "staff",
                "post_url": "https://staff.tumblr.com/post/123/example",
                "summary": "Example",
                "timestamp": 1784282400,
                "content": [
                    {
                        "type": "image",
                        "media": [
                            {"url": "https://64.media.tumblr.com/small.jpg", "width": 320, "height": 180},
                            {"url": "https://64.media.tumblr.com/large.jpg", "width": 1280, "height": 720},
                        ],
                    }
                ],
            }
        )

        self.assertIsNotNone(item)
        self.assertEqual(item.provider, "tumblr")
        self.assertEqual(item.media_type, "image")
        self.assertEqual(item.preview_url, "https://64.media.tumblr.com/large.jpg")
        self.assertTrue(item.capabilities.download_single)

    def test_npf_mixed_media_becomes_gallery_and_html_caption_is_plain(self):
        item = normalize_tumblr_post(
            {
                "id_string": "456",
                "blog_name": "art",
                "post_url": "https://art.tumblr.com/post/456/mixed",
                "caption": "<p>Hello <b>world</b></p>",
                "content": [
                    {"type": "text", "text": "Mixed post"},
                    {"type": "image", "media": [{"url": "https://64.media.tumblr.com/a.gif", "width": 500, "height": 500, "type": "image/gif"}]},
                    {"type": "video", "media": {"url": "https://va.media.tumblr.com/video.mp4", "width": 640, "height": 360, "duration": 4}},
                ],
            }
        )

        self.assertEqual(item.media_type, "gallery")
        self.assertEqual(item.media_count, 2)
        self.assertEqual(item.description, "Hello  world")
        self.assertEqual(item.media_urls[0], "https://64.media.tumblr.com/a.gif")
        self.assertEqual(item.source_metadata["assets"][0]["index"], 0)
        self.assertEqual(item.source_metadata["assets"][1]["index"], 1)

    def test_legacy_photoset_and_external_video_degrade_safely(self):
        photoset = normalize_tumblr_post(
            {
                "id_string": "789",
                "blog_name": "photos",
                "post_url": "https://photos.tumblr.com/post/789/set",
                "photos": [
                    {"original_size": {"url": "https://64.media.tumblr.com/one.jpg", "width": 900, "height": 600}},
                    {"original_size": {"url": "https://64.media.tumblr.com/two.jpg", "width": 900, "height": 600}},
                ],
            }
        )
        video = normalize_tumblr_post(
            {
                "id_string": "999",
                "blog_name": "videos",
                "post_url": "https://videos.tumblr.com/post/999/video",
                "type": "video",
                "video_url": "https://example.com/watch/1",
                "thumbnail_url": "https://64.media.tumblr.com/poster.jpg",
            }
        )

        self.assertEqual(photoset.media_type, "gallery")
        self.assertTrue(photoset.capabilities.download_all)
        self.assertEqual(video.media_type, "video")
        self.assertFalse(video.capabilities.download_single)


class TumblrProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_key_reports_configuration_required(self):
        with patch("backend.services.universal.providers.tumblr.settings.tumblr_consumer_key", None):
            provider = TumblrUniversalProvider()

            health = await provider.health()

            self.assertEqual(provider.implementation_status, "configuration_required")
            self.assertEqual(health.state, "unavailable")

    async def test_tag_search_uses_client_and_cache(self):
        client = FakeTumblrClient()
        provider = TumblrUniversalProvider(client)
        request = ProviderSearchRequest(query="digital art", media_types=["image"], limit=10)

        first = await provider.search(request)
        second = await provider.search(request)

        self.assertEqual(first.status, "completed")
        self.assertEqual(first.items[0].provider, "tumblr")
        self.assertEqual(client.calls, 1)
        self.assertEqual(second.items[0].provider_item_id, "123")

    async def test_rate_limit_maps_safely(self):
        client = FakeTumblrClient(error=TumblrApiError("tumblr_rate_limited", "limited", status_code=429, retry_after_seconds=120))
        provider = TumblrUniversalProvider(client)

        result = await provider.search(ProviderSearchRequest(query="art", media_types=["image"], limit=10))

        self.assertEqual(result.status, "rate_limited")
        self.assertEqual(result.error_code, "tumblr_rate_limited")

    def test_blog_identifier_normalization(self):
        self.assertEqual(normalize_blog_identifier("staff"), "staff.tumblr.com")
        self.assertEqual(normalize_blog_identifier("https://www.tumblr.com/staff"), "staff.tumblr.com")
        self.assertIsNone(normalize_blog_identifier("https://example.com/staff"))


class TumblrClientTests(unittest.TestCase):
    def test_response_envelope_is_parsed_and_errors_are_mapped(self):
        client = TumblrClient(consumer_key="key")
        ok = client._response_payload({"meta": {"status": 200}, "response": [{"id": 1}]}, 200)
        self.assertEqual(ok, [{"id": 1}])

        with self.assertRaises(TumblrApiError) as error:
            client._response_payload({"meta": {"status": 401}, "response": {}}, 200)
        self.assertEqual(error.exception.code, "tumblr_unauthorized")

    def test_rate_limit_header_is_safe(self):
        client = TumblrClient(consumer_key="key")
        client._capture_rate_limit(httpx.Headers({"Retry-After": "45"}))

        self.assertFalse(client.rate_limit.limited)
        self.assertEqual(client.rate_limit.retry_after_seconds, 45)


class ProviderAwareDuplicateTests(unittest.TestCase):
    def test_duplicate_request_includes_provider(self):
        request = DownloadRequest(
            provider="tumblr",
            post_id="123",
            media_type="image",
            download_scope="single",
        )

        # The repository is exercised in persistence tests; this verifies the
        # provider-aware request shape reaches duplicate lookup safely.
        self.assertIsNone(duplicate_for_request(request))


class FakeTumblrClient:
    consumer_key = "fake"

    def __init__(self, error=None):
        self.calls = 0
        self.error = error
        self.rate_limit = type("RateLimit", (), {"limited": False, "retry_after_seconds": None})()

    async def get_tagged_posts(self, tag, *, before=None, limit=20):
        self.calls += 1
        if self.error:
            raise self.error
        return TumblrTaggedResponse(
            posts=[
                {
                    "id_string": "123",
                    "blog_name": "staff",
                    "post_url": "https://staff.tumblr.com/post/123/example",
                    "summary": tag,
                    "content": [
                        {
                            "type": "image",
                            "media": [{"url": "https://64.media.tumblr.com/image.jpg", "width": 800, "height": 600}],
                        }
                    ],
                }
            ],
            next_before=123,
        )

    async def get_blog_posts(self, *args, **kwargs):
        return await self.get_tagged_posts("blog")


if __name__ == "__main__":
    unittest.main()
