import unittest

from backend.services.reddit.normalizer import normalize_submission
from backend.tests.fixtures.reddit_submissions import (
    avif_image_submission,
    crosspost_submission,
    deleted_author_submission,
    direct_video_submission,
    direct_image_submission,
    escaped_preview_submission,
    external_submission,
    gallery_submission,
    gif_submission,
    nsfw_submission,
    poll_submission,
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
        self.assertEqual(item.media_urls, ["https://i.redd.it/example.jpg"])
        self.assertEqual(item.download_strategy, "direct")

    def test_avif_image(self):
        item = normalize_submission(avif_image_submission())
        self.assertIsNotNone(item)
        self.assertEqual(item.media_type, "image")

    def test_reddit_video(self):
        item = normalize_submission(reddit_video_submission())
        self.assertIsNotNone(item)
        self.assertEqual(item.media_type, "video")
        self.assertEqual(item.width, 1280)
        self.assertEqual(item.height, 720)
        self.assertEqual(item.duration, 28)
        self.assertEqual(item.download_strategy, "yt_dlp")

    def test_direct_video(self):
        item = normalize_submission(direct_video_submission())
        self.assertIsNotNone(item)
        self.assertEqual(item.media_type, "video")
        self.assertEqual(item.download_strategy, "direct")

    def test_gif(self):
        item = normalize_submission(gif_submission())
        self.assertIsNotNone(item)
        self.assertEqual(item.media_type, "gif")
        self.assertEqual(item.download_strategy, "direct")

    def test_gallery(self):
        item = normalize_submission(gallery_submission())
        self.assertIsNotNone(item)
        self.assertEqual(item.media_type, "gallery")
        self.assertTrue(item.is_gallery)
        self.assertEqual(item.gallery_count, 2)
        self.assertEqual(item.width, 1920)
        self.assertEqual(item.height, 1080)
        self.assertEqual(item.download_strategy, "direct")

    def test_external_media_link(self):
        item = normalize_submission(external_submission())
        self.assertIsNotNone(item)
        self.assertEqual(item.media_type, "external")
        self.assertEqual(item.download_strategy, "yt_dlp")

    def test_text_only_post_is_skipped(self):
        self.assertIsNone(normalize_submission(text_submission()))

    def test_poll_is_skipped(self):
        self.assertIsNone(normalize_submission(poll_submission()))

    def test_nsfw_flag_is_preserved(self):
        item = normalize_submission(nsfw_submission())
        self.assertIsNotNone(item)
        self.assertTrue(item.is_nsfw)

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

    def test_normalization_uses_only_loaded_fields(self):
        class LazySubmission:
            def __init__(self):
                self.id = "lazy"
                self.title = "Loaded image"
                self.subreddit = "pics"
                self.author = "tester"
                self.created_utc = 1712345678
                self.permalink = "/r/pics/comments/lazy/title/"
                self.url = "https://i.redd.it/lazy.jpg"
                self.over_18 = False
                self.is_video = False
                self.is_gallery = False

            def __getattr__(self, name):
                if name in {"comments", "preview", "media_metadata", "gallery_data", "secure_media"}:
                    raise AssertionError(f"lazy field accessed: {name}")
                raise AttributeError(name)

        item = normalize_submission(LazySubmission())
        self.assertIsNotNone(item)
        self.assertEqual(item.id, "lazy")


if __name__ == "__main__":
    unittest.main()
