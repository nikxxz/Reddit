from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from time import monotonic

from backend.config import settings
from backend.services.universal.providers.pinterest_models import (
    PinterestExtractorError,
    PinterestExtractorProbe,
)
from backend.utils.logging import get_logger


logger = get_logger(__name__)
MAX_OUTPUT_BYTES = 5 * 1024 * 1024


class PinterestGalleryDlExtractor:
    def __init__(self) -> None:
        self._probe: PinterestExtractorProbe | None = None
        self._semaphore = asyncio.Semaphore(settings.pinterest_max_concurrent_extractions)

    async def probe(self, *, refresh: bool = False) -> PinterestExtractorProbe:
        if self._probe and not refresh:
            return self._probe
        started = monotonic()
        logger.info("pinterest.extractor.probe.started")
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "gallery_dl",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout=10)
            if process.returncode != 0:
                raise PinterestExtractorError("pinterest_extractor_unavailable")
            version = stdout.decode("utf-8", errors="replace").strip() or None
            self._probe = PinterestExtractorProbe(available=True, version=version)
            logger.info(
                "pinterest.extractor.probe.completed extractor_version=%s elapsed_ms=%s",
                version,
                int((monotonic() - started) * 1000),
            )
        except (FileNotFoundError, TimeoutError, asyncio.TimeoutError, PinterestExtractorError):
            self._probe = PinterestExtractorProbe(available=False, error_code="pinterest_extractor_unavailable")
            logger.warning("pinterest.extractor.probe.failed error_code=pinterest_extractor_unavailable")
        return self._probe

    async def extract(self, url: str, *, limit: int, cookie_file: Path | None = None, offset: int = 0) -> list[dict[str, object]]:
        probe = await self.probe()
        if not probe.available:
            raise PinterestExtractorError("pinterest_extractor_unavailable")
        args = [
            sys.executable,
            "-m",
            "gallery_dl",
            "--dump-json",
            "--range",
            f"{max(1, offset + 1)}-{max(1, offset + min(limit, settings.pinterest_max_results))}",
        ]
        if cookie_file and cookie_file.exists():
            args.extend(["--cookies", str(cookie_file)])
        args.append(url)
        async with self._semaphore:
            return await self._run(args)

    async def _run(self, args: list[str]) -> list[dict[str, object]]:
        started = monotonic()
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=settings.pinterest_extractor_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            try:
                process.kill()
            except Exception:
                pass
            raise PinterestExtractorError("pinterest_extractor_timeout") from exc
        except FileNotFoundError as exc:
            raise PinterestExtractorError("pinterest_extractor_unavailable") from exc
        if len(stdout) > MAX_OUTPUT_BYTES:
            raise PinterestExtractorError("pinterest_extractor_output_too_large")
        if process.returncode != 0:
            raise PinterestExtractorError("pinterest_session_required")
        try:
            records = _parse_json_lines(stdout.decode("utf-8", errors="replace"))
        except ValueError as exc:
            raise PinterestExtractorError("pinterest_extractor_invalid_json") from exc
        logger.info(
            "pinterest.extractor.completed result_count=%s elapsed_ms=%s",
            len(records),
            int((monotonic() - started) * 1000),
        )
        return records


def _parse_json_lines(text: str) -> list[dict[str, object]]:
    records = []
    for line in text.splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            records.append(value)
        elif isinstance(value, list):
            records.extend(item for item in value if isinstance(item, dict))
    return records


pinterest_extractor = PinterestGalleryDlExtractor()
