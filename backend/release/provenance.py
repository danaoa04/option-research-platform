"""Redacted deterministic build provenance."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import ReleaseConfig, load_release_config


def _command(*args: str, default: str = "unavailable") -> str:
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()
    except OSError, subprocess.CalledProcessError:
        return default


@dataclass(slots=True, frozen=True)
class BuildProvenance:
    application_version: str
    git_commit: str
    git_branch: str
    dirty: bool
    build_timestamp: str
    build_profile: str
    target_platform: str
    target_architecture: str
    python_version: str
    rust_version: str
    node_version: str
    api_version: str
    database_schema_version: str
    sidecar_protocol_version: str
    fixture_version: str

    def serialize(self) -> dict[str, str | bool]:
        return asdict(self)


def collect_provenance(
    profile: str = "development",
    *,
    root: Path | None = None,
    config: ReleaseConfig | None = None,
    timestamp: str | None = None,
) -> BuildProvenance:
    repository = root or Path(__file__).resolve().parents[2]
    metadata = config or load_release_config()
    status = _command("git", "-C", str(repository), "status", "--porcelain", default="")
    return BuildProvenance(
        application_version=metadata.versions.application_version,
        git_commit=_command("git", "-C", str(repository), "rev-parse", "--short=12", "HEAD"),
        git_branch=_command("git", "-C", str(repository), "branch", "--show-current"),
        dirty=bool(status),
        build_timestamp=timestamp
        or os.environ.get("SOURCE_DATE_EPOCH_TIMESTAMP")
        or datetime.now(UTC).replace(microsecond=0).isoformat(),
        build_profile=profile,
        target_platform=platform.system().lower(),
        target_architecture=platform.machine(),
        python_version=platform.python_version(),
        rust_version=_command("rustc", "--version"),
        node_version=_command("node", "--version"),
        api_version=metadata.versions.api_version,
        database_schema_version=metadata.versions.database_schema_current,
        sidecar_protocol_version=metadata.versions.sidecar_protocol_version,
        fixture_version=metadata.versions.fixture_version,
    )
