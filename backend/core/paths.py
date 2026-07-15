from __future__ import annotations

from pathlib import Path

from backend.config import BASE_DIR, settings


class PathSafetyError(ValueError):
    pass


def get_application_root() -> Path:
    return BASE_DIR.resolve()


def get_app_data_root() -> Path:
    return _resolve_root(settings.app_data_dir)


def get_download_root() -> Path:
    return _resolve_root(settings.download_dir)


def get_database_dir() -> Path:
    return get_app_data_root() / "database"


def get_database_path() -> Path:
    return get_database_dir() / settings.database_filename


def get_thumbnail_root() -> Path:
    return get_app_data_root() / "thumbnails" / "generated"


def get_backup_root() -> Path:
    return get_app_data_root() / "backups"


def get_session_root() -> Path:
    return get_app_data_root() / "sessions"


def ensure_app_directories() -> None:
    for path in [
        get_app_data_root(),
        get_database_dir(),
        get_thumbnail_root(),
        get_backup_root(),
        get_session_root(),
        get_download_root(),
    ]:
        path.mkdir(parents=True, exist_ok=True)


def to_relative_download_path(path: str | Path) -> str:
    return _to_relative_path(path, get_download_root())


def to_relative_app_data_path(path: str | Path) -> str:
    return _to_relative_path(path, get_app_data_root())


def resolve_download_path(relative_path: str) -> Path:
    return _resolve_relative_path(relative_path, get_download_root())


def resolve_app_data_path(relative_path: str) -> Path:
    return _resolve_relative_path(relative_path, get_app_data_root())


def relative_to_application(path: str | Path) -> str:
    return _to_relative_path(path, get_application_root())


def _resolve_root(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = get_application_root() / path
    return path.resolve()


def _to_relative_path(path: str | Path, root: Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = get_application_root() / candidate
    candidate = candidate.resolve()
    root = root.resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise PathSafetyError("Path is outside the approved root.") from exc
    return relative.as_posix()


def _resolve_relative_path(relative_path: str, root: Path) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise PathSafetyError("Stored path must be relative.")
    raw = Path(relative_path)
    if any(part in {"..", ""} for part in raw.parts):
        raise PathSafetyError("Stored path contains unsafe traversal.")
    resolved = (root / raw).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise PathSafetyError("Stored path escapes the approved root.") from exc
    return resolved
