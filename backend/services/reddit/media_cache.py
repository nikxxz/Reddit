from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic

from backend.config import settings
from backend.models.reddit import RedditMediaItem


@dataclass
class CachedMediaItem:
    item: RedditMediaItem
    cached_at: float


class NormalizedMediaCache:
    def __init__(self) -> None:
        self._items: OrderedDict[str, CachedMediaItem] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, post_id: str | None) -> RedditMediaItem | None:
        if not post_id:
            return None
        with self._lock:
            entry = self._items.get(post_id)
            if not entry:
                return None
            if monotonic() - entry.cached_at > settings.media_cache_ttl_minutes * 60:
                del self._items[post_id]
                return None
            self._items.move_to_end(post_id)
            return entry.item

    def set(self, item: RedditMediaItem) -> None:
        if not item.id:
            return
        with self._lock:
            self._items[item.id] = CachedMediaItem(item=item, cached_at=monotonic())
            self._items.move_to_end(item.id)
            while len(self._items) > max(1, settings.media_cache_max_items):
                self._items.popitem(last=False)

    def invalidate(self, post_id: str | None) -> None:
        if not post_id:
            return
        with self._lock:
            self._items.pop(post_id, None)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


normalized_media_cache = NormalizedMediaCache()
