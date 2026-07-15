import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.models.downloads import DownloadRequest
from backend.services.downloads.gallery import download_gallery_urls
from backend.services.downloads.resolver import resolve_download_request


class GalleryDownloadTests(unittest.TestCase):
    def test_current_item_resolution(self):
        request = DownloadRequest(
            post_id="abc123",
            media_type="gallery",
            subreddit="earthporn",
            author="user",
            title="Waterfalls",
            gallery_urls=[
                "https://i.redd.it/one.jpg",
                "https://i.redd.it/two.jpg",
            ],
            gallery_index=1,
            download_scope="gallery_current",
        )
        with patch("backend.services.downloads.resolver.validate_download_url"):
            resolved = resolve_download_request(request)
        self.assertEqual(resolved.urls, ["https://i.redd.it/two.jpg"])
        self.assertTrue(resolved.filenames[0].endswith("_02.jpg"))

    def test_entire_gallery_resolution(self):
        request = DownloadRequest(
            post_id="abc123",
            media_type="gallery",
            gallery_urls=[
                "https://i.redd.it/one.jpg",
                "https://i.redd.it/two.jpg",
            ],
            download_scope="gallery_all",
        )
        with patch("backend.services.downloads.resolver.validate_download_url"):
            resolved = resolve_download_request(request)
        self.assertEqual(len(resolved.urls), 2)
        self.assertTrue(resolved.filenames[0].endswith("_01.jpg"))
        self.assertTrue(resolved.filenames[1].endswith("_02.jpg"))

    def test_partial_gallery_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            def fake_download(url, output_dir, filename, **kwargs):
                if "two" in url:
                    raise RuntimeError("Media unavailable")
                path = Path(output_dir) / filename
                path.write_bytes(b"ok")
                return path

            with patch("backend.services.downloads.gallery.download_direct_url", side_effect=fake_download):
                completed, failed = download_gallery_urls(
                    urls=["https://i.redd.it/one.jpg", "https://i.redd.it/two.jpg"],
                    output_dir=Path(tmpdir),
                    filenames=["one.jpg", "two.jpg"],
                    max_size_bytes=1024,
                )
        self.assertEqual(len(completed), 1)
        self.assertEqual(len(failed), 1)


if __name__ == "__main__":
    unittest.main()
