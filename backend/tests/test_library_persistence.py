import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.config import settings
from backend.core.paths import (
    PathSafetyError,
    get_database_path,
    resolve_download_path,
    to_relative_download_path,
)
from backend.database import migrations
from backend.database.connection import connect
from backend.database.repositories import downloads as downloads_repo
from backend.models.downloads import DownloadRequest
from backend.services.library.reconciliation import reconcile_library
from backend.services.library.thumbnails import dummy_thumbnail_response, thumbnail_response


class LibraryPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [
            patch.object(settings, "app_data_dir", str(self.root / "app-data")),
            patch.object(settings, "download_dir", str(self.root / "downloads")),
            patch.object(settings, "database_filename", "reddit_media_library.sqlite3"),
            patch.object(settings, "generate_missing_thumbnails_on_startup", False),
        ]
        for patcher in self.patches:
            patcher.start()
        downloads_repo._schema_ready = False

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        downloads_repo._schema_ready = False
        self.tmp.cleanup()

    def test_database_created_with_migration_and_pragmas(self):
        migrations.initialize_database()
        self.assertTrue(get_database_path().exists())
        self.assertEqual(migrations.get_schema_version(), 1)
        with connect() as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")

    def test_relative_paths_persist_and_absolute_escape_rejected(self):
        download_root = Path(settings.download_dir)
        media = download_root / "images" / "example.jpg"
        media.parent.mkdir(parents=True, exist_ok=True)
        media.write_bytes(b"image")
        relative = to_relative_download_path(media)
        self.assertEqual(relative, "images/example.jpg")
        self.assertEqual(resolve_download_path(relative), media.resolve())
        with self.assertRaises(PathSafetyError):
            resolve_download_path("../outside.jpg")

    def test_job_file_reconciliation_and_duplicate_detection(self):
        migrations.initialize_database()
        media = Path(settings.download_dir) / "images" / "example.jpg"
        media.parent.mkdir(parents=True, exist_ok=True)
        media.write_bytes(b"image")
        download_id = downloads_repo.create_download_record(
            job_id="job-1",
            post_id="abc123",
            title="Example",
            subreddit="pics",
            author="user",
            media_type="image",
            download_scope="single",
            status="completed",
        )
        downloads_repo.add_file_record(job_id="job-1", path=media, category="images")
        downloads_repo.update_download_status("job-1", "completed", expected_file_count=1)
        self.assertEqual(downloads_repo.update_availability(download_id), "available")
        duplicate = downloads_repo.find_duplicate("abc123", "image", "single", None)
        self.assertIsNotNone(duplicate)
        media.unlink()
        stats = reconcile_library()
        self.assertEqual(stats["files_missing"], 1)
        row = downloads_repo.list_downloads(status_filter="completed")[0]
        self.assertEqual(row["availability"], "missing")

    def test_interrupted_jobs_mark_failed(self):
        migrations.initialize_database()
        downloads_repo.create_download_record(
            job_id="job-2",
            post_id="def456",
            title=None,
            subreddit=None,
            author=None,
            media_type="video",
            download_scope="single",
            status="downloading",
        )
        self.assertEqual(downloads_repo.mark_interrupted_jobs(), 1)
        row = downloads_repo.list_downloads(status_filter="failed")[0]
        self.assertEqual(row["error_code"], "interrupted_by_restart")

    def test_thumbnail_dummy_response_and_endpoint_fallback(self):
        migrations.initialize_database()
        download_id = downloads_repo.create_download_record(
            job_id="job-3",
            post_id="ghi789",
            title=None,
            subreddit=None,
            author=None,
            media_type="image",
            download_scope="single",
            status="completed",
        )
        downloads_repo.set_thumbnail(
            download_id=download_id,
            source_file_id=None,
            relative_path=None,
            source_type="dummy",
            exists_on_disk=False,
        )
        self.assertEqual(dummy_thumbnail_response().media_type, "image/svg+xml")
        self.assertEqual(thumbnail_response(download_id).media_type, "image/svg+xml")

    def test_pre_migration_backup_created_for_existing_schema(self):
        database = get_database_path()
        database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database)
        try:
            connection.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, name TEXT, applied_at TEXT)")
            connection.commit()
        finally:
            connection.close()
        migrations.initialize_database()
        backups = list((Path(settings.app_data_dir) / "backups").glob("reddit_media_library_pre_migration_v0_*.sqlite3"))
        self.assertTrue(backups)


if __name__ == "__main__":
    unittest.main()
