from __future__ import annotations

import json
import os
from pathlib import Path

from backend.release.manifest import file_checksum
from backend.release.migration import ApplicationDataInitializer, MigrationManager
from backend.release.operations import (
    cleanup_cache,
    database_integrity_report,
    reset_plan,
    restore_database_backup,
    rotate_log,
)


def test_database_integrity_backup_restore_and_reset_plan(tmp_path: Path) -> None:
    initialized = ApplicationDataInitializer().initialize(tmp_path / "app-data")
    manager = MigrationManager(initialized.database)
    manager.migrate()
    report = database_integrity_report(initialized.database)
    assert report.ready is True
    assert report.revision == "0022_provider_runtime_operations"
    backup = initialized.database.with_name("manual.bak")
    backup.write_bytes(initialized.database.read_bytes())
    metadata = {
        "release_version": "1.0.0-rc.1",
        "sha256": file_checksum(backup),
        "size_bytes": backup.stat().st_size,
        "source_revision": "0022_provider_runtime_operations",
        "target_revision": "0022_provider_runtime_operations",
    }
    backup.with_suffix(f"{backup.suffix}.json").write_text(
        json.dumps(metadata, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    initialized.database.write_bytes(b"corrupt")
    restored = restore_database_backup(
        initialized.database,
        backup,
        confirm="RESTORE_DATABASE_BACKUP",
    )
    assert restored.pre_restore_backup is not None
    assert restored.recovery_event.is_file()
    assert database_integrity_report(initialized.database).ready is True
    plan = reset_plan(initialized.root)
    assert "database backup" in plan["export_before_reset"]
    assert any("workspaces" in value for value in plan["user_data_retained_by_default"])


def test_cache_cleanup_and_log_rotation_preserve_user_data(tmp_path: Path) -> None:
    initialized = ApplicationDataInitializer().initialize(tmp_path / "app-data")
    workspace = initialized.workspace_directory / "saved.orp-workspace"
    workspace.write_text("{}", encoding="utf-8")
    cache_file = initialized.root / "cache" / "ephemeral.bin"
    cache_file.write_bytes(b"cache")
    removed = cleanup_cache(initialized.root, confirm="CLEAR_CACHE_ONLY")
    assert cache_file in removed
    assert workspace.is_file()
    log = initialized.log_directory / "sidecar.log"
    log.write_text("x" * 200, encoding="utf-8")
    rotated = rotate_log(log, maximum_bytes=20, retention_count=2)
    assert log.is_file()
    assert rotated[0].name == "sidecar.log.1"
    assert os.stat(log).st_mode & 0o077 == 0
