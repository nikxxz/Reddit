import unittest
from types import SimpleNamespace

from backend.api.errors import InvalidSubredditError, RedditSearchError
from backend.services.reddit.entities import RedditEntityService, normalize_entity_query
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
    def __init__(self, name="pics", items=None, over_18=False):
        self.display_name = name
        self.title = "Pictures"
        self.public_description = "Image community"
        self.icon_img = "https://example.com/icon.png"
        self.subscribers = 1234
        self.over18 = over_18
        self.subreddit_type = "public"
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
    def __init__(self, results):
        self.results = results
        self.calls = 0

    def search(self, query, limit=20):
        self.calls += 1
        return self.results[:limit]


class FakeReddit:
    def __init__(self, subreddit=None, users=None, subreddits=None, error=None):
        self._subreddit = subreddit or FakeSubreddit()
        self._users = users or {"example": FakeUser()}
        self.subreddits = FakeSubreddits(subreddits or [self._subreddit])
        self.redditors = FakeRedditors(list(self._users.values()))
        self.error = error

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

    def test_unsupported_links_are_excluded(self):
        reddit = FakeReddit(subreddit=FakeSubreddit(items=[unsupported_submission()]))
        service = RedditEntityService(FakeProvider(reddit))
        response = service.browse_media(entity_type="subreddit", entity_name="pics")
        self.assertEqual(response.items, [])

    def test_suspended_user_handled_safely(self):
        reddit = FakeReddit(users={"gone": FakeUser("gone", suspended=True)})
        service = RedditEntityService(FakeProvider(reddit))
        with self.assertRaises(RedditSearchError):
            service.browse_media(entity_type="user", entity_name="gone", sort="new")

    def test_missing_subreddit_handled_safely(self):
        reddit = FakeReddit(error=RuntimeError("boom"))
        service = RedditEntityService(FakeProvider(reddit))
        with self.assertRaises(RedditSearchError):
            service.browse_media(entity_type="subreddit", entity_name="pics")


if __name__ == "__main__":
    unittest.main()
