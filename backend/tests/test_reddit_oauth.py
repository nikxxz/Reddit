import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from backend.services.reddit.oauth import RedditOAuthManager
from backend.services.reddit.session import RedditSessionData, RedditSessionStore


class RedditSessionStoreTests(unittest.TestCase):
    def test_session_store_saves_refresh_token_and_username(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "session.json"
            store = RedditSessionStore(path)
            store.save(RedditSessionData(refresh_token="refresh", username="tester"))

            loaded = store.load()
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.refresh_token, "refresh")
            self.assertEqual(loaded.username, "tester")
            self.assertNotIn("access_token", path.read_text(encoding="utf-8"))

    def test_session_store_delete_removes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "session.json"
            store = RedditSessionStore(path)
            store.save(RedditSessionData(refresh_token="refresh", username="tester"))
            store.delete()
            self.assertFalse(path.exists())


class RedditOAuthManagerTests(unittest.TestCase):
    def test_state_can_only_be_consumed_once(self):
        manager = RedditOAuthManager(RedditSessionStore(Path("unused.json")))
        manager._states["state"] = 9999999999
        self.assertTrue(manager._consume_state("state"))
        self.assertFalse(manager._consume_state("state"))

    def test_logout_clears_cached_client_and_session(self):
        store = Mock()
        manager = RedditOAuthManager(store)
        manager._authenticated_client = object()
        manager._username = "tester"

        manager.logout()

        self.assertIsNone(manager.get_authenticated_client())
        self.assertIsNone(manager.username)
        store.delete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
