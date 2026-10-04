"""Small in-memory LRU cache keyed by hash of normalized input."""
import hashlib
import json
from collections import OrderedDict
from typing import Any


class LRUCache:
    """Bounded LRU cache."""

    def __init__(self, size: int = 64) -> None:
        self._d: OrderedDict[str, Any] = OrderedDict()
        self._size = size

    @staticmethod
    def key(payload: dict) -> str:
        """Hash a normalized payload."""
        norm = json.dumps(payload, sort_keys=True, ensure_ascii=False).lower()
        return hashlib.sha256(norm.encode()).hexdigest()

    def get(self, k: str) -> Any | None:
        """Fetch and refresh an entry."""
        if k in self._d:
            self._d.move_to_end(k)
            return self._d[k]
        return None

    def put(self, k: str, v: Any) -> None:
        """Store an entry, evicting the oldest."""
        self._d[k] = v
        self._d.move_to_end(k)
        while len(self._d) > self._size:
            self._d.popitem(last=False)
