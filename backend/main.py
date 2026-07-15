from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routes.health import router as health_router
from backend.routes.reddit import router as reddit_router

app = FastAPI(title="Reddit Media Downloader")

app.include_router(health_router, prefix="/api")
app.include_router(reddit_router, prefix="/api")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DOWNLOAD_DIR = settings.download_dir_path
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def read_index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/styles.css")
def get_styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "styles.css")


@app.get("/app.js")
def get_app_js() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "app.js")
