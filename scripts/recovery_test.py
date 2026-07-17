"""Deterministic recovery and rollback scenario validation."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from alembic import command

from backend.release.config import load_release_config
from backend.release.manifest import file_checksum
from backend.release.migration import ApplicationDataInitializer, MigrationManager, MigrationStatus
from backend.release.operations import (
    cleanup_cache,
    database_integrity_report,
    restore_database_backup,
    rotate_log,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "release-artifacts" / "recovery"


def seed_revision(database: Path, revision: str) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES (?)", (revision,))


def main() -> int:
    if ARTIFACTS.exists():
        import shutil

        shutil.rmtree(ARTIFACTS)
    ARTIFACTS.mkdir(parents=True)
    release = load_release_config()
    root = ARTIFACTS / "app-data"
    initialized = ApplicationDataInitializer(release).initialize(root)
    manager = MigrationManager(initialized.database, release)
    manager.migrate()
    command.downgrade(manager._alembic(initialized.database), "0021_provider_operations_completion")
    upgraded = manager.migrate()
    if upgraded.backup_path is None:
        raise SystemExit("Expected backup for recovery restore scenario")
    checksum = file_checksum(upgraded.backup_path)
    restored = restore_database_backup(
        initialized.database,
        upgraded.backup_path,
        confirm="RESTORE_DATABASE_BACKUP",
    )
    future_db = ARTIFACTS / "future.sqlite3"
    seed_revision(future_db, "9999_future")
    old_db = ARTIFACTS / "old.sqlite3"
    seed_revision(old_db, "0001_initial_schema")
    corrupt_db = ARTIFACTS / "corrupt.sqlite3"
    corrupt_db.write_bytes(b"not a sqlite database")
    interrupted = ARTIFACTS / "interrupted.sqlite3"
    interrupted.write_bytes(initialized.database.read_bytes())
    interrupted_manager = MigrationManager(interrupted, release)
    interrupted_manager.marker.write_text("migration_running", encoding="utf-8")
    (initialized.root / "cache" / "temporary.bin").write_bytes(b"cache")
    removed_cache = cleanup_cache(initialized.root, confirm="CLEAR_CACHE_ONLY")
    log = initialized.log_directory / "sidecar.log"
    log.write_text("x" * 2048, encoding="utf-8")
    rotated = rotate_log(log, maximum_bytes=100, retention_count=2)
    evidence = {
        "cache_cleanup": {
            "database_retained": initialized.database.is_file(),
            "removed_count": len(removed_cache),
            "workspaces_retained": initialized.workspace_directory.is_dir(),
        },
        "corrupt_database": database_integrity_report(corrupt_db).serialize(),
        "future_schema_status": MigrationManager(future_db, release).status().value,
        "interrupted_migration_status": interrupted_manager.status().value,
        "log_rotation": [path.name for path in rotated],
        "old_schema_status": MigrationManager(old_db, release).status().value,
        "restore": restored.serialize(),
        "restore_checksum_verified": checksum == restored.checksum,
        "status": "passed",
    }
    expected = {
        "future_schema_status": MigrationStatus.SCHEMA_TOO_NEW.value,
        "interrupted_migration_status": MigrationStatus.RECOVERY_REQUIRED.value,
        "old_schema_status": MigrationStatus.SCHEMA_TOO_OLD.value,
    }
    for key, value in expected.items():
        if evidence[key] != value:
            raise SystemExit(f"Unexpected recovery evidence {key}: {evidence[key]}")
    (ARTIFACTS / "recovery-evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("recovery test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
