"""Generic cache manager for historical-data framework components."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CacheEntry:
    """Structured representation of a cached entry."""

    payload: Any
    created_at: datetime
    expires_at: datetime | None
    version: str | None
    integrity_hash: str


class CacheManager:
    """Store and retrieve small payloads on disk with metadata and expiration."""

    def __init__(
        self,
        base_dir: str | Path | None = None,
        default_ttl_seconds: float | None = None,
    ) -> None:
        self.base_dir = Path(base_dir or os.getenv("OPTION_RESEARCH_CACHE_DIR", ".cache"))
        self.default_ttl_seconds = default_ttl_seconds
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def set(
        self,
        key: str,
        value: Any,
        *,
        version: str | None = None,
        ttl_seconds: float | None = None,
    ) -> None:
        """Persist a value to disk with metadata and versioning."""
        payload = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
        integrity_hash = hashlib.sha256(payload).hexdigest()
        created_at = datetime.now(tz=datetime.UTC)
        expires_at = None
        if ttl_seconds is not None or self.default_ttl_seconds is not None:
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
            assert ttl is not None
            expires_at = created_at + timedelta(seconds=float(ttl))

        entry = CacheEntry(
            payload=value,
            created_at=created_at,
            expires_at=expires_at,
            version=version,
            integrity_hash=integrity_hash,
        )
        self._write_entry(key, entry)

    def get(self, key: str) -> Any | None:
        """Return a cached value if it is present and has not expired."""
        entry = self.get_metadata(key)
        if entry is None:
            return None
        return entry.payload

    def get_metadata(self, key: str) -> CacheEntry | None:
        """Return the cache entry metadata, or None if the entry is missing or expired."""
        path = self._entry_path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        created_at = datetime.fromisoformat(entry["created_at"])
        expires_at = None
        if entry.get("expires_at"):
            expires_at = datetime.fromisoformat(entry["expires_at"])
        if expires_at is not None and datetime.now(tz=datetime.UTC) > expires_at:
            self.delete(key)
            return None

        return CacheEntry(
            payload=entry["payload"],
            created_at=created_at,
            expires_at=expires_at,
            version=entry.get("version"),
            integrity_hash=entry.get("integrity_hash", ""),
        )

    def contains(self, key: str) -> bool:
        """Return whether a key exists and is still valid."""
        return self.get_metadata(key) is not None

    def delete(self, key: str) -> None:
        """Delete an entry from the cache."""
        path = self._entry_path(key)
        if path.exists():
            path.unlink()

    def _entry_path(self, key: str) -> Path:
        safe_key = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.base_dir / f"{safe_key}.json"

    def _write_entry(self, key: str, entry: CacheEntry) -> None:
        path = self._entry_path(key)
        payload = {
            "payload": entry.payload,
            "created_at": entry.created_at.isoformat(),
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
            "version": entry.version,
            "integrity_hash": entry.integrity_hash,
        }
        path.write_text(json.dumps(payload, sort_keys=True, default=str), encoding="utf-8")
