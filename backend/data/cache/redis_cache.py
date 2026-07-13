"""Redis-backed cache adapter stub."""

from __future__ import annotations


class RedisCache:
    """Placeholder cache implementation."""

    def get(self, key: str) -> object | None:
        """Retrieve a value from cache."""
        return None

    def set(self, key: str, value: object) -> None:
        """Store a value in cache."""
        return None
