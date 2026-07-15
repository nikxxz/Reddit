from backend.services.reddit import RedditConnectionService, RedditSearchService


def get_reddit_connection_service() -> RedditConnectionService:
    return RedditConnectionService()


def get_reddit_search_service() -> RedditSearchService:
    return RedditSearchService()
