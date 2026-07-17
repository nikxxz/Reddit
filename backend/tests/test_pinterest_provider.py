import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.models.universal_search import ProviderSearchRequest
from backend.services.universal.providers.pinterest import PinterestUniversalProvider
from backend.services.universal.providers.pinterest_models import PinterestExtractorError, PinterestExtractorProbe
from backend.services.universal.providers.pinterest_normalizer import normalize_pinterest_records
from backend.services.universal.providers.pinterest_session import PinterestSessionStore, validate_cookie_bytes
from backend.services.universal.providers.pinterest_urls import (
    normalize_board_url,
    normalize_pin_url,
    normalize_profile_url,
    search_url,
)


COOKIE = b"# Netscape HTTP Cookie File\n.pinterest.com\tTRUE\t/\tTRUE\t1893456000\t_auth\tsecret\n"


class PinterestSessionTests(unittest.TestCase):
    def test_valid_netscape_cookie_file_is_accepted(self):
        text = validate_cookie_bytes(COOKIE)
        self.assertIn("pinterest.com", text)

    def test_binary_oversized_and_non_pinterest_cookies_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "pinterest_cookie_binary"):
            validate_cookie_bytes(b"abc\x00def")
        with self.assertRaisesRegex(ValueError, "pinterest_cookie_oversized"):
            validate_cookie_bytes(b"a" * (2 * 1024 * 1024 + 1))
        with self.assertRaisesRegex(ValueError, "pinterest_cookie_missing_domain"):
            validate_cookie_bytes(b".example.com\tTRUE\t/\tTRUE\t1893456000\ta\tb\n")

    def test_import_and_clear_do_not_return_cookie_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PinterestSessionStore(Path(tmp) / "cookies.txt")
            status = store.import_cookie_bytes(COOKIE)

            self.assertTrue(status.configured)
            self.assertNotIn("secret", str(status))
            self.assertTrue(store.path.exists())
            cleared = store.clear()
            self.assertFalse(cleared.configured)
            self.assertFalse(store.path.exists())


class PinterestUrlTests(unittest.TestCase):
    def test_search_and_supported_url_modes_normalize_safely(self):
        self.assertEqual(search_url("cyberpunk city"), "https://www.pinterest.com/search/pins/?q=cyberpunk%20city")
        self.assertEqual(normalize_pin_url("https://www.pinterest.com/pin/12345/"), "https://www.pinterest.com/pin/12345/")
        self.assertEqual(normalize_profile_url("staff"), "https://www.pinterest.com/staff/")
        self.assertEqual(normalize_board_url("staff/design ideas"), "https://www.pinterest.com/staff/design%20ideas/")

    def test_external_and_non_https_urls_are_rejected(self):
        self.assertIsNone(normalize_pin_url("http://www.pinterest.com/pin/123/"))
        self.assertIsNone(normalize_pin_url("https://example.com/pin/123/"))
        self.assertIsNone(normalize_profile_url("https://example.com/staff"))
        self.assertIsNone(normalize_board_url("only-profile"))


class PinterestNormalizerTests(unittest.TestCase):
    def test_image_video_and_story_records_map_to_universal_items(self):
        records = [
            {
                "id": "1",
                "title": "Image Pin",
                "description": "<p>Nice</p>",
                "creator": "maker",
                "board": "Ideas",
                "images": {
                    "small": {"url": "https://i.pinimg.com/236x/a.jpg", "width": 236, "height": 300},
                    "large": {"url": "https://i.pinimg.com/originals/a.jpg", "width": 1200, "height": 1600},
                },
            },
            {
                "id": "2",
                "description": "Video Pin",
                "video_url": "https://v.pinimg.com/videos/mc/video.mp4",
                "thumbnail_url": "https://i.pinimg.com/736x/poster.jpg",
                "duration": 12,
            },
            {
                "id": "3",
                "story_pages": [
                    {"image_url": "https://i.pinimg.com/originals/one.jpg"},
                    {"video_url": "https://v.pinimg.com/videos/mc/two.mp4", "poster": "https://i.pinimg.com/736x/two.jpg"},
                ],
            },
        ]

        items = normalize_pinterest_records(records, media_types=["image", "video", "gallery"])
        by_id = {item.provider_item_id: item for item in items}

        self.assertEqual(by_id["1"].media_type, "image")
        self.assertEqual(by_id["1"].preview_url, "https://i.pinimg.com/originals/a.jpg")
        self.assertEqual(by_id["1"].description, "Nice")
        self.assertEqual(by_id["2"].media_type, "video")
        self.assertEqual(by_id["2"].duration_seconds, 12)
        self.assertEqual(by_id["3"].media_type, "gallery")
        self.assertEqual(by_id["3"].media_urls[1], "https://v.pinimg.com/videos/mc/two.mp4")
        self.assertFalse(by_id["3"].capabilities.download_single)


class PinterestProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_session_reports_session_required(self):
        provider = PinterestUniversalProvider(FakeExtractor(), FakeSessionStore(configured=False))
        result = await provider.search(ProviderSearchRequest(query="cat", media_types=["image"], limit=5))
        self.assertEqual(result.status, "session_required")

    async def test_search_returns_normalized_results_and_cache(self):
        extractor = FakeExtractor()
        provider = PinterestUniversalProvider(extractor, FakeSessionStore(configured=True))

        request = ProviderSearchRequest(query="cat", media_types=["image"], limit=5)
        first = await provider.search(request)
        second = await provider.search(request)

        self.assertEqual(first.status, "completed")
        self.assertEqual(first.items[0].provider, "pinterest")
        self.assertEqual(extractor.calls, 1)
        self.assertEqual(second.items[0].provider_item_id, "1")

    async def test_extractor_failure_isolated(self):
        provider = PinterestUniversalProvider(FakeExtractor(error=PinterestExtractorError("pinterest_session_required")), FakeSessionStore(configured=True))
        result = await provider.search(ProviderSearchRequest(query="cat", media_types=["image"], limit=5))
        self.assertEqual(result.status, "session_required")


class PinterestApiTests(unittest.TestCase):
    def test_session_upload_rejects_invalid_file_safely(self):
        client = TestClient(app)
        response = client.post(
            "/api/universal/providers/pinterest/session",
            files={"file": ("cookies.txt", b"not\tvalid", "text/plain")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("not\tvalid", response.text)

    def test_provider_endpoint_includes_pinterest_not_planned(self):
        client = TestClient(app)
        response = client.get("/api/universal/providers")

        self.assertEqual(response.status_code, 200)
        pinterest = next(provider for provider in response.json()["providers"] if provider["name"] == "pinterest")
        self.assertEqual(pinterest["implementation_status"], "available")
        instagram = next(provider for provider in response.json()["providers"] if provider["name"] == "instagram")
        self.assertEqual(instagram["implementation_status"], "planned")


class FakeExtractor:
    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    async def probe(self, refresh=False):
        return PinterestExtractorProbe(available=True, version="1.27.7")

    async def extract(self, url, *, limit, cookie_file=None, offset=0):
        self.calls += 1
        if self.error:
            raise self.error
        return [
            {
                "id": "1",
                "title": "Pin",
                "image_url": "https://i.pinimg.com/originals/pin.jpg",
                "creator": "maker",
                "board": "Ideas",
            }
        ]


class FakeSessionStore:
    path = Path("cookies.txt")
    generation = 1

    def __init__(self, configured):
        self.configured = configured

    def status(self):
        return type("Status", (), {"configured": self.configured, "valid": True, "error_code": None})()


if __name__ == "__main__":
    unittest.main()
