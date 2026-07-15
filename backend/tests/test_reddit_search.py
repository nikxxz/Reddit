import unittest

from backend.services.reddit.media_detector import (
    ALLOWED_MEDIA_TYPES,
    ALLOWED_SORTS,
    ALLOWED_TIME_FILTERS,
)
from backend.services.reddit.search import RedditSearchService
from backend.tests.fixtures.reddit_submissions import direct_image_submission, nsfw_submission, text_submission


class RedditSearchConstantsTests(unittest.TestCase):
    def test_expected_search_values_are_supported(self):
        self.assertIn("image", ALLOWED_MEDIA_TYPES)
        self.assertIn("external", ALLOWED_MEDIA_TYPES)
        self.assertNotIn("comments", ALLOWED_SORTS)
        self.assertIn("all", ALLOWED_TIME_FILTERS)

    def test_search_collection_skips_nsfw_by_default(self):
        service = RedditSearchService()
        items, _, stats = service._collect_media_items(
            [direct_image_submission(), nsfw_submission(), text_submission()],
            "all",
            24,
            False,
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(stats.skipped_nsfw, 1)
        self.assertEqual(stats.skipped_unsupported, 1)

    def test_search_collection_allows_nsfw_when_enabled(self):
        service = RedditSearchService()
        items, _, stats = service._collect_media_items(
            [direct_image_submission(), nsfw_submission()],
            "all",
            24,
            True,
        )
        self.assertEqual(len(items), 2)
        self.assertEqual(stats.skipped_nsfw, 0)


if __name__ == "__main__":
    unittest.main()
