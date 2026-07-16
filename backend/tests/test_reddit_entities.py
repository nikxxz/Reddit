import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
from prawcore import exceptions as prawcore_exceptions

from backend.api.dependencies import get_reddit_entity_service
from backend.api.errors import (
    PrivateSubredditError,
    RedditEntityNotFoundError,
    RedditSearchError,
    RedditUserSuspendedError,
)
from backend.main import app
from backend.services.reddit.entities import RedditEntityService, TtlCache, normalize_entity_query
from backend.tests.fixtures.reddit_submissions import (
    direct_image_submission,
    gallery_submission,
    gif_submission,
    reddit_video_submission,
    text_submission,
    unsupported_submission,
)


class FakeListing(list):
    def __init__(self, items, after=None):
      super().__init__(items)
      self.params = {"after": after} if after else {}


class FakeSubreddit:
    def __init__(self, name="pics", items=None, over_18=False, subreddit_type="public"):
        self.display_name = name
        self.title = "Pictures"
        self.public_description = "Image community"
        self.icon_img = "https://example.com/icon.png"
        self.subscribers = 1234
        self.over18 = over_18
        self.subreddit_type = subreddit_type
        self.items = items or []
        self.calls = []

    def hot(self, **kwargs):
        self.calls.append(("hot", kwargs))
        return FakeListing(self.items, after="t3_next")

    def new(self, **kwargs):
        self.calls.append(("new", kwargs))
        return FakeListing(self.items, after="t3_next")

    def top(self, **kwargs):
        self.calls.append(("top", kwargs))
        return FakeListing(self.items, after="t3_next")

    def rising(self, **kwargs):
        self.calls.append(("rising", kwargs))
        return FakeListing(self.items, after="t3_next")


class FakeSubreddits:
    def __init__(self, results):
        self.results = results
        self.calls = 0

    def search(self, query, limit=20):
        self.calls += 1
        return self.results[:limit]


class FakeSubmissions:
    def __init__(self, items):
        self.items = items
        self.calls = []

    def new(self, **kwargs):
        self.calls.append(("new", kwargs))
        return FakeListing(self.items, after="t3_user_next")

    def top(self, **kwargs):
        self.calls.append(("top", kwargs))
        return FakeListing(self.items, after="t3_user_next")


class FakeUser:
    def __init__(self, name="example", items=None, suspended=False):
        self.name = name
        self.id = "user-id"
        self.link_karma = 100
        self.comment_karma = 200
        self.is_suspended = suspended
        self.subreddit = SimpleNamespace(display_name=name, icon_img=None, over_18=False)
        self.submissions = FakeSubmissions(items or [])

    def hot(self, **kwargs):
        return FakeListing(self.submissions.items, after="t3_hot_user_next")


class FakeRedditors:
    def __init__(self, results, error=None):
        self.results = results
        self.calls = 0
        self.error = error

    def search(self, query, limit=20):
        if self.error:
            raise self.error
        self.calls += 1
        return self.results[:limit]


class FakeReddit:
    def __init__(self, subreddit=None, users=None, subreddits=None, error=None, redditors_error=None):
        self._subreddit = subreddit or FakeSubreddit()
        self._users = users or {"example": FakeUser()}
        self.subreddits = FakeSubreddits(subreddits or [self._subreddit])
        self.redditors = FakeRedditors(list(self._users.values()), error=redditors_error)
        self.error = error
        self.redditors_error = redditors_error

    def subreddit(self, name):
        if self.error:
            raise self.error
        return self._subreddit

    def redditor(self, name):
        if self.error:
            raise self.error
        return self._users.get(name, FakeUser(name))


class FakeProvider:
    def __init__(self, reddit):
        self.reddit = reddit

    def get_client(self):
        return self.reddit

    def sanitize_error(self, error):
        return "safe"

    def client_context(self):
        return "anonymous", None


class RedditEntityServiceTests(unittest.TestCase):
    def test_prefixes_are_normalized(self):
        self.assertEqual(normalize_entity_query("r/pics"), "pics")
        self.assertEqual(normalize_entity_query("/u/example"), "example")

    def test_entity_search_normalizes_subreddits_and_users(self):
        reddit = FakeReddit()
        service = RedditEntityService(FakeProvider(reddit))
        response = service.search_entities("pics")
        self.assertEqual(response.subreddits[0].name, "pics")
        self.assertEqual(response.users[0].username, "example")

    def test_entity_search_cache_is_used(self):
        reddit = FakeReddit()
        service = RedditEntityService(FakeProvider(reddit))
        service.search_entities("pics")
        service.search_entities("pics")
        self.assertEqual(reddit.subreddits.calls, 1)
        self.assertEqual(reddit.redditors.calls, 1)

    def test_result_limits_are_enforced(self):
        subreddits = [FakeSubreddit(f"sub{i}") for i in range(25)]
        users = {f"user{i}": FakeUser(f"user{i}") for i in range(25)}
        reddit = FakeReddit(users=users, subreddits=subreddits)
        service = RedditEntityService(FakeProvider(reddit))
        response = service.search_entities("wa", limit=20)
        self.assertEqual(len(response.subreddits), 20)
        self.assertEqual(len(response.users), 20)

    def test_subreddit_media_returns_normalized_items_and_excludes_text(self):
        reddit = FakeReddit(subreddit=FakeSubreddit(items=[direct_image_submission(), text_submission()]))
        service = RedditEntityService(FakeProvider(reddit))
        response = service.browse_media(entity_type="subreddit", entity_name="pics", limit=1)
        self.assertEqual(len(response.items), 1)
        self.assertEqual(response.items[0].media_type, "image")
        self.assertTrue(response.has_more)

    def test_media_filters_include_supported_types(self):
        reddit = FakeReddit(
            subreddit=FakeSubreddit(items=[direct_image_submission(), reddit_video_submission(), gif_submission(), gallery_submission()])
        )
        service = RedditEntityService(FakeProvider(reddit))
        self.assertEqual(service.browse_media(entity_type="subreddit", entity_name="pics", media_type="video").items[0].media_type, "video")
        self.assertEqual(service.browse_media(entity_type="subreddit", entity_name="pics", media_type="gif").items[0].media_type, "gif")
        self.assertEqual(service.browse_media(entity_type="subreddit", entity_name="pics", media_type="gallery").items[0].media_type, "gallery")

    def test_nsfw_subreddit_hidden_when_disabled(self):
        reddit = FakeReddit(subreddit=FakeSubreddit(over_18=True, items=[direct_image_submission()]))
        service = RedditEntityService(FakeProvider(reddit))
        response = service.browse_media(entity_type="subreddit", entity_name="pics", include_nsfw=False)
        self.assertEqual(response.items, [])
        self.assertIn("NSFW", response.message)

    def test_user_media_keeps_actual_subreddit(self):
        user = FakeUser(items=[direct_image_submission()])
        reddit = FakeReddit(users={"example": user})
        service = RedditEntityService(FakeProvider(reddit))
        response = service.browse_media(entity_type="user", entity_name="example", sort="new")
        self.assertEqual(response.items[0].subreddit, "pics")

    def test_user_rising_sort_rejected(self):
        service = RedditEntityService(FakeProvider(FakeReddit()))
        with self.assertRaises(ValueError):
            service.browse_media(entity_type="user", entity_name="example", sort="rising")

    def test_user_hot_sort_rejected(self):
        reddit = FakeReddit()
        service = RedditEntityService(FakeProvider(reddit))
        with self.assertRaises(ValueError):
            service.browse_media(entity_type="user", entity_name="example", sort="hot")

    def test_user_new_and_top_use_submissions_listing(self):
        user = FakeUser(items=[direct_image_submission()])
        reddit = FakeReddit(users={"example": user})
        service = RedditEntityService(FakeProvider(reddit))

        service.browse_media(entity_type="user", entity_name="example", sort="new")
        service.browse_media(entity_type="user", entity_name="example", sort="top", time_filter="week")

        self.assertEqual(user.submissions.calls[0][0], "new")
        self.assertEqual(user.submissions.calls[1][0], "top")
        self.assertEqual(user.submissions.calls[1][1]["time_filter"], "week")

    def test_subreddit_hot_and_rising_sorts_are_accepted(self):
        subreddit = FakeSubreddit(items=[direct_image_submission()])
        reddit = FakeReddit(subreddit=subreddit)
        service = RedditEntityService(FakeProvider(reddit))

        service.browse_media(entity_type="subreddit", entity_name="pics", sort="hot")
        service.browse_media(entity_type="subreddit", entity_name="pics", sort="rising")

        self.assertEqual([call[0] for call in subreddit.calls[-2:]], ["hot", "rising"])

    def test_unsupported_links_are_excluded(self):
        reddit = FakeReddit(subreddit=FakeSubreddit(items=[unsupported_submission()]))
        service = RedditEntityService(FakeProvider(reddit))
        response = service.browse_media(entity_type="subreddit", entity_name="pics")
        self.assertEqual(response.items, [])

    def test_suspended_user_handled_safely(self):
        reddit = FakeReddit(users={"gone": FakeUser("gone", suspended=True)})
        service = RedditEntityService(FakeProvider(reddit))
        with self.assertRaises(RedditUserSuspendedError):
            service.browse_media(entity_type="user", entity_name="gone", sort="new")

    def test_missing_subreddit_handled_safely(self):
        reddit = FakeReddit(error=prawcore_exceptions.NotFound(Mock()))
        service = RedditEntityService(FakeProvider(reddit))
        with self.assertRaises(RedditEntityNotFoundError):
            service.browse_media(entity_type="subreddit", entity_name="pics")

    def test_private_subreddit_handled_safely(self):
        reddit = FakeReddit(subreddit=FakeSubreddit(subreddit_type="private"))
        service = RedditEntityService(FakeProvider(reddit))
        with self.assertRaises(PrivateSubredditError):
            service.browse_media(entity_type="subreddit", entity_name="pics")

    def test_upstream_failure_remains_search_error(self):
        reddit = FakeReddit(error=RuntimeError("reddit down"))
        service = RedditEntityService(FakeProvider(reddit))
        with self.assertRaises(RedditSearchError):
            service.browse_media(entity_type="subreddit", entity_name="pics")

    def test_exact_missing_user_returns_no_result(self):
        reddit = FakeReddit(users={})
        reddit.redditor = Mock(side_effect=prawcore_exceptions.NotFound(Mock()))
        service = RedditEntityService(FakeProvider(reddit))
        self.assertIsNone(service._exact_user(reddit, "missing"))

    def test_exact_user_timeout_propagates(self):
        reddit = FakeReddit(users={})
        reddit.redditor = Mock(side_effect=TimeoutError("slow"))
        service = RedditEntityService(FakeProvider(reddit))
        with self.assertRaises(TimeoutError):
            service._exact_user(reddit, "slow")

    def test_exact_user_unexpected_exception_propagates(self):
        reddit = FakeReddit(users={})
        reddit.redditor = Mock(side_effect=AssertionError("bug"))
        service = RedditEntityService(FakeProvider(reddit))
        with self.assertRaises(AssertionError):
            service._exact_user(reddit, "bug")

    def test_exact_match_is_appended_without_duplication(self):
        reddit = FakeReddit(users={"example": FakeUser("example")})
        reddit.redditors = FakeRedditors([])
        service = RedditEntityService(FakeProvider(reddit))
        users = service._search_users(reddit, "example", 20)
        self.assertEqual([user.username for user in users], ["example"])
        reddit.redditors = FakeRedditors([FakeUser("example")])
        users = service._search_users(reddit, "example", 20)
        self.assertEqual([user.username for user in users], ["example"])

    def test_user_search_failure_is_not_silently_empty(self):
        reddit = FakeReddit(redditors_error=RuntimeError("temporary"))
        service = RedditEntityService(FakeProvider(reddit))
        with self.assertRaises(RedditSearchError):
            service.search_entities("example")


class TtlCacheTests(unittest.TestCase):
    def test_cache_returns_stored_value_and_evicts_lru(self):
        cache = TtlCache(ttl_seconds=60, max_size=2)
        cache.set(("a",), 1)
        cache.set(("b",), 2)
        self.assertEqual(cache.get(("a",)), 1)
        cache.set(("c",), 3)
        self.assertIsNone(cache.get(("b",)))
        self.assertEqual(cache.get(("c",)), 3)

    def test_expired_value_is_removed(self):
        cache = TtlCache(ttl_seconds=0, max_size=2)
        cache.set(("a",), 1)
        self.assertIsNone(cache.get(("a",)))

    def test_concurrent_access_is_safe(self):
        cache = TtlCache(ttl_seconds=60, max_size=20)

        def touch(index):
            key = (index % 5,)
            cache.set(key, index)
            return cache.get(key)

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(touch, range(100)))

        self.assertEqual(len(results), 100)


class RedditEntityRouteTests(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.pop(get_reddit_entity_service, None)

    def _client_with_service(self, service):
        app.dependency_overrides[get_reddit_entity_service] = lambda: service
        return TestClient(app)

    def test_route_rejects_invalid_user_sort_with_400(self):
        client = self._client_with_service(RedditEntityService(FakeProvider(FakeReddit())))
        response = client.get("/api/reddit/media?entity_type=user&entity_name=test&sort=hot")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid sort for this entity.")

    def test_route_maps_typed_errors_without_message_inference(self):
        service = Mock()
        service.browse_media.side_effect = RedditEntityNotFoundError("suspended words should not matter")
        client = self._client_with_service(service)
        response = client.get("/api/reddit/media?entity_type=subreddit&entity_name=gone")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "This Reddit community or user does not exist or is unavailable.")

        service.browse_media.side_effect = PrivateSubredditError("private")
        response = client.get("/api/reddit/media?entity_type=subreddit&entity_name=private")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "This subreddit is private.")

        service.browse_media.side_effect = RedditSearchError("does not exist text from upstream")
        response = client.get("/api/reddit/media?entity_type=subreddit&entity_name=boom")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "Reddit media browsing is temporarily unavailable.")


if __name__ == "__main__":
    unittest.main()
