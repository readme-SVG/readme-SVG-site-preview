"""Small thread-safe TTL caches bounded by entry count and payload size."""

import time
from collections import OrderedDict
from threading import Lock
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")
_MISSING = object()


class TTLCache(Generic[K, V]):
    def __init__(self, max_entries: int, ttl: float, max_bytes: int | None = None):
        self.max_entries = max_entries
        self.ttl = ttl
        self.max_bytes = max_bytes
        self._entries: OrderedDict[K, tuple[float, V, int]] = OrderedDict()
        self._bytes = 0
        self._lock = Lock()

    def get(self, key: K, default=None):
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key, _MISSING)
            if entry is _MISSING:
                return default
            expires, value, _size = entry
            if expires <= now:
                self._remove(key)
                return default
            self._entries.move_to_end(key)
            return value

    def set(self, key: K, value: V, size: int = 0, ttl: float | None = None) -> None:
        if self.max_bytes is not None and size > self.max_bytes:
            return
        with self._lock:
            if key in self._entries:
                self._remove(key)
            self._entries[key] = (
                time.monotonic() + (self.ttl if ttl is None else ttl),
                value,
                size,
            )
            self._bytes += size
            while self._entries and (
                len(self._entries) > self.max_entries
                or (self.max_bytes is not None and self._bytes > self.max_bytes)
            ):
                self._remove(next(iter(self._entries)))

    def _remove(self, key: K) -> None:
        _, _, size = self._entries.pop(key)
        self._bytes -= size
