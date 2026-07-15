from fastapi import APIRouter, HTTPException

from backend.services.reddit_service import RedditService

router = APIRouter(tags=["reddit"])


@router.get("/reddit/test")
def test_reddit_connection() -> dict[str, object]:
    service = RedditService()
    result = service.test_connection()

    if result.get("connected"):
        return {
            "status": "ok",
            "reddit": {
                "connected": True,
                "read_only": result.get("read_only", True),
                "authenticated_user": None,
            },
        }

    message = result.get("error", "Reddit API connection failed")
    raise HTTPException(status_code=502, detail=message)
