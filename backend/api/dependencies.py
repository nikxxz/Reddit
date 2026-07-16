from backend.services.reddit import RedditConnectionService, RedditSearchService
from backend.services.reddit.entities import RedditEntityService


def get_reddit_connection_service() -> RedditConnectionService:
    return RedditConnectionService()


def get_reddit_search_service() -> RedditSearchService:
    return RedditSearchService()


def get_reddit_entity_service() -> RedditEntityService:
    return RedditEntityService()
