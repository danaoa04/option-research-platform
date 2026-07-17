from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest
from alembic import command

from backend.data.integration.export import export_html, export_json
from backend.release.config import (
    load_release_config,
    load_release_profile,
    validate_build_policy,
)
from backend.release.manifest import (
    ReadinessStatus,
    clean_install_readiness_report,
    create_manifest,
    default_readiness_report,
)
from backend.release.migration import (
    ApplicationDataInitializer,
    MigrationManager,
    MigrationStatus,
)
from backend.release.provenance import collect_provenance


def test_canonical_versions_profiles_and_build_policy() -> None:
    config = load_release_config()
    assert config.versions.application_version == "1.0.0-rc.1"
    assert config.versions.frontend_version == config.versions.backend_version
    assert load_release_profile("release-candidate").telemetry is False
    with pytest.raises(ValueError, match="clean Git tree"):
        validate_build_policy("release-candidate", dirty=True)
    with pytest.raises(ValueError, match="matching version tag"):
        validate_build_policy("production-release", dirty=False, exact_tag="v0.9.0")
    validate_build_policy("production-release", dirty=False, exact_tag="v1.0.0-rc.1")
    with pytest.raises(ValueError, match="Unsupported release profile"):
        load_release_profile("unknown")


def test_provenance_and_manifest_are_redacted_and_consistent(tmp_path: Path) -> None:
    sidecar = tmp_path / "orp-backend"
    sidecar.write_bytes(b"synthetic executable fixture")
    provenance = collect_provenance(
        "test",
        root=tmp_path,
        timestamp="2026-07-17T00:00:00+00:00",
    )
    manifest = create_manifest(sidecar, "test", provenance=provenance)
    manifest.validate()
    encoded = json.dumps(manifest.serialize(), sort_keys=True)
    assert manifest.application_version == "1.0.0-rc.1"
    assert len(manifest.sidecar_checksum) == 64
    assert str(tmp_path) not in encoded
    assert "credential" not in encoded.lower()


def test_application_data_initialization_is_safe_and_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "application-data"
    result = ApplicationDataInitializer().initialize(root)
    repeated = ApplicationDataInitializer().initialize(root)
    assert result == repeated
    assert (root / "configuration.json").is_file()
    assert (root / "fixtures/manifest.json").is_file()
    assert (root / "crash-state.json").is_file()
    assert os.stat(root).st_mode & 0o077 == 0
    symlink = tmp_path / "unsafe"
    symlink.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        ApplicationDataInitializer().initialize(symlink)


def test_fresh_database_bootstrap_and_idempotent_startup(tmp_path: Path) -> None:
    initialized = ApplicationDataInitializer().initialize(tmp_path / "fresh")
    manager = MigrationManager(initialized.database)
    assert manager.status() is MigrationStatus.REQUIRED
    result = manager.migrate()
    assert result.previous_revision is None
    assert manager.status() is MigrationStatus.COMPLETED
    assert manager.migrate().current_revision == result.current_revision
    with sqlite3.connect(initialized.database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    assert "alembic_version" in tables
    assert "provider_runtime_state" in tables
    assert os.stat(initialized.database).st_mode & 0o077 == 0


def test_future_old_and_interrupted_migrations_are_blocked(tmp_path: Path) -> None:
    database = tmp_path / "versions.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES ('9999_future')")
    manager = MigrationManager(database)
    assert manager.status() is MigrationStatus.SCHEMA_TOO_NEW
    with pytest.raises(RuntimeError, match="newer"):
        manager.migrate()
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE alembic_version SET version_num = '0001_initial_schema'")
    assert manager.status() is MigrationStatus.SCHEMA_TOO_OLD
    manager.marker.write_text("migration_running", encoding="utf-8")
    assert manager.status() is MigrationStatus.RECOVERY_REQUIRED
    corrupt = tmp_path / "corrupt.sqlite3"
    corrupt.write_bytes(b"not a database")
    assert MigrationManager(corrupt).status() is MigrationStatus.RECOVERY_REQUIRED


def test_supported_upgrade_creates_verified_backup(tmp_path: Path) -> None:
    initialized = ApplicationDataInitializer().initialize(tmp_path / "upgrade")
    manager = MigrationManager(initialized.database)
    manager.migrate()
    command.downgrade(manager._alembic(initialized.database), "0021_provider_operations_completion")
    assert manager.status() is MigrationStatus.REQUIRED
    upgraded = manager.migrate()
    assert upgraded.previous_revision == "0021_provider_operations_completion"
    assert upgraded.backup_path is not None and upgraded.backup_path.is_file()
    assert upgraded.backup_checksum is not None
    metadata = json.loads(
        upgraded.backup_path.with_suffix(f"{upgraded.backup_path.suffix}.json").read_text(
            encoding="utf-8"
        )
    )
    assert metadata["sha256"] == upgraded.backup_checksum


def test_export_workspace_fixture_and_readiness_compatibility() -> None:
    first = export_json({"workspace_schema": 1, "secret": "hidden"})
    second = export_json({"secret": "hidden", "workspace_schema": 1})
    assert first == second
    assert '"secret":"***"' in first
    rendered = export_html("<Release>", {"version": "1.0.0-rc.1"})
    assert "&lt;Release&gt;" in rendered
    fixture = json.loads(Path("release/fixture-manifest.json").read_text(encoding="utf-8"))
    assert fixture["licensed_data_included"] is False
    report = default_readiness_report()
    assert report.release_candidate_ready is True
    assert report.public_release_ready is False
    assert any(item.status is ReadinessStatus.UNVALIDATED for item in report.categories)
    clean_install = clean_install_readiness_report()
    assert clean_install.release_candidate_ready is True
    assert clean_install.public_release_ready is False
    assert any(item.category == "source_tree_independence" for item in clean_install.categories)
