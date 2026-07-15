import unittest

from backend.models.reddit import RedditConnectionStatus


class RedditConnectionModelTests(unittest.TestCase):
    def test_connection_status_is_safe_by_default(self):
        status = RedditConnectionStatus(connected=False)
        self.assertTrue(status.read_only)
        self.assertIsNone(status.authenticated_user)


if __name__ == "__main__":
    unittest.main()
