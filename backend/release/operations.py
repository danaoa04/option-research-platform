"""Clean-install, recovery, and retention helpers for packaged releases."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import ReleaseConfig, load_release_config
from .migration import MigrationManager, MigrationStatus


@dataclass(slots=True, frozen=True)
class DatabaseIntegrityReport:
    database: Path
    exists: bool
    readable: bool
    integrity_check: str
    revision: str | None
    required_tables_present: bool
    status: MigrationStatus

    @property
    def ready(self) -> bool:
        return (
            self.exists
            and self.readable
            and self.integrity_check == "ok"
            and self.required_tables_present
            and self.status is MigrationStatus.COMPLETED
        )

    def serialize(self) -> dict[str, Any]:
        return {
            "database": self.database.name,
            "exists": self.exists,
            "integrity_check": self.integrity_check,
            "readable": self.readable,
            "ready": self.ready,
            "required_tables_present": self.required_tables_present,
            "revision": self.revision,
            "status": self.status.value,
        }


@dataclass(slots=True, frozen=True)
class RestoreResult:
    restored_database: Path
    source_backup: Path
    pre_restore_backup: Path | None
    checksum: str
    recovery_event: Path

    def serialize(self) -> dict[str, Any]:
        return {
            "checksum": self.checksum,
            "pre_restore_backup": self.pre_restore_backup.name if self.pre_restore_backup else None,
            "recovery_event": self.recovery_event.name,
            "restored_database": self.restored_database.name,
            "source_backup": self.source_backup.name,
        }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def database_integrity_report(
    database: Path,
    *,
    config: ReleaseConfig | None = None,
) -> DatabaseIntegrityReport:
    release = config or load_release_config()
    manager = MigrationManager(database, release)
    exists = database.is_file()
    if not exists:
        return DatabaseIntegrityReport(
            database,
            False,
            False,
            "missing",
            None,
            False,
            MigrationStatus.REQUIRED,
        )
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            tables = {
                str(row[0])
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
    except OSError, sqlite3.DatabaseError:
        return DatabaseIntegrityReport(
            database,
            True,
            False,
            "unreadable",
            manager.revision(),
            False,
            manager.status(),
        )
    required = {"alembic_version", "provider_runtime_state", "workspace_metadata"}
    return DatabaseIntegrityReport(
        database,
        True,
        True,
        integrity,
        manager.revision(),
        required.issubset(tables),
        manager.status(),
    )


def restore_database_backup(
    database: Path,
    backup: Path,
    *,
    confirm: str,
) -> RestoreResult:
    if confirm != "RESTORE_DATABASE_BACKUP":
        raise ValueError("Explicit restore confirmation is required")
    metadata_path = backup.with_suffix(f"{backup.suffix}.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    checksum = sha256(backup)
    if metadata.get("sha256") != checksum:
        raise ValueError("Backup checksum mismatch")
    pre_restore: Path | None = None
    if database.exists():
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        pre_restore = database.with_name(f"{database.name}.pre-restore-{stamp}.bak")
        shutil.copy2(database, pre_restore)
        os.chmod(pre_restore, stat.S_IRUSR | stat.S_IWUSR)
    temporary = database.with_name(f".{database.name}.restore.tmp")
    try:
        shutil.copy2(backup, temporary)
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
        temporary.replace(database)
    finally:
        temporary.unlink(missing_ok=True)
    event = database.with_name("recovery-events.jsonl")
    payload = {
        "at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "backup": backup.name,
        "checksum": checksum,
        "event": "database_backup_restored",
        "pre_restore_backup": pre_restore.name if pre_restore else None,
        "restart_required": True,
    }
    with event.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")
    os.chmod(event, stat.S_IRUSR | stat.S_IWUSR)
    return RestoreResult(database, backup, pre_restore, checksum, event)


def cleanup_cache(root: Path, *, confirm: str) -> list[Path]:
    if confirm != "CLEAR_CACHE_ONLY":
        raise ValueError("Explicit cache cleanup confirmation is required")
    cache = root / "cache"
    removed: list[Path] = []
    if not cache.exists():
        return removed
    for path in sorted(cache.rglob("*"), reverse=True):
        if path.is_file() or path.is_symlink():
            path.unlink()
            removed.append(path)
        elif path.is_dir():
            path.rmdir()
            removed.append(path)
    return removed


def rotate_log(log: Path, *, maximum_bytes: int, retention_count: int) -> list[Path]:
    if not log.exists() or log.stat().st_size <= maximum_bytes:
        return []
    rotated: list[Path] = []
    for index in range(retention_count, 0, -1):
        source = log.with_name(f"{log.name}.{index}")
        target = log.with_name(f"{log.name}.{index + 1}")
        if source.exists():
            if index == retention_count:
                source.unlink()
            else:
                source.replace(target)
                rotated.append(target)
    first = log.with_name(f"{log.name}.1")
    log.replace(first)
    log.write_text("", encoding="utf-8")
    os.chmod(log, stat.S_IRUSR | stat.S_IWUSR)
    rotated.append(first)
    return rotated


def reset_plan(root: Path) -> dict[str, list[str]]:
    return {
        "destructive_requires_confirmation": [
            "create fresh database",
            "remove all local application data",
        ],
        "export_before_reset": [
            "workspace export",
            "report export",
            "diagnostics export",
            "database backup",
            "configuration export",
        ],
        "safe_without_user_data_removal": [
            "clear cache",
            "reset UI settings",
            "reset offline fixtures",
        ],
        "user_data_retained_by_default": [
            "workspaces/",
            "exports/",
            "option-research-platform.sqlite3",
        ],
    }
