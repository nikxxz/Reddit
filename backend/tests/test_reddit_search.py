import unittest

from backend.services.reddit.media_detector import (
    ALLOWED_MEDIA_TYPES,
    ALLOWED_SORTS,
    ALLOWED_TIME_FILTERS,
)


class RedditSearchConstantsTests(unittest.TestCase):
    def test_expected_search_values_are_supported(self):
        self.assertIn("image", ALLOWED_MEDIA_TYPES)
        self.assertIn("comments", ALLOWED_SORTS)
        self.assertIn("all", ALLOWED_TIME_FILTERS)


if __name__ == "__main__":
    unittest.main()
