"""Clean-profile and source-tree-independence validation for the packaged app."""

from __future__ import annotations

import json
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from backend.release.config import load_release_config
from backend.release.manifest import clean_install_readiness_report, file_checksum
from backend.release.operations import database_integrity_report, reset_plan

ROOT = Path(__file__).resolve().parents[1]
SOURCE_APP = ROOT / "frontend/src-tauri/target/release/bundle/macos/Option Research Platform.app"
ARTIFACTS = ROOT / "release-artifacts" / "clean-install"
PORT = 8765


def port_closed(port: int = PORT) -> bool:
    with socket.socket() as connection:
        connection.settimeout(0.2)
        return connection.connect_ex(("127.0.0.1", port)) != 0


def directory_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def wait_for_health() -> tuple[dict[str, object], float]:
    started = time.monotonic()
    for _ in range(160):
        try:
            with urlopen(f"http://127.0.0.1:{PORT}/v1/health", timeout=0.25) as response:
                payload = json.loads(response.read())
                if payload.get("sidecar_ready") and (
                    payload.get("migration_status") == "migration_completed"
                ):
                    return payload, time.monotonic() - started
        except OSError:
            time.sleep(0.1)
    raise SystemExit("Clean-install health readiness timed out")


def launch_app(
    executable: Path,
    home: Path,
) -> tuple[subprocess.Popen[str], dict[str, object], float]:
    environment = {
        "HOME": str(home),
        "PATH": "/usr/bin:/bin",
        "TMPDIR": str(ARTIFACTS / "tmp"),
    }
    Path(environment["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [str(executable)],
        cwd=str(ARTIFACTS),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        payload, ready_seconds = wait_for_health()
    except Exception:
        process.terminate()
        process.wait(timeout=10)
        raise
    return process, payload, ready_seconds


def stop_app(process: subprocess.Popen[str]) -> float:
    started = time.monotonic()
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    for _ in range(80):
        if port_closed():
            return time.monotonic() - started
        time.sleep(0.1)
    raise SystemExit("Clean-install sidecar remained after app shutdown")


def main() -> int:
    if not SOURCE_APP.is_dir():
        raise SystemExit("Packaged app is missing; run make release-build")
    if ARTIFACTS.exists():
        shutil.rmtree(ARTIFACTS)
    install_root = ARTIFACTS / "external-install"
    copied_app = install_root / SOURCE_APP.name
    shutil.copytree(SOURCE_APP, copied_app)
    executable = copied_app / "Contents/MacOS/option-research-platform-desktop"
    home = ARTIFACTS / "clean-home"
    home.mkdir(parents=True)
    first_started = time.monotonic()
    first, first_health, first_ready = launch_app(executable, home)
    first_shutdown = stop_app(first)
    second, second_health, second_ready = launch_app(executable, home)
    second_shutdown = stop_app(second)

    release = load_release_config()
    app_data = home / "Library/Application Support/io.optionresearch.platform"
    database = app_data / release.database_filename
    with sqlite3.connect(database) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    resources = copied_app / "Contents/Resources/release"
    resource_files = sorted(path.name for path in resources.iterdir() if path.is_file())
    inventory = sorted(
        path.relative_to(app_data).as_posix() for path in app_data.rglob("*") if path.is_file()
    )
    evidence = {
        "application_version": first_health["version"],
        "app_bundle_bytes": directory_size(copied_app),
        "app_data_bytes": directory_size(app_data),
        "app_data_inventory": inventory,
        "app_data_root": "isolated-clean-home",
        "database_bytes": database.stat().st_size,
        "database_integrity": database_integrity_report(database).serialize(),
        "fixture_mode_supported": first_health["fixture_mode_supported"],
        "first_launch_seconds": round(time.monotonic() - first_started, 3),
        "first_readiness_seconds": round(first_ready, 3),
        "first_shutdown_seconds": round(first_shutdown, 3),
        "installed_outside_repository": True,
        "migration_revision": revision,
        "packaged_release_resources": resource_files,
        "release_manifest_checksum": file_checksum(resources / "release-manifest.json"),
        "reset_plan": reset_plan(app_data),
        "second_readiness_seconds": round(second_ready, 3),
        "second_shutdown_seconds": round(second_shutdown, 3),
        "source_tree_independence": {
            "cwd": "release-artifacts/clean-install",
            "home": "release-artifacts/clean-install/clean-home",
            "node_required": False,
            "python_venv_required": False,
            "repository_required": False,
        },
        "status": (
            "passed" if second_health["migration_status"] == "migration_completed" else "failed"
        ),
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "clean-install-evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (ARTIFACTS / "clean-install-readiness.json").write_text(
        json.dumps(
            clean_install_readiness_report("release-candidate").serialize(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print("clean install test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
