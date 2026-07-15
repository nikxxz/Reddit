from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit, urlunsplit

from backend.config import settings
from backend.models.downloads import (
    DownloadJobFilter,
    DownloadJobSummary,
    DownloadRequest,
    DownloadStatusResponse,
    DownloadedFile,
)
from backend.services.downloads.direct import download_direct_url
from backend.services.downloads.errors import DownloadCancelled, DownloadError
from backend.services.downloads.gallery import download_gallery_urls
from backend.services.downloads.resolver import resolve_download_request
from backend.services.downloads.yt_dlp_service import download_with_yt_dlp, ffmpeg_available
from backend.services.system import PART_SUFFIX, cleanup_stale_part_files, has_minimum_free_space
from backend.utils.logging import get_logger


logger = get_logger(__name__)
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
NON_TERMINAL_STATUSES = {"queued", "resolving", "downloading", "merging"}
ACTIVE_STATUSES = {"resolving", "downloading", "merging"}
RETRYABLE_STATUSES = {"failed", "cancelled"}
SUMMARY_ORDER = {
    "resolving": 0,
    "downloading": 0,
    "merging": 0,
    "queued": 1,
    "failed": 2,
    "completed": 3,
    "cancelled": 4,
}
LEGAL_TRANSITIONS = {
    "queued": {"resolving", "downloading", "failed", "cancelled"},
    "resolving": {"downloading", "failed", "cancelled"},
    "downloading": {"merging", "completed", "failed", "cancelled"},
    "merging": {"completed", "failed", "cancelled"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


@dataclass
class DownloadJob:
    job_id: str
    request: DownloadRequest
    status: str = "queued"
    progress: int | None = 0
    message: str = "Waiting to start"
    filename: str | None = None
    files: list[dict[str, object]] = field(default_factory=list)
    error: str | None = None
    bytes_downloaded: int | None = None
    total_bytes: int | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    created_at: float = field(default_factory=monotonic)
    updated_at: float = field(default_factory=monotonic)
    created_at_wall: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at_wall: datetime | None = None
    completed_at_wall: datetime | None = None
    partial_paths: set[Path] = field(default_factory=set)


class DownloadJobManager:
    def __init__(self, max_concurrent: int | None = None) -> None:
        self.jobs: dict[str, DownloadJob] = {}
        self.lock = threading.RLock()
        self.semaphore = asyncio.Semaphore(max_concurrent or settings.max_concurrent_downloads)
        logger.info("download.ffmpeg.status available=%s", ffmpeg_available())

    async def create_job(self, request: DownloadRequest) -> DownloadJob:
        self.cleanup_jobs()
        if not has_minimum_free_space(settings.download_dir_path):
            raise DownloadError("Not enough free disk space to start this download.")
        job = DownloadJob(job_id=str(uuid.uuid4()), request=request)
        with self.lock:
            self.jobs[job.job_id] = job
        logger.info(
            "download.job.created job_id=%s post_id=%s media_type=%s subreddit=%s author=%s",
            job.job_id,
            request.post_id,
            request.media_type,
            request.subreddit,
            request.author,
        )
        asyncio.create_task(self._run_job(job))
        return job

    def get_status(self, job_id: str) -> DownloadStatusResponse | None:
        self.cleanup_jobs()
        with self.lock:
            job = self.jobs.get(job_id)
        if not job:
            return None
        return self._response(job)

    def list_jobs(self, status_filter: DownloadJobFilter = "all") -> list[DownloadJobSummary]:
        self.cleanup_jobs()
        with self.lock:
            jobs = [job for job in self.jobs.values() if _matches_filter(job.status, status_filter)]
            jobs.sort(key=lambda item: (SUMMARY_ORDER.get(item.status, 99), -item.created_at))
            return [self._summary(job) for job in jobs]

    def cancel_job(self, job_id: str) -> DownloadStatusResponse | None:
        with self.lock:
            job = self.jobs.get(job_id)
        if not job:
            return None
        if job.status not in TERMINAL_STATUSES:
            job.cancel_event.set()
            self.transition_job(job, "cancelled", progress=None, message="Download cancelled", error=None)
        return self._response(job)

    async def retry_job(self, job_id: str) -> DownloadJob | None:
        started = monotonic()
        logger.info("download.job.retry.start old_job_id=%s", job_id)
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            if job.status not in RETRYABLE_STATUSES:
                logger.warning(
                    "download.job.retry.failed old_job_id=%s reason=not_retryable elapsed_ms=%s",
                    job_id,
                    int((monotonic() - started) * 1000),
                )
                raise DownloadError("Only failed or cancelled downloads can be retried.")
            request = job.request.model_copy(deep=True)
        new_job = await self.create_job(request)
        logger.info(
            "download.job.retry.success old_job_id=%s new_job_id=%s elapsed_ms=%s",
            job_id,
            new_job.job_id,
            int((monotonic() - started) * 1000),
        )
        return new_job

    def clear_terminal_jobs(self, statuses: set[str] | None = None) -> int:
        started = monotonic()
        requested = statuses or TERMINAL_STATUSES
        removable = requested & TERMINAL_STATUSES
        removed = 0
        logger.info("download.jobs.clear.start status_filters=%s", ",".join(sorted(removable)))
        try:
            with self.lock:
                for job_id, job in list(self.jobs.items()):
                    if job.status in removable:
                        del self.jobs[job_id]
                        removed += 1
            logger.info(
                "download.jobs.clear.success removed=%s elapsed_ms=%s",
                removed,
                int((monotonic() - started) * 1000),
            )
            return removed
        except Exception:
            logger.exception(
                "download.jobs.clear.failed elapsed_ms=%s",
                int((monotonic() - started) * 1000),
            )
            raise

    def cleanup_jobs(self) -> dict[str, int]:
        started = monotonic()
        completed_cutoff = started - (settings.download_job_retention_hours * 3600)
        failed_cutoff = started - (settings.failed_job_retention_hours * 3600)
        stats = {
            "jobs_examined": 0,
            "jobs_removed": 0,
            "completed_removed": 0,
            "failed_removed": 0,
            "cancelled_removed": 0,
            "elapsed_ms": 0,
        }
        logger.info("download.jobs.cleanup.start")
        with self.lock:
            for job_id, job in list(self.jobs.items()):
                stats["jobs_examined"] += 1
                if job.status in NON_TERMINAL_STATUSES:
                    continue
                cutoff = completed_cutoff if job.status == "completed" else failed_cutoff
                if job.updated_at >= cutoff:
                    continue
                del self.jobs[job_id]
                stats["jobs_removed"] += 1
                if job.status == "completed":
                    stats["completed_removed"] += 1
                elif job.status == "failed":
                    stats["failed_removed"] += 1
                elif job.status == "cancelled":
                    stats["cancelled_removed"] += 1
        stats["elapsed_ms"] = int((monotonic() - started) * 1000)
        logger.info(
            "download.jobs.cleanup.completed jobs_examined=%s jobs_removed=%s completed_removed=%s failed_removed=%s cancelled_removed=%s elapsed_ms=%s",
            stats["jobs_examined"],
            stats["jobs_removed"],
            stats["completed_removed"],
            stats["failed_removed"],
            stats["cancelled_removed"],
            stats["elapsed_ms"],
        )
        return stats

    def active_counts(self) -> tuple[int, int]:
        with self.lock:
            active = sum(1 for job in self.jobs.values() if job.status in {"resolving", "downloading", "merging"})
            queued = sum(1 for job in self.jobs.values() if job.status == "queued")
        return active, queued

    def active_part_paths(self) -> set[Path]:
        with self.lock:
            return {path for job in self.jobs.values() if job.status in NON_TERMINAL_STATUSES for path in job.partial_paths}

    def cleanup_stale_part_files(self) -> dict[str, int]:
        return cleanup_stale_part_files(active_part_paths=self.active_part_paths())

    def transition_job(self, job: DownloadJob, new_status: str, **updates: object) -> bool:
        with self.lock:
            if job.status == new_status:
                for key, value in updates.items():
                    setattr(job, key, value)
                job.updated_at = monotonic()
                return True
            if new_status not in LEGAL_TRANSITIONS.get(job.status, set()):
                logger.warning(
                    "download.job.transition.invalid job_id=%s from_status=%s to_status=%s",
                    job.job_id,
                    job.status,
                    new_status,
                )
                return False
            job.status = new_status
            for key, value in updates.items():
                setattr(job, key, value)
            job.updated_at = monotonic()
            if new_status in ACTIVE_STATUSES and job.started_at_wall is None:
                job.started_at_wall = datetime.now(timezone.utc)
            if new_status in TERMINAL_STATUSES:
                job.completed_at_wall = datetime.now(timezone.utc)
            if new_status == "cancelled":
                logger.info("download.job.cancelled job_id=%s", job.job_id)
            return True

    async def _run_job(self, job: DownloadJob) -> None:
        async with self.semaphore:
            if job.cancel_event.is_set():
                self._mark_cancelled(job)
                return

            started = monotonic()
            logger.info("download.job.started job_id=%s", job.job_id)
            try:
                if not self.transition_job(job, "resolving", message="Preparing media..."):
                    return
                resolved = resolve_download_request(job.request)
                resolved.output_dir.mkdir(parents=True, exist_ok=True)
                job.partial_paths = {
                    (resolved.output_dir / filename).with_suffix(Path(filename).suffix + PART_SUFFIX)
                    for filename in resolved.filenames
                }

                max_size = settings.max_download_size_mb * 1024 * 1024
                if resolved.strategy == "gallery":
                    await asyncio.to_thread(self._run_gallery, job, resolved, max_size)
                elif resolved.strategy == "direct":
                    await asyncio.to_thread(self._run_direct, job, resolved, max_size)
                elif resolved.strategy == "yt_dlp":
                    await asyncio.to_thread(self._run_ytdlp, job, resolved)
                else:
                    raise DownloadError("The selected media cannot be downloaded.")

                if self.transition_job(job, "completed", progress=100, message=job.message or "Download completed"):
                    logger.info(
                        "download.job.completed job_id=%s elapsed_ms=%s",
                        job.job_id,
                        int((monotonic() - started) * 1000),
                    )
            except DownloadCancelled:
                self._mark_cancelled(job)
            except Exception as exc:
                self.transition_job(
                    job,
                    "failed",
                    progress=None,
                    error=_safe_error(exc),
                    message="Download failed",
                )
                logger.warning(
                    "download.job.failed job_id=%s error_type=%s elapsed_ms=%s",
                    job.job_id,
                    exc.__class__.__name__,
                    int((monotonic() - started) * 1000),
                )

    def _run_direct(self, job: DownloadJob, resolved, max_size: int) -> None:
        url = resolved.urls[0]
        filename = resolved.filenames[0]
        if not self.transition_job(job, "downloading", message="Downloading..."):
            return
        logger.info(
            "download.direct.start job_id=%s post_id=%s media_type=%s filename=%s",
            job.job_id,
            job.request.post_id,
            job.request.media_type,
            filename,
        )
        path = download_direct_url(
            url,
            resolved.output_dir,
            filename=filename,
            max_size_bytes=max_size,
            progress_callback=lambda done, total: self._update_progress(job, done, total),
            cancel_event=job.cancel_event,
        )
        if job.status in TERMINAL_STATUSES:
            return
        job.filename = path.name
        job.files = [{"filename": path.name, "category": resolved.category, "status": "completed"}]
        job.message = "Download completed"
        logger.info(
            "download.direct.completed job_id=%s filename=%s bytes=%s",
            job.job_id,
            path.name,
            job.bytes_downloaded,
        )

    def _run_gallery(self, job: DownloadJob, resolved, max_size: int) -> None:
        if not self.transition_job(job, "downloading", message="Downloading gallery..."):
            return
        total = len(resolved.urls)
        logger.info(
            "download.gallery.start job_id=%s post_id=%s total_items=%s",
            job.job_id,
            job.request.post_id,
            total,
        )

        def update(item_index: int, done: int, total_bytes: int | None, total_items: int) -> None:
            if job.status in TERMINAL_STATUSES:
                return
            job.bytes_downloaded = done
            job.total_bytes = total_bytes
            job.progress = min(99, int(((item_index - 1) / total_items) * 100))
            job.message = f"{item_index} of {total_items} downloading"

        completed, failed = download_gallery_urls(
            urls=resolved.urls,
            output_dir=resolved.output_dir,
            filenames=resolved.filenames,
            max_size_bytes=max_size,
            progress_callback=update,
            cancel_event=job.cancel_event,
        )
        if job.status in TERMINAL_STATUSES:
            return
        files = [
            {**item, "category": resolved.category}
            for item in [*completed, *failed]
        ]
        job.files = files
        job.filename = completed[0]["filename"] if len(completed) == 1 else None
        job.message = (
            "One or more gallery items could not be downloaded."
            if failed
            else "Download completed"
        )
        logger.info(
            "download.gallery.completed job_id=%s total_items=%s failed_items=%s",
            job.job_id,
            total,
            len(failed),
        )

    def _run_ytdlp(self, job: DownloadJob, resolved) -> None:
        url = resolved.urls[0]
        filename = resolved.filenames[0]
        if not self.transition_job(job, "downloading", message="Downloading..."):
            return
        logger.info(
            "download.ytdlp.start job_id=%s post_id=%s media_type=%s filename=%s ffmpeg_available=%s",
            job.job_id,
            job.request.post_id,
            job.request.media_type,
            filename,
            ffmpeg_available(),
        )

        def progress_hook(progress: dict[str, object]) -> None:
            status = progress.get("status")
            if job.status in TERMINAL_STATUSES:
                return
            if status == "downloading":
                done = _safe_int(progress.get("downloaded_bytes"))
                total = _safe_int(progress.get("total_bytes") or progress.get("total_bytes_estimate"))
                self._update_progress(job, done or 0, total)
            if status == "finished":
                if self.transition_job(job, "merging", message="Merging audio and video..."):
                    logger.info("download.ytdlp.merging job_id=%s", job.job_id)

        path = download_with_yt_dlp(
            url,
            resolved.output_dir,
            filename=filename,
            progress_callback=progress_hook,
            cancel_event=job.cancel_event,
        )
        if job.status in TERMINAL_STATUSES:
            return
        job.filename = path.name
        job.files = [{"filename": path.name, "category": resolved.category, "status": "completed"}]
        job.message = "Download completed"
        logger.info("download.ytdlp.completed job_id=%s filename=%s", job.job_id, path.name)

    def _update_progress(self, job: DownloadJob, done: int, total: int | None) -> None:
        if job.status in TERMINAL_STATUSES:
            return
        job.bytes_downloaded = done
        job.total_bytes = total
        if total:
            job.progress = max(0, min(99, int(done / total * 100)))
            job.message = f"Downloading {job.progress}%"
        else:
            job.progress = None
            job.message = f"Downloading {done} bytes"

    def _mark_cancelled(self, job: DownloadJob) -> None:
        job.cancel_event.set()
        self.transition_job(job, "cancelled", progress=None, message="Download cancelled", error=None)

    def _response(self, job: DownloadJob) -> DownloadStatusResponse:
        files = [DownloadedFile(**file) for file in job.files]
        return DownloadStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            message=job.message,
            filename=job.filename,
            files=files,
            error=job.error,
            bytes_downloaded=job.bytes_downloaded,
            total_bytes=job.total_bytes,
        )

    def _summary(self, job: DownloadJob) -> DownloadJobSummary:
        files = [DownloadedFile(**file) for file in job.files]
        return DownloadJobSummary(
            job_id=job.job_id,
            post_id=job.request.post_id,
            status=job.status,
            progress=job.progress,
            message=job.message,
            media_type=job.request.media_type,
            title=job.request.title,
            subreddit=job.request.subreddit,
            author=job.request.author,
            thumbnail_url=_safe_public_url(job.request.thumbnail_url),
            created_at=job.created_at_wall,
            started_at=job.started_at_wall,
            completed_at=job.completed_at_wall,
            files=files,
            error=job.error,
            bytes_downloaded=job.bytes_downloaded,
            total_bytes=job.total_bytes,
            cancellable=job.status not in TERMINAL_STATUSES,
            retryable=job.status in RETRYABLE_STATUSES,
        )


def _safe_error(error: Exception) -> str:
    if isinstance(error, DownloadError) and str(error):
        return str(error)
    return "The selected media could not be downloaded."


def _safe_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _matches_filter(status: str, status_filter: DownloadJobFilter) -> bool:
    if status_filter == "all":
        return True
    if status_filter == "active":
        return status in ACTIVE_STATUSES
    return status == status_filter


def _safe_public_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


download_job_manager = DownloadJobManager()
