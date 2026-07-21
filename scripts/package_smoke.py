"""Launch the unsigned macOS app and validate packaged sidecar lifecycle."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/src-tauri/target/release/bundle/macos/Option Research Platform.app"
EXECUTABLE = APP / "Contents/MacOS/option-research-platform-desktop"
EVIDENCE = ROOT / "release-artifacts/smoke-test-evidence.json"
MANIFEST = APP / "Contents/Resources/release/release-manifest.json"


def port_closed(port: int) -> bool:
    with socket.socket() as connection:
        connection.settimeout(0.2)
        return connection.connect_ex(("127.0.0.1", port)) != 0


def main() -> int:
    if not EXECUTABLE.is_file():
        raise SystemExit("Packaged application executable is missing")
    smoke_home = ROOT / "release-artifacts/smoke-home"
    smoke_home.mkdir(parents=True, exist_ok=True)
    environment = {"HOME": str(smoke_home), "PATH": "/usr/bin:/bin", "TMPDIR": "/tmp"}
    process = subprocess.Popen(
        [str(EXECUTABLE)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    payload: dict[str, object] | None = None
    try:
        for _ in range(100):
            if process.poll() is not None:
                detail = process.stderr.read() if process.stderr else ""
                raise SystemExit(f"Packaged application exited before readiness: {detail[-500:]}")
            try:
                with urlopen("http://127.0.0.1:8765/v1/health", timeout=0.25) as response:
                    value = json.loads(response.read())
                    migration_completed = value.get("migration_status") == "migration_completed"
                    if value.get("sidecar_ready") and migration_completed:
                        payload = value
                        break
            except OSError:
                time.sleep(0.1)
        if payload is None:
            raise SystemExit("Packaged sidecar readiness timed out")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    for _ in range(50):
        if port_closed(8765):
            break
        time.sleep(0.1)
    else:
        raise SystemExit("Packaged sidecar remained after application shutdown")
    if not MANIFEST.is_file():
        raise SystemExit("Packaged release manifest is missing")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    provenance = payload.get("build_provenance")
    expected_provenance = manifest.get("build_provenance")
    if not isinstance(provenance, dict) or provenance != expected_provenance:
        raise SystemExit("Packaged health provenance does not match the release manifest")
    EVIDENCE.parent.mkdir(exist_ok=True)
    EVIDENCE.write_text(
        json.dumps(
            {
                "application_version": payload["version"],
                "api_version": payload["api_version"],
                "git_commit": provenance["git_commit"],
                "migration_status": payload["migration_status"],
                "release_profile": provenance["build_profile"],
                "sidecar_shutdown": "confirmed",
                "status": "passed",
                "target_architecture": provenance["target_architecture"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print("packaged smoke passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
