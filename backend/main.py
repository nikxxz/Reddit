from pathlib import Path
from contextlib import asynccontextmanager
from time import monotonic

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routes.auth import router as auth_router
from backend.routes.downloads import router as downloads_router
from backend.routes.health import router as health_router
from backend.routes.library import router as library_router
from backend.routes.reddit import router as reddit_router
from backend.routes.system import router as system_router
from backend.routes.universal_search import router as universal_search_router
from backend.services.background import background_task_registry
from backend.services.downloads.manager import download_job_manager
from backend.services.lifecycle import application_lifecycle
from backend.services.maintenance import maintenance_scheduler
from backend.services.library.startup import initialize_library
from backend.services.library.reconciliation import library_reconciliation_service
from backend.services.reddit.oauth import reddit_oauth_manager
from backend.services.system import startup_diagnostics
from backend.utils.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    started = monotonic()
    configure_logging(settings.debug)
    application_lifecycle.mark_starting()
    logger = get_logger(__name__)
    logger.info("application.startup.begin")
    try:
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        initialize_library()
        startup_diagnostics()
        application_lifecycle.mark_ready(
            database_ready=True,
            download_manager_ready=True,
            reddit_ready=True,
        )
        if settings.library_reconcile_on_startup:
            await library_reconciliation_service.start()
        await background_task_registry.create(
            maintenance_scheduler.run(),
            name="maintenance-loop",
            group="maintenance",
        )
        try:
            reddit_oauth_manager.restore_session()
        except Exception:
            logger.exception("application.startup.reddit_session_restore.failed")
            application_lifecycle.mark_ready(
                database_ready=True,
                download_manager_ready=True,
                reddit_ready=False,
            )
        logger.info("application.startup.ready elapsed_ms=%s", int((monotonic() - started) * 1000))
    except Exception:
        application_lifecycle.mark_shutdown()
        logger.exception("application.startup.failed elapsed_ms=%s", int((monotonic() - started) * 1000))
        raise
    try:
        yield
    finally:
        shutdown_started = monotonic()
        application_lifecycle.mark_shutdown()
        logger.info("application.shutdown.begin")
        await maintenance_scheduler.stop()
        await library_reconciliation_service.cancel()
        await download_job_manager.shutdown(settings.shutdown_grace_period_seconds)
        await background_task_registry.cancel_all()
        await background_task_registry.wait_all(settings.shutdown_grace_period_seconds)
        logger.info("application.shutdown.completed elapsed_ms=%s", int((monotonic() - shutdown_started) * 1000))


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(health_router, prefix="/api")
app.include_router(reddit_router, prefix="/api")
app.include_router(universal_search_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(downloads_router, prefix="/api")
app.include_router(library_router, prefix="/api")
app.include_router(system_router, prefix="/api")

BASE_DIR = Path(__file__).resolve().parent.parent
REACT_DIST = BASE_DIR / "frontend-react" / "dist"
REACT_INDEX = REACT_DIST / "index.html"
REACT_ASSETS = REACT_DIST / "assets"
DOWNLOAD_DIR = settings.download_dir_path

if REACT_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=REACT_ASSETS), name="react-assets")


@app.get("/", include_in_schema=False)
def serve_frontend() -> Response:
    if react_build_exists():
        return FileResponse(REACT_INDEX)

    return frontend_not_built_response()


@app.get("/{path:path}", include_in_schema=False)
def serve_spa_fallback(path: str) -> Response:
    if path == "" or path.startswith("api/"):
        raise HTTPException(status_code=404)

    requested_file = REACT_DIST / path

    if react_build_exists() and requested_file.is_file():
        return FileResponse(requested_file)

    if "." in Path(path).name:
        raise HTTPException(status_code=404)

    if react_build_exists():
        return FileResponse(REACT_INDEX)

    return frontend_not_built_response()


def react_build_exists() -> bool:
    return REACT_INDEX.exists() and REACT_ASSETS.exists()


def frontend_not_built_response() -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html>"
        "<html lang=\"en\">"
        "<head><meta charset=\"utf-8\"><title>React frontend not built</title></head>"
        "<body>"
        "<h1>React frontend not built</h1>"
        "<p>Run npm install and npm run dev, or run npm run build.</p>"
        "</body>"
        "</html>",
        status_code=503
    )
