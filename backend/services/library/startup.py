from __future__ import annotations

from backend.core.paths import ensure_app_directories
from backend.database.migrations import initialize_database
from backend.database.repositories.downloads import mark_interrupted_jobs
from backend.services.library.backups import create_routine_backup_if_due
from backend.services.library.reconciliation import reconcile_library
from backend.config import settings
from backend.utils.logging import get_logger


logger = get_logger(__name__)


def initialize_library() -> None:
    ensure_app_directories()
    initialize_database()
    interrupted = mark_interrupted_jobs()
    if interrupted:
        logger.info("library.startup.interrupted_marked count=%s", interrupted)
    if settings.library_reconcile_on_startup:
        reconcile_library()
    create_routine_backup_if_due()
