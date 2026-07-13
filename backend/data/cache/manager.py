"""Generic cache manager for historical-data framework components."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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
    manifest_checksum: str | None = None
    cache_key: str | None = None


@dataclass(slots=True)
class CacheCleanupReport:
    """Summary describing what cleanup removed from the cache."""

    removed_expired: int = 0
    removed_corrupt: int = 0
    removed_invalidated: int = 0


class CacheManager:
    """Store and retrieve small payloads on disk with metadata and expiration."""

    def __init__(
        self,
        base_dir: str | Path | None = None,
        default_ttl_seconds: float | None = None,
    ) -> None:
        env_cache_dir = os.getenv("OPTION_RESEARCH_CACHE_DIR") or ".cache"
        base_dir_value = base_dir if base_dir is not None else env_cache_dir
        self.base_dir = Path(base_dir_value)
        self.default_ttl_seconds = default_ttl_seconds
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def set(
        self,
        key: str,
        value: Any,
        *,
        version: str | None = None,
        ttl_seconds: float | None = None,
        manifest_checksum: str | None = None,
    ) -> None:
        """Persist a value to disk with metadata and versioning."""
        payload = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
        integrity_hash = hashlib.sha256(payload).hexdigest()
        created_at = datetime.now(tz=UTC)
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
            manifest_checksum=manifest_checksum,
            cache_key=key,
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
        except json.JSONDecodeError, OSError:
            self._safe_unlink(path)
            return None

        created_at = datetime.fromisoformat(entry["created_at"])
        expires_at = None
        if entry.get("expires_at"):
            expires_at = datetime.fromisoformat(entry["expires_at"])
        if expires_at is not None and datetime.now(tz=UTC) > expires_at:
            self.delete(key)
            return None

        payload = entry.get("payload")
        expected_hash = str(entry.get("integrity_hash", ""))
        actual_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        if expected_hash != actual_hash:
            self.delete(key)
            return None

        return CacheEntry(
            payload=payload,
            created_at=created_at,
            expires_at=expires_at,
            version=entry.get("version"),
            integrity_hash=expected_hash,
            manifest_checksum=entry.get("manifest_checksum"),
            cache_key=entry.get("cache_key"),
        )

    def contains(self, key: str) -> bool:
        """Return whether a key exists and is still valid."""
        return self.get_metadata(key) is not None

    def delete(self, key: str) -> None:
        """Delete an entry from the cache."""
        path = self._entry_path(key)
        if path.exists():
            self._safe_unlink(path)

    def verify_integrity(self, key: str, *, manifest_checksum: str | None = None) -> bool:
        """Verify payload hash and optional manifest checksum for a key."""
        entry = self.get_metadata(key)
        if entry is None:
            return False
        if manifest_checksum is not None and entry.manifest_checksum != manifest_checksum:
            return False
        return True

    def invalidate(
        self,
        predicate: Callable[[CacheEntry], bool] | None = None,
    ) -> CacheCleanupReport:
        """Invalidate cache entries by predicate, or all entries when omitted."""
        report = CacheCleanupReport()
        for path in self.base_dir.glob("*.json"):
            raw_entry = self._read_entry_file(path)
            if raw_entry is None:
                continue
            if predicate is None or predicate(raw_entry):
                self._safe_unlink(path)
                report.removed_invalidated += 1
        return report

    def cleanup(self) -> CacheCleanupReport:
        """Safely remove expired or corrupt entries and return a summary."""
        report = CacheCleanupReport()
        now = datetime.now(tz=UTC)

        for path in self.base_dir.glob("*.json"):
            raw_entry = self._read_entry_file(path)
            if raw_entry is None:
                report.removed_corrupt += 1
                continue

            if raw_entry.expires_at is not None and now > raw_entry.expires_at:
                self._safe_unlink(path)
                report.removed_expired += 1

        return report

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
            "manifest_checksum": entry.manifest_checksum,
            "cache_key": entry.cache_key,
        }
        serialized = json.dumps(payload, sort_keys=True, default=str)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.base_dir,
            delete=False,
            suffix=".tmp",
        ) as tmp:
            tmp.write(serialized)
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, path)

    def _read_entry_file(self, path: Path) -> CacheEntry | None:
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError, OSError:
            self._safe_unlink(path)
            return None

        try:
            created_at = datetime.fromisoformat(entry["created_at"])
            expires_at = (
                datetime.fromisoformat(entry["expires_at"]) if entry.get("expires_at") else None
            )
            payload = entry["payload"]
            expected_hash = str(entry.get("integrity_hash", ""))
        except KeyError, TypeError, ValueError:
            self._safe_unlink(path)
            return None

        actual_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        if expected_hash != actual_hash:
            self._safe_unlink(path)
            return None

        return CacheEntry(
            payload=payload,
            created_at=created_at,
            expires_at=expires_at,
            version=entry.get("version"),
            integrity_hash=expected_hash,
            manifest_checksum=entry.get("manifest_checksum"),
            cache_key=entry.get("cache_key"),
        )

    def _safe_unlink(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Failed to remove cache file: %s", path)
