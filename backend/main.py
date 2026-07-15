from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routes.auth import router as auth_router
from backend.routes.health import router as health_router
from backend.routes.reddit import router as reddit_router
from backend.services.reddit.oauth import reddit_oauth_manager
from backend.utils.logging import configure_logging

configure_logging(settings.debug)
app = FastAPI(title=settings.app_name)

app.include_router(health_router, prefix="/api")
app.include_router(reddit_router, prefix="/api")
app.include_router(auth_router, prefix="/api")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DOWNLOAD_DIR = settings.download_dir_path
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/styles", StaticFiles(directory=FRONTEND_DIR / "styles"), name="styles")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def read_index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/styles.css")
def get_styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "styles.css")


@app.on_event("startup")
def restore_reddit_auth_session() -> None:
    reddit_oauth_manager.restore_session()
