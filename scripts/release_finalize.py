"""Sprint 12F macOS release-candidate finalization commands.

The signing and notarization commands deliberately fail closed when credentials
are unavailable. Evidence contains status and public identifiers only; secret
material is never serialized.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.release.config import load_release_config
from backend.release.manifest import file_checksum
from backend.release.provenance import collect_provenance
from scripts.release_tool import bundle_check

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/src-tauri/target/release/bundle/macos/Option Research Platform.app"
EXECUTABLE = APP / "Contents/MacOS/option-research-platform-desktop"
SIDECAR = APP / "Contents/MacOS/orp-backend"
FINAL = ROOT / "release-artifacts/final-rc"


@dataclass(slots=True, frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def _run(args: list[str], *, cwd: Path = ROOT) -> CommandResult:
    result = subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _write(name: str, value: dict[str, Any]) -> Path:
    FINAL.mkdir(parents=True, exist_ok=True)
    path = FINAL / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _architecture(path: Path) -> str:
    result = _run(["file", str(path)])
    if result.returncode != 0:
        raise SystemExit(f"Unable to inspect architecture: {path.name}")
    if "arm64" not in result.stdout:
        raise SystemExit(f"Expected Apple Silicon binary: {path.name}")
    return "arm64"


def _identity_status() -> tuple[str | None, str]:
    result = _run(["security", "find-identity", "-v", "-p", "codesigning"])
    matches = re.findall(r'\d+\) [0-9A-F]+ "([^"]+)"', result.stdout)
    developer_ids = [value for value in matches if value.startswith("Developer ID Application:")]
    configured = os.environ.get("APPLE_SIGNING_IDENTITY")
    if configured and configured in developer_ids:
        return configured, "available"
    if developer_ids:
        return developer_ids[0], "available"
    return None, "blocked"


def _notary_configuration() -> str:
    profile = os.environ.get("APPLE_NOTARYTOOL_PROFILE")
    api_values = (
        os.environ.get("APPLE_API_KEY_PATH"),
        os.environ.get("APPLE_API_KEY_ID"),
        os.environ.get("APPLE_API_ISSUER"),
    )
    if profile:
        return "keychain_profile"
    if all(api_values):
        return "app_store_connect_api_key"
    return "unavailable"


def signing_status() -> dict[str, Any]:
    identity, prerequisite = _identity_status()
    signature = _run(["codesign", "--display", "--verbose=4", str(APP)])
    signature_text = f"{signature.stdout}\n{signature.stderr}"
    signed = (
        signature.returncode == 0
        and "Signature=adhoc" not in signature_text
        and "TeamIdentifier=not set" not in signature_text
    )
    verification = _run(["codesign", "--verify", "--deep", "--strict", str(APP)])
    signed_and_valid = signed and verification.returncode == 0
    team_match = re.search(r"TeamIdentifier=([^\s]+)", signature_text)
    executable_checksum = file_checksum(EXECUTABLE) if EXECUTABLE.is_file() else None
    signing: dict[str, Any] = {
        "app_signature_valid": signed_and_valid,
        "developer_id_identity": identity or "unavailable",
        "hardened_runtime_configured": True,
        "identity_prerequisite": prerequisite,
        "non_default_entitlements": [],
        "status": "passed" if signed_and_valid else "blocked",
        "team_id": team_match.group(1) if signed and team_match else "unavailable",
    }
    previous_notarization = FINAL / "notarization-status.json"
    notarization: dict[str, Any]
    if previous_notarization.is_file():
        value = json.loads(previous_notarization.read_text(encoding="utf-8"))
        notarization = value if isinstance(value, dict) else {}
    else:
        notarization = {}
    if not (
        notarization.get("status") == "passed"
        and notarization.get("executable_sha256") == executable_checksum
        and signed_and_valid
    ):
        notarization = {
            "credential_mode": _notary_configuration(),
            "executable_sha256": executable_checksum,
            "status": "unvalidated" if signed_and_valid else "blocked",
            "submission_id": None,
            "ticket_stapled": False,
        }
    gatekeeper_result = _run(["spctl", "--assess", "--type", "execute", "--verbose=4", str(APP)])
    gatekeeper = {
        "assessment": "accepted" if gatekeeper_result.returncode == 0 else "rejected",
        "exit_code": gatekeeper_result.returncode,
        "first_launch_validation": "unvalidated",
        "status": "passed" if gatekeeper_result.returncode == 0 else "blocked",
    }
    _write("signing-status.json", signing)
    _write("notarization-status.json", notarization)
    _write("gatekeeper-status.json", gatekeeper)
    return {"gatekeeper": gatekeeper, "notarization": notarization, "signing": signing}


def browser_e2e() -> dict[str, Any]:
    result = _run(["npm", "run", "test:e2e"], cwd=ROOT / "frontend")
    output = f"{result.stdout}\n{result.stderr}"

    def count(label: str) -> int:
        match = re.search(rf"(\d+) {label}", output)
        return int(match.group(1)) if match else 0

    evidence = {
        "browser": "Playwright Chromium",
        "command": "npm run test:e2e",
        "environment": f"macOS {platform.mac_ver()[0]} {platform.machine()}",
        "exit_code": result.returncode,
        "failed": count("failed"),
        "passed": count("passed"),
        "skipped": count("skipped"),
        "status": "passed" if result.returncode == 0 else "failed",
    }
    _write("final-e2e.json", evidence)
    if result.returncode != 0:
        print(output[-4000:])
        raise SystemExit("Browser E2E failed")
    print(f"browser E2E passed: {evidence['passed']} tests")
    return evidence


def desktop_smoke() -> dict[str, Any]:
    result = _run([sys.executable, "-m", "scripts.package_smoke"])
    source = ROOT / "release-artifacts/smoke-test-evidence.json"
    packaged = json.loads(source.read_text(encoding="utf-8")) if source.is_file() else {}
    evidence = {
        "automated": {
            "application_launch": packaged.get("status") == "passed",
            "fixture_mode": True,
            "health_readiness": packaged.get("migration_status") == "migration_completed",
            "sidecar_launch": packaged.get("status") == "passed",
            "sidecar_shutdown": packaged.get("sidecar_shutdown") == "confirmed",
        },
        "browser_fixture_routes": "covered by final-e2e.json",
        "native_file_dialog": "unvalidated",
        "native_ui_automation": "unsupported by the current harness",
        "status": "passed_with_warnings" if result.returncode == 0 else "failed",
        "webgl_or_fallback": "covered by browser E2E",
        "workspace_native_reopen": "unvalidated",
    }
    _write("desktop-smoke.json", evidence)
    if result.returncode != 0:
        detail = f"{result.stdout}\n{result.stderr}"
        print(detail[-4000:])
        raise SystemExit("Packaged desktop smoke failed")
    print("packaged desktop smoke passed with native automation warnings")
    return evidence


def manual_rc_evidence() -> dict[str, Any]:
    tasks = [
        "launch packaged RC",
        "verify diagnostics UI",
        "open offline demo",
        "complete quick start",
        "build example strategy",
        "run example backtest",
        "inspect risk scenario",
        "inspect volatility surface",
        "import example workspace",
        "save and reopen workspace",
        "export report",
        "restart application",
        "confirm persistence",
        "generate diagnostic bundle",
    ]
    evidence = {
        "automated_coverage": [
            "packaged launch, sidecar health, and shutdown",
            "browser fixture navigation, strategy, backtest, risk, volatility, and diagnostics",
            "clean-profile restart and persistence checks",
        ],
        "manual_observations": [],
        "status": "unvalidated",
        "tasks": [{"name": task, "status": "unvalidated"} for task in tasks],
        "warning": (
            "No human-operated desktop dogfood session was performed by this automation run."
        ),
    }
    _write("manual-rc-validation.json", evidence)
    return evidence


def _copy_evidence(source: Path, destination: str) -> str:
    target = FINAL / destination
    if not source.is_file():
        return "missing"
    FINAL.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return "passed"


def _artifact_scan() -> dict[str, Any]:
    bundle_check()
    forbidden_names = re.compile(
        r"(^|/)(\.env(?:\..*)?|__pycache__|\.pytest_cache|\.git|node_modules|target)(/|$)"
        r"|\.(pem|p12|key|py|pyc|map)$",
        re.IGNORECASE,
    )
    files = [path.relative_to(APP).as_posix() for path in APP.rglob("*") if path.is_file()]
    violations = [name for name in files if forbidden_names.search(name)]
    evidence = {
        "bundle_file_count": len(files),
        "forbidden_files": violations,
        "licensed_market_data_detected": False,
        "local_path_scan": "passed by bundle-check",
        "status": "passed" if not violations else "failed",
    }
    _write("artifact-scan.json", evidence)
    if violations:
        raise SystemExit(f"Forbidden release files: {violations}")
    return evidence


def _licence_scan() -> dict[str, Any]:
    required = [
        ROOT / "LICENSE",
        ROOT / "docs/Third_Party_Notices.md",
        ROOT / "requirements.lock",
        ROOT / "requirements-sidecar.lock",
        ROOT / "frontend/package-lock.json",
        ROOT / "frontend/src-tauri/Cargo.lock",
        ROOT / "release/fixture-manifest.json",
    ]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.is_file()]
    evidence = {
        "fixture_classification": "project-created synthetic data",
        "legal_review": "unvalidated",
        "missing": missing,
        "notice_inventory": [path.relative_to(ROOT).as_posix() for path in required],
        "status": "ready_with_warnings" if not missing else "incomplete",
        "warning": "Engineering inventory only; no legal opinion is claimed.",
    }
    _write("licence-scan.json", evidence)
    if missing:
        raise SystemExit(f"Missing licence inputs: {missing}")
    return evidence


def _distribution_archive(version: str) -> Path:
    archive = FINAL / f"option-research-platform-{version}-macos-arm64.zip"
    if archive.exists():
        archive.unlink()
    result = _run(
        [
            "/usr/bin/ditto",
            "-c",
            "-k",
            "--sequesterRsrc",
            "--keepParent",
            str(APP),
            str(archive),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(f"Unable to create release archive: {result.stderr[-500:]}")
    return archive


def _read_status(name: str) -> dict[str, Any]:
    path = FINAL / name
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def finalize() -> dict[str, Any]:
    if not APP.is_dir() or not EXECUTABLE.is_file() or not SIDECAR.is_file():
        raise SystemExit("Final macOS app is missing; run make release-build")
    bundle_check()
    release = load_release_config()
    version = release.versions.application_version
    _architecture(EXECUTABLE)
    _architecture(SIDECAR)
    statuses = signing_status()
    _artifact_scan()
    _licence_scan()
    manual_rc_evidence()

    _copy_evidence(
        ROOT / "release-artifacts/clean-install/clean-install-evidence.json",
        "clean-install-final.json",
    )
    _copy_evidence(ROOT / "release-artifacts/upgrade/upgrade-evidence.json", "upgrade-final.json")
    _copy_evidence(
        ROOT / "release-artifacts/reinstall/reinstall-evidence.json",
        "reinstall-final.json",
    )

    provenance = collect_provenance("release-candidate").serialize()
    source_policy_path = FINAL / "source-policy.json"
    if source_policy_path.is_file():
        source_policy = json.loads(source_policy_path.read_text(encoding="utf-8"))
        source_clean_at_build_start = bool(source_policy.get("clean", False))
    else:
        source_clean_at_build_start = False
    provenance["source_clean_at_build_start"] = source_clean_at_build_start
    provenance["signing_status"] = statuses["signing"]["status"]
    provenance["notarization_status"] = statuses["notarization"]["status"]
    provenance["tauri_version"] = "2.11.4"
    provenance_path = _write("build-provenance-final.json", provenance)

    sidecar_artifact = FINAL / f"orp-backend-{version}-macos-arm64"
    shutil.copy2(SIDECAR, sidecar_artifact)
    archive = _distribution_archive(version)
    limitations = [
        "Apple Silicon macOS only",
        "Intel macOS, Windows, and Linux are unvalidated",
        "External clean-machine validation is unvalidated",
        "Broker connectivity and order execution are excluded",
        "Live provider readiness remains provider- and licence-dependent",
    ]
    if statuses["signing"]["status"] != "passed":
        limitations.append("Artifact is unsigned")
    if statuses["notarization"]["status"] != "passed":
        limitations.append("Artifact is not notarized")

    manifest = {
        "api_version": release.versions.api_version,
        "application_version": version,
        "artifacts": [
            {
                "architecture": "arm64",
                "name": archive.name,
                "sha256": file_checksum(archive),
                "size_bytes": archive.stat().st_size,
                "type": "macos-app-zip",
            },
            {
                "architecture": "arm64",
                "name": sidecar_artifact.name,
                "sha256": file_checksum(sidecar_artifact),
                "size_bytes": sidecar_artifact.stat().st_size,
                "type": "sidecar",
            },
        ],
        "database_schema": {
            "current": release.versions.database_schema_current,
            "minimum": release.versions.database_schema_minimum,
        },
        "fixture_version": release.versions.fixture_version,
        "known_limitations": limitations,
        "notarization_status": statuses["notarization"]["status"],
        "platform": {"minimum_macos": release.minimum_macos_version, "name": "macOS"},
        "provenance": provenance_path.name,
        "release_profile": "release-candidate",
        "sidecar_protocol_version": release.versions.sidecar_protocol_version,
        "signing_status": statuses["signing"]["status"],
        "workspace_schema": {
            "current": release.versions.workspace_schema_current,
            "minimum": release.versions.workspace_schema_minimum,
        },
    }
    manifest_path = _write("release-manifest-final.json", manifest)

    checksum_paths = [archive, sidecar_artifact, manifest_path, provenance_path]
    checksums = {path.name: file_checksum(path) for path in checksum_paths}
    _write("checksums.json", {"algorithm": "SHA-256", "artifacts": checksums})
    (FINAL / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items())),
        encoding="utf-8",
    )

    required_evidence = {
        "browser_e2e": FINAL / "final-e2e.json",
        "clean_install": FINAL / "clean-install-final.json",
        "desktop_smoke": FINAL / "desktop-smoke.json",
        "reinstall": FINAL / "reinstall-final.json",
        "upgrade": FINAL / "upgrade-final.json",
    }
    missing_evidence = [name for name, path in required_evidence.items() if not path.is_file()]
    public_blockers = []
    if statuses["signing"]["status"] != "passed":
        public_blockers.append("Developer ID signing incomplete")
    if statuses["notarization"]["status"] != "passed":
        public_blockers.append("Apple notarization incomplete")
    if statuses["gatekeeper"]["status"] != "passed":
        public_blockers.append("Gatekeeper assessment failed")
    public_blockers.extend(f"missing {name} evidence" for name in missing_evidence)
    public_blockers.append("external clean-machine validation unvalidated")
    public_blockers.append("third-party licence legal review unvalidated")
    internal_blockers = [f"missing {name} evidence" for name in missing_evidence]
    if not source_clean_at_build_start:
        internal_blockers.append("clean build-start evidence is unavailable for this artifact")
        public_blockers.append("clean build-start evidence is unavailable for this artifact")
    readiness = {
        "application_version": version,
        "internal_rc_blockers": internal_blockers,
        "internal_rc_status": "ready_with_warnings" if not internal_blockers else "incomplete",
        "manual_onboarding": "unvalidated",
        "public_release_blockers": public_blockers,
        "public_release_status": "blocked" if public_blockers else "ready",
        "status_model": ["ready", "ready_with_warnings", "incomplete", "blocked", "unvalidated"],
    }
    _write("release-readiness-final.json", readiness)
    _write(
        "github-release.json",
        {
            "artifacts": sorted([*checksums, "SHA256SUMS", "checksums.json"]),
            "draft": True,
            "prerelease": True,
            "publish_automatically": False,
            "release_notes": "docs/Release_Notes_1.0.0-rc.1.md",
            "tag_name": f"v{version}",
            "title": f"Option Research Platform {version}",
        },
    )
    print(FINAL.relative_to(ROOT))
    return readiness


def sign() -> None:
    identity, status = _identity_status()
    if status != "available" or identity is None:
        signing_status()
        raise SystemExit("Developer ID Application identity is unavailable")
    source_policy_path = FINAL / "source-policy.json"
    if not source_policy_path.is_file():
        raise SystemExit("Clean source-policy evidence is required before signing")
    source_policy = json.loads(source_policy_path.read_text(encoding="utf-8"))
    current_commit = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    if not source_policy.get("clean") or source_policy.get("git_commit") != current_commit:
        raise SystemExit("Signing requires clean build-start evidence for the current Git commit")
    for binary in (SIDECAR, EXECUTABLE):
        result = _run(
            [
                "codesign",
                "--force",
                "--options",
                "runtime",
                "--timestamp",
                "--sign",
                identity,
                str(binary),
            ]
        )
        if result.returncode != 0:
            raise SystemExit(f"Failed to sign {binary.name}: {result.stderr[-500:]}")
    app_result = _run(
        ["codesign", "--force", "--options", "runtime", "--timestamp", "--sign", identity, str(APP)]
    )
    if app_result.returncode != 0:
        raise SystemExit(f"Failed to sign application: {app_result.stderr[-500:]}")
    verified = _run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(APP)])
    if verified.returncode != 0:
        raise SystemExit(f"Signed application verification failed: {verified.stderr[-500:]}")
    signing_status()
    print("Developer ID signing passed")


def _notary_credentials() -> list[str]:
    profile = os.environ.get("APPLE_NOTARYTOOL_PROFILE")
    if profile:
        return ["--keychain-profile", profile]
    key_path = os.environ.get("APPLE_API_KEY_PATH")
    key_id = os.environ.get("APPLE_API_KEY_ID")
    issuer = os.environ.get("APPLE_API_ISSUER")
    if key_path and key_id and issuer:
        return ["--key", key_path, "--key-id", key_id, "--issuer", issuer]
    raise SystemExit("Notarization credentials are unavailable")


def notarize() -> None:
    status = signing_status()
    if status["signing"]["status"] != "passed":
        raise SystemExit("A valid Developer ID signature is required before notarization")
    release = load_release_config()
    archive = _distribution_archive(release.versions.application_version)
    credentials = _notary_credentials()
    result = _run(
        [
            "xcrun",
            "notarytool",
            "submit",
            str(archive),
            "--wait",
            "--output-format",
            "json",
            *credentials,
        ]
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {}
    accepted = result.returncode == 0 and payload.get("status") == "Accepted"
    evidence = {
        "credential_mode": _notary_configuration(),
        "executable_sha256": file_checksum(EXECUTABLE),
        "status": "passed" if accepted else "failed",
        "submission_id": payload.get("id"),
        "ticket_stapled": False,
    }
    _write("notarization-status.json", evidence)
    if not accepted:
        submission_id = payload.get("id")
        if isinstance(submission_id, str) and submission_id:
            log_result = _run(
                [
                    "xcrun",
                    "notarytool",
                    "log",
                    submission_id,
                    "--output-format",
                    "json",
                    *credentials,
                ]
            )
            try:
                log_payload = json.loads(log_result.stdout)
            except json.JSONDecodeError:
                log_payload = {}
            issues = log_payload.get("issues", []) if isinstance(log_payload, dict) else []
            evidence["failure_issues"] = [
                {
                    "code": item.get("code"),
                    "message": re.sub(
                        r"/(Users|home)/[^/\s]+",
                        r"/\1/[REDACTED]",
                        str(item.get("message", "notarization issue")),
                    ),
                    "severity": item.get("severity"),
                }
                for item in issues
                if isinstance(item, dict)
            ]
            _write("notarization-status.json", evidence)
        raise SystemExit("Apple notarization was not accepted; redacted evidence was recorded")
    staple = _run(["xcrun", "stapler", "staple", str(APP)])
    validate = _run(["xcrun", "stapler", "validate", str(APP)])
    if staple.returncode != 0 or validate.returncode != 0:
        raise SystemExit("Notarization succeeded but ticket stapling validation failed")
    evidence["ticket_stapled"] = True
    _write("notarization-status.json", evidence)
    finalize()
    print("notarization and stapling passed")


def source_policy() -> dict[str, Any]:
    status = _run(["git", "status", "--porcelain"])
    commit = _run(["git", "rev-parse", "HEAD"])
    evidence = {
        "clean": status.returncode == 0 and not status.stdout.strip(),
        "git_commit": commit.stdout.strip(),
        "profile": "release-candidate",
    }
    _write("source-policy.json", evidence)
    if not evidence["clean"]:
        raise SystemExit("Release-candidate build inputs require a clean Git tree")
    print("clean release source policy recorded")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "command",
        choices=(
            "browser-e2e",
            "desktop-smoke",
            "finalize",
            "notarize",
            "sign",
            "signing-status",
            "source-policy",
        ),
    )
    command = parser.parse_args().command
    if command == "browser-e2e":
        browser_e2e()
    elif command == "desktop-smoke":
        desktop_smoke()
    elif command == "finalize":
        finalize()
    elif command == "notarize":
        notarize()
    elif command == "sign":
        sign()
    elif command == "source-policy":
        source_policy()
    else:
        signing_status()
        print("signing readiness evidence written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
