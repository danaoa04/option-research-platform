"""Typed canonical release configuration."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RELEASE_ROOT = ROOT / "release"
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-rc\.\d+)?$")


@dataclass(slots=True, frozen=True)
class VersionMetadata:
    application_version: str
    api_version: str
    backend_version: str
    database_schema_current: str
    database_schema_minimum: str
    export_schema_version: str
    fixture_version: str
    frontend_version: str
    report_schema_version: str
    sidecar_protocol_version: str
    workspace_schema_current: int
    workspace_schema_minimum: int

    def validate(self) -> None:
        versions = (self.application_version, self.backend_version, self.frontend_version)
        if any(not SEMVER.fullmatch(value) for value in versions):
            raise ValueError("Application versions must use supported semantic versioning")
        if len(set(versions)) != 1:
            raise ValueError("Application, backend, and frontend versions disagree")
        if not re.fullmatch(r"v\d+", self.api_version):
            raise ValueError("API version must use the vN convention")
        if self.database_schema_minimum > self.database_schema_current:
            raise ValueError("Database schema range is inverted")
        if self.workspace_schema_minimum > self.workspace_schema_current:
            raise ValueError("Workspace schema range is inverted")


@dataclass(slots=True, frozen=True)
class ReleaseConfig:
    application_data_directory: str
    application_name: str
    backend_startup_timeout_seconds: int
    bundle_identifier: str
    database_filename: str
    diagnostic_bundle_prefix: str
    export_directory: str
    fixture_directory: str
    log_directory: str
    maximum_export_bytes: int
    maximum_workspace_bytes: int
    minimum_macos_version: str
    release_channel: str
    sidecar_executable_name: str
    supported_architectures: tuple[str, ...]
    workspace_directory: str
    workspace_extension: str
    versions: VersionMetadata

    def validate(self) -> None:
        self.versions.validate()
        if self.bundle_identifier != "io.optionresearch.platform":
            raise ValueError("Public bundle identifier changed unexpectedly")
        if self.release_channel not in {"development", "test", "offline", "rc", "production"}:
            raise ValueError("Unsupported release channel")
        if self.backend_startup_timeout_seconds < 1:
            raise ValueError("Backend startup timeout must be positive")
        names = (
            self.database_filename,
            self.export_directory,
            self.fixture_directory,
            self.log_directory,
            self.workspace_directory,
        )
        if any(Path(value).is_absolute() or ".." in Path(value).parts for value in names):
            raise ValueError("Release paths must be safe relative names")


@dataclass(slots=True, frozen=True)
class ReleaseProfile:
    name: str
    runtime_mode: str
    fixture_available: bool
    log_level: str
    diagnostics: str
    provider_policy: str
    export_policy: str
    updater: bool
    webgl: bool
    debug_tools: bool
    source_maps: bool
    telemetry: bool

    def validate(self) -> None:
        if self.telemetry:
            raise ValueError("Telemetry is prohibited")
        if self.name in {"release-candidate", "production-release"} and (
            self.debug_tools or self.source_maps
        ):
            raise ValueError("Release profiles cannot include debug tools or source maps")


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path.name}")
    return value


def load_release_config(root: Path = RELEASE_ROOT) -> ReleaseConfig:
    versions = VersionMetadata(**_json(root / "version.json"))
    raw = _json(root / "config.json")
    raw["supported_architectures"] = tuple(raw["supported_architectures"])
    config = ReleaseConfig(**raw, versions=versions)
    config.validate()
    return config


def load_release_profile(name: str, root: Path = RELEASE_ROOT) -> ReleaseProfile:
    profiles = _json(root / "profiles.json")
    try:
        raw = profiles[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported release profile: {name}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid release profile: {name}")
    profile = ReleaseProfile(name=name, **raw)
    profile.validate()
    return profile


def validate_build_policy(
    profile: str,
    *,
    dirty: bool,
    exact_tag: str | None = None,
    version: str | None = None,
) -> None:
    load_release_profile(profile)
    application_version = version or load_release_config().versions.application_version
    if profile in {"release-candidate", "production-release"} and dirty:
        raise ValueError(f"{profile} builds require a clean Git tree")
    if profile == "production-release" and exact_tag not in {
        application_version,
        f"v{application_version}",
    }:
        raise ValueError("Public release requires an exact matching version tag")
