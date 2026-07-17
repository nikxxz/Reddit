import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.main import app
from backend.models.reddit import RedditGalleryItem, RedditMediaItem, RedditSearchResponse
from backend.models.universal_search import (
    ProviderCapabilities,
    ProviderHealth,
    ProviderSearchRequest,
    ProviderSearchResult,
    UniversalMediaItem,
    UniversalSearchRequest,
)
from backend.services.universal.coordinator import UniversalSearchCoordinator
from backend.services.universal.errors import DuplicateProviderError, UnknownProviderError
from backend.services.universal.jobs import UniversalSearchJob, UniversalSearchJobManager
from backend.services.universal.providers.reddit_adapter import RedditUniversalProvider
from backend.services.universal.providers.tumblr_placeholder import TumblrPlaceholderProvider
from backend.services.universal.registry import UniversalProviderRegistry


class FakeRedditService:
    def __init__(self, items=None, error=None):
        self.items = items or []
        self.error = error
        self.calls = []
        self.client_provider = self

    def search_media(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return RedditSearchResponse(
            query=kwargs["query"],
            subreddit=kwargs["subreddit"],
            media_type=kwargs["media_type"],
            sort=kwargs["sort"],
            time_filter=kwargs["time_filter"],
            count=len(self.items),
            next_after="t3_next",
            message=None,
            items=self.items,
        )

    def client_context(self):
        return "oauth", "tester"


class FakeProvider:
    display_name = "Fake"
    implementation_status = "available"

    def __init__(self, provider_name, result):
        self.provider_name = provider_name
        self.result = result

    async def search(self, request):
        return self.result

    async def health(self):
        return ProviderHealth(state="ready", authenticated=False)

    def capabilities(self):
        return ProviderCapabilities(keyword_search=True)


def reddit_item(**overrides):
    values = {
        "id": "abc123",
        "title": "Universal cat",
        "subreddit": "wallpapers",
        "author": "poster",
        "created_utc": 1784282400,
        "permalink": "/r/wallpapers/comments/abc123/universal_cat/",
        "post_url": "https://reddit.com/r/wallpapers/comments/abc123/universal_cat/",
        "media_type": "image",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "media_url": "https://example.com/cat.jpg",
        "width": 1920,
        "height": 1080,
        "duration": None,
        "is_gallery": False,
        "gallery_count": 0,
        "is_nsfw": False,
    }
    values.update(overrides)
    return RedditMediaItem(**values)


class UniversalProviderRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_known_providers_registered_and_placeholders_report_not_implemented(self):
        registry = UniversalProviderRegistry()
        registry.register(RedditUniversalProvider(FakeRedditService()))
        registry.register(TumblrPlaceholderProvider())

        summaries = await registry.list_summaries()
        by_name = {summary.name: summary for summary in summaries}

        self.assertIn("reddit", by_name)
        self.assertEqual(by_name["tumblr"].health, "not_implemented")
        self.assertTrue(by_name["reddit"].capabilities.keyword_search)

    def test_duplicate_provider_registration_is_rejected(self):
        registry = UniversalProviderRegistry()
        registry.register(TumblrPlaceholderProvider())
        with self.assertRaises(DuplicateProviderError):
            registry.register(TumblrPlaceholderProvider())

    def test_unknown_provider_is_rejected_safely(self):
        registry = UniversalProviderRegistry()
        with self.assertRaises(UnknownProviderError):
            registry.get("unknown")


class RedditUniversalAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_maps_reddit_image_to_provider_neutral_item(self):
        original = reddit_item()
        provider = RedditUniversalProvider(FakeRedditService([original]))

        result = await provider.search(
            ProviderSearchRequest(
                query="cat",
                media_types=["image", "gif", "video", "gallery"],
                limit=24,
            )
        )

        item = result.items[0]
        self.assertEqual(item.provider, "reddit")
        self.assertEqual(item.provider_item_id, "abc123")
        self.assertEqual(item.collection, "wallpapers")
        self.assertEqual(item.author, "poster")
        self.assertEqual(item.media_type, "image")
        self.assertEqual(item.canonical_url, "https://www.reddit.com/r/wallpapers/comments/abc123/universal_cat/")
        self.assertEqual(item.preview_url, "https://example.com/cat.jpg")
        self.assertFalse(item.nsfw)
        self.assertEqual(original.subreddit, "wallpapers")

    async def test_maps_video_gif_and_gallery(self):
        items = [
            reddit_item(id="video1", media_type="video", media_url="https://v.redd.it/video.mp4", duration=12),
            reddit_item(id="gif1", media_type="gif", media_url="https://example.com/anim.mp4"),
            reddit_item(
                id="gallery1",
                media_type="gallery",
                media_url=None,
                media_urls=[],
                gallery_items=[
                    RedditGalleryItem(index=0, url="https://example.com/one.jpg"),
                    RedditGalleryItem(index=1, url="https://example.com/two.jpg"),
                ],
                gallery_count=2,
                is_gallery=True,
            ),
        ]
        provider = RedditUniversalProvider(FakeRedditService(items))

        result = await provider.search(
            ProviderSearchRequest(query="media", media_types=["video", "gif", "gallery"], limit=24)
        )

        by_id = {item.provider_item_id: item for item in result.items}
        self.assertEqual(by_id["video1"].media_type, "video")
        self.assertEqual(by_id["video1"].duration_seconds, 12)
        self.assertEqual(by_id["gif1"].media_type, "gif")
        self.assertEqual(by_id["gallery1"].media_type, "gallery")
        self.assertEqual(by_id["gallery1"].media_count, 2)
        self.assertEqual(by_id["gallery1"].media_urls, ["https://example.com/one.jpg", "https://example.com/two.jpg"])

    async def test_deleted_author_and_missing_thumbnail_are_safe(self):
        provider = RedditUniversalProvider(
            FakeRedditService([reddit_item(author=None, thumbnail_url=None, is_nsfw=True)])
        )

        result = await provider.search(
            ProviderSearchRequest(query="cat", media_types=["image"], include_nsfw=True, limit=24)
        )

        self.assertIsNone(result.items[0].author)
        self.assertIsNone(result.items[0].thumbnail_url)
        self.assertTrue(result.items[0].nsfw)

    async def test_adapter_uses_existing_service_directly(self):
        service = FakeRedditService([reddit_item()])
        provider = RedditUniversalProvider(service)

        await provider.search(ProviderSearchRequest(query="cat", media_types=["image"], limit=24))

        self.assertEqual(len(service.calls), 1)
        self.assertEqual(service.calls[0]["query"], "cat")
        self.assertEqual(service.calls[0]["media_type"], "image")


class UniversalCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_reddit_success_plus_placeholder_yields_completed_with_errors(self):
        registry = UniversalProviderRegistry()
        registry.register(
            FakeProvider(
                "reddit",
                ProviderSearchResult(
                    provider="reddit",
                    status="completed",
                    items=[universal_item("reddit", "1"), universal_item("reddit", "2")],
                ),
            )
        )
        registry.register(TumblrPlaceholderProvider())
        coordinator = UniversalSearchCoordinator(registry)

        status, providers, items = await coordinator.search(
            "search-1",
            UniversalSearchRequest(query="cat", providers=["reddit", "tumblr"], media_types=["image"]),
        )

        self.assertEqual(status, "completed_with_errors")
        self.assertEqual(providers["reddit"].status, "completed")
        self.assertEqual(providers["tumblr"].status, "not_implemented")
        self.assertEqual([item.provider_item_id for item in items], ["1", "2"])

    async def test_no_implemented_provider_available_fails_safely(self):
        registry = UniversalProviderRegistry()
        registry.register(TumblrPlaceholderProvider())
        coordinator = UniversalSearchCoordinator(registry)

        status, providers, items = await coordinator.search(
            "search-2",
            UniversalSearchRequest(query="cat", providers=["tumblr"], media_types=["image"]),
        )

        self.assertEqual(status, "failed")
        self.assertEqual(providers["tumblr"].status, "not_implemented")
        self.assertEqual(items, [])

    def test_source_balanced_and_grouped_merge_keep_provider_ids_distinct(self):
        coordinator = UniversalSearchCoordinator(UniversalProviderRegistry())
        provider_items = {
            "reddit": [universal_item("reddit", "same"), universal_item("reddit", "r2")],
            "tumblr": [universal_item("tumblr", "same")],
        }

        balanced = coordinator.merge_results(provider_items, "source_balanced")
        grouped = coordinator.merge_results(provider_items, "grouped")

        self.assertEqual([item.provider for item in balanced], ["reddit", "tumblr", "reddit"])
        self.assertEqual([f"{item.provider}:{item.provider_item_id}" for item in grouped], ["reddit:same", "reddit:r2", "tumblr:same"])

    def test_stale_terminal_jobs_are_cleaned_and_active_jobs_are_kept(self):
        manager = UniversalSearchJobManager()
        old = UniversalSearchJob(
            search_id="old",
            request=UniversalSearchRequest(query="cat", providers=["tumblr"], media_types=["image"]),
            status="completed",
        )
        old.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        active = UniversalSearchJob(
            search_id="active",
            request=UniversalSearchRequest(query="dog", providers=["tumblr"], media_types=["image"]),
            status="searching",
        )
        active.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        manager._jobs = {"old": old, "active": active}

        removed = manager.cleanup_jobs()

        self.assertEqual(removed, 1)
        self.assertNotIn("old", manager._jobs)
        self.assertIn("active", manager._jobs)


class UniversalSearchApiTests(unittest.TestCase):
    def test_provider_list_endpoint_works(self):
        client = TestClient(app)
        response = client.get("/api/universal/providers")

        self.assertEqual(response.status_code, 200)
        names = {provider["name"] for provider in response.json()["providers"]}
        self.assertEqual(names, {"reddit", "tumblr", "pinterest", "instagram"})

    def test_placeholder_search_request_creates_job_without_live_reddit(self):
        client = TestClient(app)
        response = client.post(
            "/api/universal/search",
            json={
                "query": "cat",
                "providers": ["tumblr"],
                "media_types": ["image"],
                "limit_per_provider": 5,
            },
        )

        self.assertEqual(response.status_code, 200)
        search_id = response.json()["search_id"]
        status_response = client.get(f"/api/universal/search/{search_id}")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["items"], [])

    def test_invalid_request_values_are_rejected(self):
        client = TestClient(app)

        blank = client.post(
            "/api/universal/search",
            json={"query": " ", "providers": ["reddit"], "media_types": ["image"]},
        )
        invalid_media = client.post(
            "/api/universal/search",
            json={"query": "cat", "providers": ["reddit"], "media_types": ["bad"]},
        )
        excessive_limit = client.post(
            "/api/universal/search",
            json={"query": "cat", "providers": ["reddit"], "media_types": ["image"], "limit_per_provider": 101},
        )

        self.assertEqual(blank.status_code, 422)
        self.assertEqual(invalid_media.status_code, 422)
        self.assertEqual(excessive_limit.status_code, 422)


def universal_item(provider, item_id):
    return UniversalMediaItem(
        provider=provider,
        provider_item_id=item_id,
        title=f"{provider} {item_id}",
        media_type="image",
        preview_url=f"https://example.com/{provider}/{item_id}.jpg",
    )


if __name__ == "__main__":
    unittest.main()

