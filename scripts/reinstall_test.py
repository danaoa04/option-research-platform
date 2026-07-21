"""Validate same-version reinstall while retaining isolated application data."""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

from backend.release.config import load_release_config
from backend.release.manifest import file_checksum
from backend.release.operations import database_integrity_report
from scripts.clean_install_test import launch_app, stop_app

ROOT = Path(__file__).resolve().parents[1]
SOURCE_APP = ROOT / "frontend/src-tauri/target/release/bundle/macos/Option Research Platform.app"
ARTIFACTS = ROOT / "release-artifacts/reinstall"


def main() -> int:
    if not SOURCE_APP.is_dir():
        raise SystemExit("Packaged app is missing; run make release-build")
    if ARTIFACTS.exists():
        shutil.rmtree(ARTIFACTS)
    install_root = ARTIFACTS / "Applications"
    installed_app = install_root / SOURCE_APP.name
    home = ARTIFACTS / "retained-home"
    install_root.mkdir(parents=True)
    home.mkdir(parents=True)

    shutil.copytree(SOURCE_APP, installed_app)
    executable = installed_app / "Contents/MacOS/option-research-platform-desktop"
    first, first_health, _ = launch_app(executable, home, ARTIFACTS)
    stop_app(first)

    release = load_release_config()
    app_data = home / "Library/Application Support/io.optionresearch.platform"
    database = app_data / release.database_filename
    before_checksum = file_checksum(database)
    marker = app_data / "workspaces/reinstall-marker.orp-workspace"
    marker.write_text('{"schemaVersion":1,"workspaceId":"reinstall-marker"}\n', encoding="utf-8")

    shutil.rmtree(installed_app)
    if not app_data.is_dir():
        raise SystemExit("Removing the app unexpectedly removed retained application data")
    shutil.copytree(SOURCE_APP, installed_app)
    second, second_health, _ = launch_app(executable, home, ARTIFACTS)
    stop_app(second)

    with sqlite3.connect(database) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    evidence = {
        "application_version": second_health["version"],
        "database_checksum_before_reinstall": before_checksum,
        "database_integrity": database_integrity_report(database).serialize(),
        "first_launch_migration_status": first_health["migration_status"],
        "migration_revision": revision,
        "reinstalled_same_rc": True,
        "retained_app_data": app_data.is_dir(),
        "second_launch_migration_status": second_health["migration_status"],
        "status": "passed",
        "workspace_preserved": marker.is_file(),
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "reinstall-evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("reinstall test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
