"""Release manifest and evidence-based readiness models."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .config import ReleaseConfig, load_release_config, load_release_profile
from .provenance import BuildProvenance, collect_provenance

SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReadinessStatus(StrEnum):
    READY = "ready"
    READY_WITH_WARNINGS = "ready_with_warnings"
    INCOMPLETE = "incomplete"
    BLOCKED = "blocked"
    UNVALIDATED = "unvalidated"


@dataclass(slots=True, frozen=True)
class ReadinessCategory:
    category: str
    status: ReadinessStatus
    evidence: str
    blocks_release_candidate: bool
    blocks_public_release: bool


@dataclass(slots=True, frozen=True)
class ReleaseReadinessReport:
    application_version: str
    profile: str
    categories: tuple[ReadinessCategory, ...]

    @property
    def release_candidate_ready(self) -> bool:
        return not any(
            item.blocks_release_candidate and item.status is not ReadinessStatus.READY
            for item in self.categories
        )

    @property
    def public_release_ready(self) -> bool:
        return not any(
            item.blocks_public_release and item.status is not ReadinessStatus.READY
            for item in self.categories
        )

    def serialize(self) -> dict[str, Any]:
        return {
            "application_version": self.application_version,
            "categories": [asdict(item) for item in self.categories],
            "profile": self.profile,
            "public_release_ready": self.public_release_ready,
            "release_candidate_ready": self.release_candidate_ready,
        }


@dataclass(slots=True, frozen=True)
class ReleaseManifest:
    application_version: str
    api_version: str
    backend_version: str
    build_provenance: dict[str, str | bool]
    database_schema_range: tuple[str, str]
    export_schema_version: str
    fixture_version: str
    frontend_version: str
    known_limitations: tuple[str, ...]
    licences: tuple[str, ...]
    release_profile: str
    report_schema_version: str
    sidecar_checksum: str
    sidecar_protocol_version: str
    target_architecture: str
    target_platform: str
    workspace_schema_range: tuple[int, int]

    def serialize(self) -> dict[str, Any]:
        return asdict(self)

    def validate(self, config: ReleaseConfig | None = None) -> None:
        release = config or load_release_config()
        release.versions.validate()
        if self.application_version != release.versions.application_version:
            raise ValueError("Manifest application version disagrees with canonical version")
        if not SHA256.fullmatch(self.sidecar_checksum):
            raise ValueError("Manifest sidecar checksum is invalid")
        if self.database_schema_range[0] > self.database_schema_range[1]:
            raise ValueError("Manifest database schema range is inverted")
        serialized = json.dumps(self.serialize(), sort_keys=True)
        if re.search(r"/(Users|home)/|api[_-]?key|password|credential", serialized, re.I):
            raise ValueError("Manifest contains a local path or secret marker")


def file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_manifest(
    sidecar: Path,
    profile: str,
    *,
    provenance: BuildProvenance | None = None,
    config: ReleaseConfig | None = None,
) -> ReleaseManifest:
    release = config or load_release_config()
    load_release_profile(profile)
    build = provenance or collect_provenance(profile, config=release)
    manifest = ReleaseManifest(
        application_version=release.versions.application_version,
        api_version=release.versions.api_version,
        backend_version=release.versions.backend_version,
        build_provenance=build.serialize(),
        database_schema_range=(
            release.versions.database_schema_minimum,
            release.versions.database_schema_current,
        ),
        export_schema_version=release.versions.export_schema_version,
        fixture_version=release.versions.fixture_version,
        frontend_version=release.versions.frontend_version,
        known_limitations=(
            "Unsigned and not notarized",
            "Clean-machine validation deferred to Sprint 12B",
            "Apple Silicon is the only validated architecture",
        ),
        licences=("LICENSE", "docs/Third_Party_Notices.md"),
        release_profile=profile,
        report_schema_version=release.versions.report_schema_version,
        sidecar_checksum=file_checksum(sidecar),
        sidecar_protocol_version=release.versions.sidecar_protocol_version,
        target_architecture=build.target_architecture,
        target_platform=build.target_platform,
        workspace_schema_range=(
            release.versions.workspace_schema_minimum,
            release.versions.workspace_schema_current,
        ),
    )
    manifest.validate(release)
    return manifest


def default_readiness_report(profile: str = "release-candidate") -> ReleaseReadinessReport:
    version = load_release_config().versions.application_version
    ready = ReadinessStatus.READY
    return ReleaseReadinessReport(
        version,
        profile,
        (
            ReadinessCategory("version_consistency", ready, "version-check", True, True),
            ReadinessCategory("quality_gates", ready, "make quality", True, True),
            ReadinessCategory("api_compatibility", ready, "contract tests", True, True),
            ReadinessCategory("database_migrations", ready, "migration tests", True, True),
            ReadinessCategory("workspace_compatibility", ready, "schema tests", True, True),
            ReadinessCategory("sidecar_build", ready, "sidecar-check", True, True),
            ReadinessCategory("sidecar_lifecycle", ready, "packaged smoke", True, True),
            ReadinessCategory("fixture_integrity", ready, "fixture manifest", True, True),
            ReadinessCategory("dependency_locks", ready, "lock audit", True, True),
            ReadinessCategory("bundle_content", ready, "bundle inspection", True, True),
            ReadinessCategory("architecture", ready, "arm64 validated", True, True),
            ReadinessCategory("licences_notices", ready, "notice inventory", True, True),
            ReadinessCategory("security", ready, "bundle denylist", True, True),
            ReadinessCategory("accessibility", ready, "frontend tests", False, True),
            ReadinessCategory("performance", ready, "build metrics", False, False),
            ReadinessCategory("packaged_smoke_tests", ready, "macOS local smoke", True, True),
            ReadinessCategory(
                "clean_machine_validation",
                ReadinessStatus.UNVALIDATED,
                "Sprint 12B",
                False,
                True,
            ),
            ReadinessCategory("signing", ReadinessStatus.INCOMPLETE, "deferred", False, True),
            ReadinessCategory("notarization", ReadinessStatus.INCOMPLETE, "deferred", False, True),
        ),
    )
