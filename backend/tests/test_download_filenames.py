import tempfile
import unittest
from pathlib import Path

from backend.services.downloads.filenames import build_download_filename, unique_path


class DownloadFilenameTests(unittest.TestCase):
    def test_standard_title(self):
        filename = build_download_filename(
            subreddit="cosplay",
            author="ExampleUser",
            title="Malenia cosplay",
            post_id="abc123",
            source_url="https://i.redd.it/source.jpg",
        )
        self.assertEqual(filename, "cosplay_exampleuser_malenia_cosplay.jpg")

    def test_deleted_author(self):
        filename = build_download_filename(
            subreddit="pics",
            author="[deleted]",
            title="Image",
            post_id="abc123",
            source_url="https://i.redd.it/source.png",
        )
        self.assertTrue(filename.startswith("pics_deleted_image"))

    def test_invalid_windows_characters(self):
        filename = build_download_filename(
            subreddit="a/b",
            author="user:name",
            title='bad <title> with "chars"?',
            post_id="abc123",
            source_url="https://i.redd.it/source.webp",
        )
        self.assertNotRegex(filename, r'[<>:"/\\|?*]')

    def test_reserved_windows_filename_part(self):
        filename = build_download_filename(
            subreddit="CON",
            author="NUL",
            title="AUX",
            post_id="abc123",
            source_url="https://i.redd.it/source.gif",
        )
        self.assertIn("con_file", filename)
        self.assertIn("nul_file", filename)
        self.assertIn("aux_file", filename)

    def test_gallery_numbering(self):
        filename = build_download_filename(
            subreddit="earthporn",
            author="landscapeuser",
            title="Iceland waterfalls",
            post_id="abc123",
            source_url="https://i.redd.it/source.jpg",
            gallery_index=2,
        )
        self.assertEqual(filename, "earthporn_landscapeuser_iceland_waterfalls_02.jpg")

    def test_duplicate_filename_suffix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            (directory / "cosplay_user_kratos.jpg").write_bytes(b"one")
            path = unique_path(directory, "cosplay_user_kratos.jpg")
        self.assertEqual(path.name, "cosplay_user_kratos_2.jpg")

    def test_long_title_truncation(self):
        filename = build_download_filename(
            subreddit="sub",
            author="user",
            title="x" * 220,
            post_id="abc123",
            source_url="https://i.redd.it/source.jpg",
        )
        self.assertLessEqual(len(Path(filename).stem), 140)

    def test_path_traversal_blocked(self):
        filename = build_download_filename(
            subreddit="../secret",
            author="user",
            title="../../evil",
            post_id="abc123",
            source_url="https://i.redd.it/source.jpg",
        )
        self.assertNotIn("..", filename)
        self.assertNotIn("/", filename)


if __name__ == "__main__":
    unittest.main()
