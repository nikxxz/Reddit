from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename_from_url(url: str, fallback: str = "download") -> str:
    name = Path(urlparse(url).path).name or fallback
    name = SAFE_FILENAME_RE.sub("_", name).strip("._")
    return name or fallback
