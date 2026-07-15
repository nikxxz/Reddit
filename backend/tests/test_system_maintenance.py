import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.system import cleanup_stale_part_files


class RepositoryCleanupTests(unittest.TestCase):
    def test_runtime_files_are_ignored(self):
        gitignore = Path(".gitignore").read_text(encoding="utf-8")
        self.assertIn("*.pid", gitignore)
        self.assertIn(".codex-*.pid", gitignore)
        self.assertIn("backend/data/session.json", gitignore)
        self.assertIn("downloads/*", gitignore)
        self.assertIn("!downloads/.gitkeep", gitignore)


class PartialCleanupTests(unittest.TestCase):
    def test_stale_part_file_removed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            part = root / "images" / "stale.jpg.part"
            part.parent.mkdir()
            part.write_bytes(b"partial")
            old = time.time() - 24 * 3600
            os.utime(part, (old, old))
            stats = cleanup_stale_part_files(root=root, max_age_hours=12)
            self.assertEqual(stats["files_removed"], 1)
            self.assertFalse(part.exists())

    def test_recent_part_file_preserved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            part = root / "images" / "recent.jpg.part"
            part.parent.mkdir()
            part.write_bytes(b"partial")
            stats = cleanup_stale_part_files(root=root, max_age_hours=12)
            self.assertEqual(stats["files_removed"], 0)
            self.assertTrue(part.exists())

    def test_completed_media_preserved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            media = root / "images" / "done.jpg"
            media.parent.mkdir()
            media.write_bytes(b"media")
            old = time.time() - 24 * 3600
            os.utime(media, (old, old))
            cleanup_stale_part_files(root=root, max_age_hours=12)
            self.assertTrue(media.exists())

    def test_file_outside_download_root_untouched(self):
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as outside:
            root = Path(tmpdir)
            external = Path(outside) / "external.jpg.part"
            external.write_bytes(b"partial")
            old = time.time() - 24 * 3600
            os.utime(external, (old, old))
            cleanup_stale_part_files(root=root, max_age_hours=12)
            self.assertTrue(external.exists())

    def test_active_job_part_file_preserved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            part = root / "images" / "active.jpg.part"
            part.parent.mkdir()
            part.write_bytes(b"partial")
            old = time.time() - 24 * 3600
            os.utime(part, (old, old))
            stats = cleanup_stale_part_files(
                root=root,
                max_age_hours=12,
                active_part_paths={part},
            )
            self.assertEqual(stats["files_removed"], 0)
            self.assertTrue(part.exists())


class DiagnosticsTests(unittest.TestCase):
    def test_disk_space_checks(self):
        with patch("backend.services.system.disk_free_gb", return_value=3.0), patch(
            "backend.services.system.settings.min_free_disk_gb",
            2,
        ):
            from backend.services.system import has_minimum_free_space

            self.assertTrue(has_minimum_free_space())
        with patch("backend.services.system.disk_free_gb", return_value=1.0), patch(
            "backend.services.system.settings.min_free_disk_gb",
            2,
        ):
            from backend.services.system import has_minimum_free_space

            self.assertFalse(has_minimum_free_space())

    def test_system_status_safe_response(self):
        client = TestClient(app)
        with patch("backend.routes.system.ffmpeg_available", return_value=True), patch(
            "backend.routes.system.yt_dlp_available",
            return_value=True,
        ), patch("backend.routes.system.disk_free_gb", return_value=128.4), patch(
            "backend.routes.system.download_directory_ready",
            return_value=True,
        ), patch(
            "backend.routes.system.download_directory_writable",
            return_value=True,
        ):
            response = client.get("/api/system/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["free_space_gb"], 128.4)
        serialized = str(data)
        self.assertNotIn("REDDIT_CLIENT_SECRET", serialized)
        self.assertNotIn(":\\", serialized)
        self.assertNotIn("/", serialized.replace("ok", ""))

    def test_ffmpeg_and_ytdlp_availability_variants(self):
        with patch("backend.services.system.shutil.which", return_value="ffmpeg"):
            from backend.services.system import ffmpeg_available

            self.assertTrue(ffmpeg_available())
        with patch("backend.services.system.shutil.which", return_value=None):
            from backend.services.system import ffmpeg_available

            self.assertFalse(ffmpeg_available())
        with patch("backend.services.system.importlib.util.find_spec", return_value=object()):
            from backend.services.system import yt_dlp_available

            self.assertTrue(yt_dlp_available())

    def test_unwritable_download_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "missing"
            from backend.services.system import download_directory_writable

            self.assertFalse(download_directory_writable(target))


if __name__ == "__main__":
    unittest.main()
