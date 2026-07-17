"""Deterministic Version 1 release audit and artifact commands."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

from backend.release.config import (
    load_release_config,
    load_release_profile,
    validate_build_policy,
)
from backend.release.manifest import create_manifest, default_readiness_report, file_checksum
from backend.release.provenance import collect_provenance

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "release-artifacts"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"Expected JSON object: {path}")
    return value


def target_triple() -> str:
    machine = {"arm64": "aarch64", "x86_64": "x86_64"}.get(platform.machine())
    system = {"Darwin": "apple-darwin", "Linux": "unknown-linux-gnu"}.get(platform.system())
    if machine is None or system is None:
        raise SystemExit("Unsupported release architecture")
    return f"{machine}-{system}"


def sidecar_path() -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return ROOT / "frontend/src-tauri/binaries" / f"orp-backend-{target_triple()}{suffix}"


def _run(
    args: list[str],
    *,
    check: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=text)


def _binary_strings(path: Path) -> str:
    try:
        return _run(["strings", "-a", str(path)], check=False).stdout
    except OSError:
        return ""


def _scan_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return _binary_strings(path)


def _artifact_leak_scan(paths: list[Path]) -> None:
    root_text = ROOT.as_posix()
    home = Path.home().as_posix()
    username = Path.home().name
    secret = re.compile(
        r"(api[_-]?key|secret[_-]?key|password|credential|token)\s*[:=]"
        r"|(^|/)\.env(?:$|[./])",
        re.IGNORECASE,
    )
    violations: list[str] = []
    for base in paths:
        candidates = (
            [base] if base.is_file() else [path for path in base.rglob("*") if path.is_file()]
        )
        for path in candidates:
            relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
            if ".git" in path.parts:
                continue
            payload = _scan_text(path)
            if root_text in payload or home in payload:
                violations.append(f"{relative}: local path")
            if username and re.search(rf"/Users/{re.escape(username)}\b", payload):
                violations.append(f"{relative}: local username")
            if secret.search(payload):
                violations.append(f"{relative}: secret marker")
    if violations:
        raise SystemExit(f"Release artifact leak scan failed: {violations[:10]}")


def _directory_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _sidecar_contract(binary: Path) -> None:
    expected = load_release_config().versions.application_version
    version = _run([str(binary), "--version"]).stdout.strip()
    if version != expected:
        raise SystemExit(f"Unexpected sidecar version: {version}")


def version_check() -> None:
    expected = load_release_config().versions.application_version
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    cargo = tomllib.loads((ROOT / "frontend/src-tauri/Cargo.toml").read_text(encoding="utf-8"))
    cargo_lock = tomllib.loads((ROOT / "frontend/src-tauri/Cargo.lock").read_text(encoding="utf-8"))
    cargo_locked = next(
        item["version"]
        for item in cargo_lock["package"]
        if item["name"] == "option-research-platform-desktop"
    )
    package_lock = _json(ROOT / "frontend/package-lock.json")
    values = {
        "python": pyproject["project"]["version"],
        "poetry": pyproject["tool"]["poetry"]["version"],
        "frontend": _json(ROOT / "frontend/package.json")["version"],
        "cargo": cargo["package"]["version"],
        "cargo lock": cargo_locked,
        "tauri": _json(ROOT / "frontend/src-tauri/tauri.conf.json")["version"],
        "npm lock": package_lock["packages"][""]["version"],
    }
    mismatches = {name: value for name, value in values.items() if value != expected}
    frontend_metadata = (ROOT / "frontend/src/config/releaseMetadata.ts").read_text(
        encoding="utf-8"
    )
    if f'applicationVersion: "{expected}"' not in frontend_metadata:
        mismatches["frontend metadata"] = "not synchronized"
    if mismatches:
        raise SystemExit(f"Version mismatch: {mismatches}")
    print(f"versions synchronized: {expected}")


def git_policy(profile: str) -> None:
    load_release_profile(profile)
    dirty = bool(_run(["git", "status", "--porcelain"]).stdout)
    tag: str | None = None
    if profile == "production-release":
        tag = _run(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            check=False,
        ).stdout.strip()
    try:
        validate_build_policy(profile, dirty=dirty, exact_tag=tag)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def lock_audit() -> None:
    required = (
        ROOT / "requirements.lock",
        ROOT / "requirements-sidecar.lock",
        ROOT / "frontend/package-lock.json",
        ROOT / "frontend/src-tauri/Cargo.lock",
    )
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing dependency locks: {', '.join(missing)}")


def release_audit() -> None:
    version_check()
    lock_audit()
    config = load_release_config()
    for profile in (
        "development",
        "test",
        "offline-demo",
        "release-candidate",
        "production-release",
    ):
        load_release_profile(profile)
    if config.supported_architectures != ("aarch64-apple-darwin",):
        raise SystemExit("Sprint 12A supports only the audited Apple Silicon target")
    fixture_checksums = _json(ROOT / "release/fixture-checksums.json")
    for filename, checksum in fixture_checksums.items():
        fixture = ROOT / "release" / filename
        if not fixture.is_file() or file_checksum(fixture) != checksum:
            raise SystemExit(f"Fixture integrity failed: {filename}")
    for notice in (ROOT / "LICENSE", ROOT / "docs/Third_Party_Notices.md"):
        if not notice.is_file():
            raise SystemExit(f"Missing licence notice: {notice.name}")
    print("release audit passed")


def write_artifacts(profile: str) -> None:
    started = time.monotonic()
    binary = sidecar_path()
    if not binary.is_file():
        raise SystemExit("Sidecar is missing; run make backend-sidecar")
    _sidecar_contract(binary)
    ARTIFACTS.mkdir(exist_ok=True)
    provenance = collect_provenance(profile)
    manifest = create_manifest(binary, profile, provenance=provenance)
    readiness = default_readiness_report(profile)
    values = {
        "release-manifest.json": manifest.serialize(),
        "build-provenance.json": provenance.serialize(),
        "release-readiness.json": readiness.serialize(),
        "checksums.json": {binary.name: file_checksum(binary)},
    }
    for name, value in values.items():
        (ARTIFACTS / name).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    shutil.copy2(binary, ARTIFACTS / binary.name)
    app = ROOT / "frontend/src-tauri/target/release/bundle/macos/Option Research Platform.app"
    if app.is_dir():
        resources = app / "Contents/Resources/release"
        resources.mkdir(parents=True, exist_ok=True)
        for name in ("release-manifest.json", "build-provenance.json", "release-readiness.json"):
            shutil.copy2(ARTIFACTS / name, resources / name)
        shutil.copy2(ROOT / "LICENSE", resources / "LICENSE")
        shutil.copy2(
            ROOT / "docs/Third_Party_Notices.md",
            resources / "Third_Party_Notices.md",
        )
        packaged = ARTIFACTS / "application" / app.name
        if packaged.exists():
            shutil.rmtree(packaged)
        packaged.parent.mkdir(exist_ok=True)
        shutil.copytree(app, packaged)
    performance = {
        "application_bundle_bytes": _directory_size(app) if app.is_dir() else None,
        "artifact_generation_seconds": round(time.monotonic() - started, 3),
        "fixture_manifest_bytes": (ROOT / "release/fixture-manifest.json").stat().st_size,
        "sidecar_bytes": binary.stat().st_size,
        "status": "measured",
    }
    (ARTIFACTS / "performance.json").write_text(
        json.dumps(performance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _artifact_leak_scan([ARTIFACTS / name for name in values] + [ARTIFACTS / "performance.json"])
    print(ARTIFACTS.relative_to(ROOT))


def bundle_check() -> None:
    app = ROOT / "frontend/src-tauri/target/release/bundle/macos/Option Research Platform.app"
    if not app.is_dir():
        raise SystemExit("macOS application bundle is missing")
    files = [path.relative_to(app).as_posix() for path in app.rglob("*") if path.is_file()]
    required = {
        "Contents/Info.plist",
        "Contents/MacOS/orp-backend",
        "Contents/Resources/release/LICENSE",
        "Contents/Resources/release/Third_Party_Notices.md",
        "Contents/Resources/release/release-manifest.json",
    }
    if not required.issubset(files):
        raise SystemExit(f"Bundle is missing required files: {sorted(required - set(files))}")
    forbidden = re.compile(r"(^|/)(\.env|__pycache__|\.pytest_cache)(/|$)|\.(py|pyc|map)$")
    violations = [value for value in files if forbidden.search(value)]
    if violations:
        raise SystemExit(f"Forbidden bundle content: {violations}")
    sidecar = app / "Contents/MacOS/orp-backend"
    executable = app / "Contents/MacOS/option-research-platform-desktop"
    for binary in (sidecar, executable):
        architecture = _run(["file", str(binary)]).stdout
        if "arm64" not in architecture:
            raise SystemExit(f"Bundle architecture is not Apple Silicon: {binary.name}")
    _artifact_leak_scan([app])
    print(f"bundle inspection passed: {len(files)} files")


def main() -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "command",
        choices=(
            "version-check",
            "release-audit",
            "manifest",
            "release-check",
            "bundle-check",
            "policy",
        ),
    )
    parser.add_argument("--profile", default="development")
    arguments = parser.parse_args()
    if arguments.command == "version-check":
        version_check()
    elif arguments.command == "release-audit":
        release_audit()
    elif arguments.command == "manifest":
        write_artifacts(arguments.profile)
    elif arguments.command == "bundle-check":
        bundle_check()
    elif arguments.command == "policy":
        git_policy(arguments.profile)
    else:
        release_audit()
        write_artifacts(arguments.profile)
        if arguments.profile in {"release-candidate", "production-release"}:
            git_policy(arguments.profile)
    return 0


if __name__ == "__main__":
    sys.exit(main())
