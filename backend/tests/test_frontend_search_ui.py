import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_frontend(path: str) -> str:
    return (ROOT / "frontend" / path).read_text(encoding="utf-8")


class FrontendSearchUiSourceTests(unittest.TestCase):
    def test_search_status_constants_exist(self):
        source = read_frontend("js/state.js")
        self.assertIn('IDLE: "idle"', source)
        self.assertIn('LOADING: "loading"', source)
        self.assertIn('SUCCESS: "success"', source)
        self.assertIn('EMPTY: "empty"', source)
        self.assertIn('ERROR: "error"', source)

    def test_search_request_does_not_send_empty_q(self):
        source = read_frontend("js/api/redditApi.js")
        self.assertIn("if (params.query?.trim())", source)
        self.assertNotIn("q: params.query", source)

    def test_central_renderer_controls_search_state_visibility(self):
        source = read_frontend("js/renderers/stateRenderer.js")
        self.assertIn("status !== SearchStatus.LOADING", source)
        self.assertIn("status !== SearchStatus.EMPTY", source)
        self.assertIn("status !== SearchStatus.ERROR", source)
        self.assertIn("status !== SearchStatus.SUCCESS", source)

    def test_load_more_has_separate_loading_state(self):
        source = read_frontend("js/pages/searchPage.js")
        self.assertIn("state.isLoadingMore = true", source)
        self.assertIn("state.items = state.items.concat", source)
        self.assertIn("startFreshSearch", source)

    def test_retry_uses_last_request(self):
        source = read_frontend("js/pages/searchPage.js")
        self.assertIn("state.lastRequest", source)
        self.assertIn("retryLastSearch", source)

    def test_thumbnail_has_load_and_error_handlers(self):
        source = read_frontend("js/renderers/mediaCard.js")
        self.assertIn('image.addEventListener("load"', source)
        self.assertIn('image.addEventListener("error"', source)
        self.assertIn("thumbnail-failed", source)


if __name__ == "__main__":
    unittest.main()
