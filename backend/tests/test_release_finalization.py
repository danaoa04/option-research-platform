from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.api.v1 import runtime_provenance
from backend.release.manifest import create_manifest
from backend.sidecar import configure_build_provenance
from scripts import release_finalize


def test_tauri_hardened_runtime_uses_no_unnecessary_entitlements() -> None:
    config = json.loads(Path("frontend/src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    macos = config["bundle"]["macOS"]
    assert macos["hardenedRuntime"] is True
    assert "entitlements" not in macos
    assert config["identifier"] == "io.optionresearch.platform"
    assert "icons/icon.icns" in config["bundle"]["icon"]


def test_manual_evidence_does_not_fabricate_dogfood_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release_finalize, "FINAL", tmp_path)
    evidence = release_finalize.manual_rc_evidence()
    assert evidence["status"] == "unvalidated"
    assert evidence["manual_observations"] == []
    assert all(item["status"] == "unvalidated" for item in evidence["tasks"])
    stored = json.loads((tmp_path / "manual-rc-validation.json").read_text(encoding="utf-8"))
    assert stored == evidence


def test_notarization_credentials_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "APPLE_NOTARYTOOL_PROFILE",
        "APPLE_API_KEY_PATH",
        "APPLE_API_KEY_ID",
        "APPLE_API_ISSUER",
    ):
        monkeypatch.delenv(name, raising=False)
    assert release_finalize._notary_configuration() == "unavailable"
    with pytest.raises(SystemExit, match="credentials are unavailable"):
        release_finalize._notary_credentials()


def test_notarization_keychain_profile_is_referenced_without_secret_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLE_NOTARYTOOL_PROFILE", "release-profile")
    assert release_finalize._notary_configuration() == "keychain_profile"
    assert release_finalize._notary_credentials() == [
        "--keychain-profile",
        "release-profile",
    ]


def test_manifest_limitations_reflect_current_release_boundary(tmp_path: Path) -> None:
    sidecar = tmp_path / "orp-backend"
    sidecar.write_bytes(b"synthetic executable fixture")
    limitations = create_manifest(sidecar, "test").known_limitations
    assert "External clean-machine validation is unvalidated" in limitations
    assert "Intel macOS, Windows, and Linux are unvalidated" in limitations
    assert all("deferred to Sprint 12B" not in value for value in limitations)


def test_manual_release_workflow_prepares_artifacts_without_publishing() -> None:
    workflow = Path(".github/workflows/macos-release-candidate.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "make rc-build" in workflow
    assert "make release-finalize" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "gh release create" not in workflow


def test_packaged_provenance_is_allowlisted_and_path_is_not_returned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provenance = tmp_path / "build-provenance.json"
    provenance.write_text(
        json.dumps(
            {
                "build_profile": "release-candidate",
                "git_commit": "abc123def456",
                "local_path": "/Users/example/private",
                "target_architecture": "arm64",
            }
        ),
        encoding="utf-8",
    )
    configure_build_provenance(provenance.resolve())
    value = runtime_provenance()
    assert value == {
        "build_profile": "release-candidate",
        "git_commit": "abc123def456",
        "target_architecture": "arm64",
    }
    monkeypatch.delenv("ORP_BUILD_PROVENANCE_PATH", raising=False)
