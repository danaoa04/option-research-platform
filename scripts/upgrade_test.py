"""Deterministic previous-version fixture upgrade validation."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from alembic import command

from backend.release.config import load_release_config
from backend.release.manifest import file_checksum
from backend.release.migration import ApplicationDataInitializer, MigrationManager
from backend.release.operations import database_integrity_report

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "release-artifacts" / "upgrade"
PORT = 18766


def sidecar_path() -> Path:
    return ROOT / "frontend/src-tauri/binaries/orp-backend-aarch64-apple-darwin"


def wait_for_health() -> dict[str, object]:
    for _ in range(120):
        try:
            with urlopen(f"http://127.0.0.1:{PORT}/v1/health", timeout=0.25) as response:
                payload = json.loads(response.read())
                if not isinstance(payload, dict):
                    raise SystemExit("Upgrade health payload was not an object")
                if payload.get("sidecar_ready"):
                    return payload
        except OSError:
            time.sleep(0.1)
    raise SystemExit("Upgrade sidecar readiness timed out")


def main() -> int:
    release = load_release_config()
    app_data = ARTIFACTS / "previous-app-data"
    if ARTIFACTS.exists():
        import shutil

        shutil.rmtree(ARTIFACTS)
    initialized = ApplicationDataInitializer(release).initialize(app_data)
    manager = MigrationManager(initialized.database, release)
    manager.migrate()
    command.downgrade(manager._alembic(initialized.database), "0021_provider_operations_completion")
    (initialized.workspace_directory / "fixture-workspace.orp-workspace").write_text(
        json.dumps(
            {
                "checksum": "sha256:previous-workspace",
                "payload": {"note": "synthetic previous workspace"},
                "schemaVersion": 1,
                "version": 1,
                "workspaceId": "previous-workspace",
                "workspaceType": "research",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (initialized.export_directory / "previous-report.json").write_text(
        json.dumps({"report_schema": "1.0.0", "synthetic": True}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (app_data / "release-metadata.json").write_text(
        json.dumps(
            {
                "application_version": "1.0.0-beta.fixture",
                "database_schema": "0021_provider_operations_completion",
                "sidecar_protocol": release.versions.sidecar_protocol_version,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    binary = sidecar_path()
    process = subprocess.Popen(
        [
            str(binary),
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
            "--app-data",
            str(app_data),
            "--release-profile",
            "release-candidate",
            "--api-version",
            release.versions.api_version,
            "--protocol-version",
            release.versions.sidecar_protocol_version,
            "--migration-policy",
            "automatic",
            "--fixture-mode",
        ],
        env={"PATH": "/usr/bin:/bin", "TMPDIR": "/tmp"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        health = wait_for_health()
    finally:
        process.terminate()
        process.wait(timeout=10)
    with sqlite3.connect(initialized.database) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    backups = sorted(app_data.glob(f"{release.database_filename}.pre-*.bak"))
    if not backups:
        raise SystemExit("Expected migration backup was not created")
    backup = backups[0]
    metadata = json.loads(backup.with_suffix(f"{backup.suffix}.json").read_text(encoding="utf-8"))
    evidence = {
        "backup": {
            "checksum_verified": metadata["sha256"] == file_checksum(backup),
            "metadata": metadata,
            "name": backup.name,
            "size_bytes": backup.stat().st_size,
        },
        "current_revision": revision,
        "database_integrity": database_integrity_report(initialized.database).serialize(),
        "health": {
            "migration_status": health["migration_status"],
            "version": health["version"],
        },
        "reports_preserved": (initialized.export_directory / "previous-report.json").is_file(),
        "second_startup_status": MigrationManager(initialized.database, release).status().value,
        "status": "passed",
        "workspaces_preserved": (
            initialized.workspace_directory / "fixture-workspace.orp-workspace"
        ).is_file(),
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "upgrade-evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("upgrade test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
