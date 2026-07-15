import unittest
from pathlib import Path

from backend.routes.reddit import search_reddit_media, validate_search_params
from backend.models.reddit import RedditSearchResponse
from backend.services.reddit.media_detector import (
    ALLOWED_MEDIA_TYPES,
    ALLOWED_SORTS,
    ALLOWED_TIME_FILTERS,
    normalize_subreddit_input,
)
from backend.services.reddit.search import RedditSearchService
from backend.tests.fixtures.reddit_submissions import direct_image_submission, nsfw_submission, text_submission


class FakeTarget:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append(("search", query, kwargs))
        return []

    def hot(self, **kwargs):
        self.calls.append(("hot", None, kwargs))
        return []

    def new(self, **kwargs):
        self.calls.append(("new", None, kwargs))
        return []

    def top(self, **kwargs):
        self.calls.append(("top", None, kwargs))
        return []


class FakeReddit:
    def __init__(self):
        self.targets = {}
        self.requested_subreddits = []

    def subreddit(self, name):
        self.requested_subreddits.append(name)
        self.targets.setdefault(name, FakeTarget(name))
        return self.targets[name]


class FakeProvider:
    def __init__(self):
        self.reddit = FakeReddit()

    def get_client(self):
        return self.reddit

    def sanitize_error(self, error):
        return str(error)

    def client_context(self):
        return "anonymous", None


class FakeRouteService:
    def __init__(self):
        self.kwargs = None

    def search_media(self, **kwargs):
        self.kwargs = kwargs
        return RedditSearchResponse(
            query=kwargs["query"],
            subreddit=kwargs["subreddit"],
            media_type=kwargs["media_type"],
            sort=kwargs["sort"],
            time_filter=kwargs["time_filter"],
            count=0,
            next_after=None,
            message=None,
            items=[],
        )


class RedditSearchConstantsTests(unittest.TestCase):
    def test_expected_search_values_are_supported(self):
        self.assertIn("image", ALLOWED_MEDIA_TYPES)
        self.assertIn("external", ALLOWED_MEDIA_TYPES)
        self.assertIn("comments", ALLOWED_SORTS)
        self.assertIn("all", ALLOWED_TIME_FILTERS)

    def test_subreddit_input_normalization(self):
        self.assertEqual(normalize_subreddit_input("r/ExampleSubreddit"), "ExampleSubreddit")
        self.assertEqual(normalize_subreddit_input("/r/ExampleSubreddit/"), "ExampleSubreddit")
        self.assertEqual(
            normalize_subreddit_input("https://www.reddit.com/r/ExampleSubreddit/"),
            "ExampleSubreddit",
        )

    def test_invalid_subreddit_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_subreddit_input("bad/name")

    def test_search_collection_skips_nsfw_by_default(self):
        service = RedditSearchService()
        items, _, stats = service._collect_media_items(
            [direct_image_submission(), nsfw_submission(), text_submission()],
            "all",
            24,
            False,
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(stats.skipped_nsfw, 1)
        self.assertEqual(stats.skipped_text_only, 1)

    def test_search_collection_allows_nsfw_when_enabled(self):
        service = RedditSearchService()
        items, _, stats = service._collect_media_items(
            [direct_image_submission(), nsfw_submission()],
            "all",
            24,
            True,
        )
        self.assertEqual(len(items), 2)
        self.assertEqual(stats.skipped_nsfw, 0)

    def test_query_with_subreddit_uses_named_subreddit(self):
        provider = FakeProvider()
        service = RedditSearchService(provider)
        service._search_listing(
            query="Kratos",
            subreddit="CosplaySub",
            sort="relevance",
            time_filter="all",
            limit=24,
            after=None,
        )
        self.assertEqual(provider.reddit.requested_subreddits, ["CosplaySub"])
        target = provider.reddit.targets["CosplaySub"]
        self.assertEqual(target.calls[0][0], "search")

    def test_query_without_subreddit_uses_all(self):
        provider = FakeProvider()
        service = RedditSearchService(provider)
        service._search_listing(
            query="Kratos",
            subreddit=None,
            sort="relevance",
            time_filter="all",
            limit=24,
            after=None,
        )
        self.assertEqual(provider.reddit.requested_subreddits, ["all"])

    def test_subreddit_only_new_uses_new_listing(self):
        provider = FakeProvider()
        service = RedditSearchService(provider)
        service._search_listing("", "wallpapers", "new", "all", 24, None)
        self.assertEqual(provider.reddit.targets["wallpapers"].calls[0][0], "new")

    def test_subreddit_only_hot_uses_hot_listing(self):
        provider = FakeProvider()
        service = RedditSearchService(provider)
        service._search_listing("", "wallpapers", "hot", "all", 24, None)
        self.assertEqual(provider.reddit.targets["wallpapers"].calls[0][0], "hot")

    def test_subreddit_only_top_uses_top_listing(self):
        provider = FakeProvider()
        service = RedditSearchService(provider)
        service._search_listing("", "wallpapers", "top", "year", 24, None)
        method, _, kwargs = provider.reddit.targets["wallpapers"].calls[0]
        self.assertEqual(method, "top")
        self.assertEqual(kwargs["time_filter"], "year")

    def test_subreddit_only_relevance_falls_back_to_hot(self):
        provider = FakeProvider()
        service = RedditSearchService(provider)
        service._search_listing("", "wallpapers", "relevance", "all", 24, None)
        self.assertEqual(provider.reddit.targets["wallpapers"].calls[0][0], "hot")

    def test_subreddit_only_comments_falls_back_to_new(self):
        provider = FakeProvider()
        service = RedditSearchService(provider)
        service._search_listing("", "wallpapers", "comments", "all", 24, None)
        self.assertEqual(provider.reddit.targets["wallpapers"].calls[0][0], "new")

    def test_search_service_passes_query_sort_time_filter_syntax_and_limit(self):
        provider = FakeProvider()
        service = RedditSearchService(provider)
        service._search_listing(
            query="Kratos",
            subreddit="CosplaySub",
            sort="top",
            time_filter="year",
            limit=24,
            after=None,
        )
        _, query, kwargs = provider.reddit.targets["CosplaySub"].calls[0]
        self.assertEqual(query, "Kratos")
        self.assertEqual(kwargs["sort"], "top")
        self.assertEqual(kwargs["time_filter"], "year")
        self.assertEqual(kwargs["syntax"], "lucene")
        self.assertEqual(kwargs["limit"], 72)

    def test_invalid_route_subreddit_does_not_fall_back_to_all(self):
        with self.assertRaises(Exception):
            validate_search_params("Kratos", "bad/name", "all", "relevance", "all", 24)

    def test_route_forwards_subreddit_parameter(self):
        service = FakeRouteService()
        response = search_reddit_media(
            q="Kratos",
            subreddit="r/CosplaySub",
            media_type="all",
            sort="relevance",
            time_filter="all",
            limit=24,
            after=None,
            include_nsfw=False,
            service=service,
        )
        self.assertEqual(service.kwargs["subreddit"], "CosplaySub")
        self.assertEqual(response.subreddit, "CosplaySub")

    def test_subreddit_only_request_applies_image_filter_and_nsfw_filter(self):
        service = RedditSearchService()
        items, _, stats = service._collect_media_items(
            [direct_image_submission(), nsfw_submission(), text_submission()],
            "image",
            24,
            False,
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].media_type, "image")
        self.assertEqual(stats.skipped_nsfw, 1)
        self.assertEqual(stats.skipped_text_only, 1)

    def test_frontend_sends_subreddit_parameter(self):
        source = Path("legacy/frontend/js/api/redditApi.js").read_text()
        self.assertIn('searchParams.set("subreddit", params.subreddit)', source)

    def test_raw_match_with_direct_image_survives_without_dimensions(self):
        service = RedditSearchService()
        items, _, stats = service._collect_media_items(
            [direct_image_submission()],
            "all",
            24,
            False,
        )
        self.assertEqual(len(items), 1)
        self.assertIsNone(items[0].width)
        self.assertIsNone(items[0].height)
        self.assertEqual(stats.media_detected, 1)


if __name__ == "__main__":
    unittest.main()
