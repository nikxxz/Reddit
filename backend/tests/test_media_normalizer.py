import unittest

from backend.services.reddit.normalizer import normalize_submission
from backend.tests.fixtures.reddit_submissions import (
    crosspost_submission,
    deleted_author_submission,
    direct_image_submission,
    escaped_preview_submission,
    gallery_submission,
    gif_submission,
    reddit_video_submission,
    text_submission,
    unsupported_submission,
)


class RedditMediaNormalizationTests(unittest.TestCase):
    def test_direct_image(self):
        item = normalize_submission(direct_image_submission())
        self.assertIsNotNone(item)
        self.assertEqual(item.media_type, "image")
        self.assertEqual(item.media_url, "https://i.redd.it/example.jpg")
        self.assertEqual(item.thumbnail_url, "https://i.redd.it/example.jpg")

    def test_reddit_video(self):
        item = normalize_submission(reddit_video_submission())
        self.assertIsNotNone(item)
        self.assertEqual(item.media_type, "video")
        self.assertEqual(item.width, 1280)
        self.assertEqual(item.height, 720)
        self.assertEqual(item.duration, 28)

    def test_gif(self):
        item = normalize_submission(gif_submission())
        self.assertIsNotNone(item)
        self.assertEqual(item.media_type, "gif")

    def test_gallery(self):
        item = normalize_submission(gallery_submission())
        self.assertIsNotNone(item)
        self.assertEqual(item.media_type, "gallery")
        self.assertTrue(item.is_gallery)
        self.assertEqual(item.gallery_count, 2)
        self.assertEqual(item.width, 1920)
        self.assertEqual(item.height, 1080)

    def test_text_only_post_is_skipped(self):
        self.assertIsNone(normalize_submission(text_submission()))

    def test_missing_author(self):
        item = normalize_submission(deleted_author_submission())
        self.assertIsNotNone(item)
        self.assertIsNone(item.author)

    def test_escaped_preview_url(self):
        item = normalize_submission(escaped_preview_submission())
        self.assertIsNotNone(item)
        self.assertEqual(
            item.thumbnail_url,
            "https://preview.redd.it/image.jpg?width=640&crop=smart",
        )

    def test_unsupported_media_is_skipped(self):
        self.assertIsNone(normalize_submission(unsupported_submission()))

    def test_crosspost_media_fallback(self):
        item = normalize_submission(crosspost_submission())
        self.assertIsNotNone(item)
        self.assertEqual(item.id, "crosspost")
        self.assertEqual(item.title, "Crossposted title")
        self.assertEqual(item.media_type, "image")
        self.assertEqual(item.media_url, "https://i.redd.it/parent.jpg")


if __name__ == "__main__":
    unittest.main()
