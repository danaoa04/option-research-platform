"""Build and validate the deterministic PyInstaller Tauri sidecar."""

from __future__ import annotations

import importlib
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
TAURI_BIN = ROOT / "frontend" / "src-tauri" / "binaries"


def target_triple() -> str:
    machine = {"arm64": "aarch64", "x86_64": "x86_64"}.get(platform.machine())
    system = {
        "Darwin": "apple-darwin",
        "Linux": "unknown-linux-gnu",
        "Windows": "pc-windows-msvc",
    }.get(platform.system())
    if machine is None or system is None:
        raise SystemExit("Unsupported sidecar build architecture")
    return f"{machine}-{system}"


def smoke_test(binary: Path) -> None:
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    smoke_data = ROOT / "build" / "sidecar" / "smoke-data"
    process = subprocess.Popen(
        [
            str(binary),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--app-data",
            str(smoke_data),
            "--fixture-mode",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        for _ in range(80):
            if process.poll() is not None:
                detail = process.stderr.read() if process.stderr else ""
                raise SystemExit(f"Sidecar exited before readiness: {detail[-500:]}")
            try:
                with urlopen(f"http://127.0.0.1:{port}/v1/health", timeout=0.25) as response:
                    if response.status == 200 and b'"sidecar_ready":true' in response.read():
                        return
            except OSError:
                time.sleep(0.1)
        raise SystemExit("Sidecar health smoke test timed out")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main() -> int:
    build_root = ROOT / "build" / "sidecar"
    os.environ["PYINSTALLER_CONFIG_DIR"] = str(build_root / "config")
    try:
        pyinstaller = importlib.import_module("PyInstaller.__main__")
    except ImportError as exc:
        raise SystemExit(
            "PyInstaller is required for backend-sidecar; install requirements-sidecar.txt"
        ) from exc
    dist_root = build_root / "dist"
    pyinstaller.run(
        [
            str(ROOT / "backend" / "sidecar.spec"),
            "--clean",
            "--noconfirm",
            f"--distpath={dist_root}",
            f"--workpath={build_root / 'work'}",
        ]
    )
    suffix = ".exe" if os.name == "nt" else ""
    source = dist_root / f"orp-backend{suffix}"
    target = TAURI_BIN / f"orp-backend-{target_triple()}{suffix}"
    TAURI_BIN.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    version = subprocess.run(
        [str(target), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if version != "sprint-11f.2-local":
        raise SystemExit(f"Unexpected sidecar version: {version}")
    smoke_test(target)
    print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
