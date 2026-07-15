import html
from typing import Any


def decode_html_entities(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return html.unescape(value)
