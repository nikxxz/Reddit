from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from backend.services.reddit.oauth import reddit_oauth_manager
from backend.utils.logging import get_logger


router = APIRouter(tags=["reddit-auth"])
logger = get_logger(__name__)


@router.get("/reddit/auth/login")
def reddit_auth_login(frontend_origin: str | None = Query(default=None)) -> dict[str, str]:
    try:
        safe_origin = _safe_frontend_origin(frontend_origin)
        authorization_url = reddit_oauth_manager.create_authorization_url(
            frontend_origin=safe_origin
        )
        return {"url": authorization_url, "authorization_url": authorization_url}
    except Exception as exc:
        logger.warning("reddit.oauth.login.failed error_type=%s", exc.__class__.__name__)
        raise HTTPException(status_code=502, detail="Unable to connect Reddit account.") from None


@router.get("/reddit/auth/callback", response_class=HTMLResponse)
def reddit_auth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> HTMLResponse:
    target_origin = reddit_oauth_manager.get_state_frontend_origin(state)
    try:
        reddit_oauth_manager.handle_callback(code=code, state=state, error=error)
        return HTMLResponse(
            _callback_page(
                "Reddit account connected successfully.",
                "You may close this window.",
                True,
                target_origin,
            )
        )
    except ValueError as exc:
        message = str(exc) or "Unable to connect Reddit account."
        logger.warning("reddit.oauth.callback.failed reason=%s", message)
        return HTMLResponse(
            _callback_page(message, "Return to the app and try again.", False, target_origin),
            status_code=400,
        )
    except Exception as exc:
        logger.warning("reddit.oauth.callback.failed error_type=%s", exc.__class__.__name__)
        return HTMLResponse(
            _callback_page(
                "Unable to connect Reddit account.",
                "Retry later from the app.",
                False,
                target_origin,
            ),
            status_code=502,
        )


@router.get("/reddit/auth/status")
def reddit_auth_status() -> dict[str, object]:
    status = reddit_oauth_manager.status()
    if not status.connected:
        return {"connected": False}
    return {
        "connected": True,
        "username": status.username,
        "read_only": False,
    }


@router.post("/reddit/auth/logout")
def reddit_auth_logout() -> dict[str, bool]:
    try:
        reddit_oauth_manager.logout()
        return {"success": True}
    except Exception as exc:
        logger.warning("reddit.oauth.logout.failed error_type=%s", exc.__class__.__name__)
        raise HTTPException(status_code=502, detail="Unable to disconnect Reddit account.") from None


def _safe_frontend_origin(origin: str | None) -> str | None:
    if not origin:
        return None

    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return f"{parsed.scheme}://{parsed.netloc}"


def _callback_page(
    title: str,
    detail: str,
    success: bool,
    target_origin: str | None,
) -> str:
    event_type = "reddit-oauth-success" if success else "reddit-oauth-error"
    post_target = target_origin or "window.location.origin"
    quoted_target = f'"{post_target}"' if target_origin else post_target
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{title}</title>
    <style>
      body {{ font-family: system-ui, sans-serif; display: grid; min-height: 100vh; place-items: center; margin: 0; color: #0f172a; }}
      main {{ text-align: center; max-width: 32rem; padding: 2rem; }}
      h1 {{ font-size: 1.4rem; margin-bottom: 0.5rem; }}
      p {{ color: #475569; }}
    </style>
  </head>
  <body>
    <main>
      <h1>{title}</h1>
      <p>{detail}</p>
    </main>
    <script>
      if (window.opener) {{
        window.opener.postMessage({{ type: "{event_type}" }}, {quoted_target});
      }}
      window.setTimeout(() => window.close(), 700);
    </script>
  </body>
</html>"""
