"""Production provider runtime controls with an offline deterministic default."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol


class NetworkMode(StrEnum):
    OFFLINE = "offline"
    FIXTURES_ONLY = "fixtures_only"
    CACHED_ONLY = "cached_responses_only"
    AUTHENTICATED_METADATA = "authenticated_metadata_only"
    AUTHENTICATED_DOWNLOAD = "authenticated_download"
    UNRESTRICTED = "unrestricted_provider_operations"


@dataclass(slots=True, frozen=True)
class NetworkPolicy:
    mode: NetworkMode = NetworkMode.OFFLINE
    allowed_providers: tuple[str, ...] = ()

    def authorize(self, provider: str, *, network: bool, download: bool = False) -> None:
        if not network:
            return
        if self.mode in {NetworkMode.OFFLINE, NetworkMode.FIXTURES_ONLY, NetworkMode.CACHED_ONLY}:
            raise PermissionError(f"Network policy {self.mode.value} denies provider requests")
        if self.allowed_providers and provider not in self.allowed_providers:
            raise PermissionError(f"Provider {provider!r} is not authorized by network policy")
        if download and self.mode is NetworkMode.AUTHENTICATED_METADATA:
            raise PermissionError("Metadata-only policy denies downloads")


class SecretSource(Protocol):
    def get(self, provider: str, name: str) -> str | None: ...


@dataclass(slots=True, frozen=True)
class CredentialStatus:
    provider: str
    configured: bool
    source: str
    validated: bool = False
    reason: str | None = None


@dataclass(slots=True, frozen=True)
class LicensedSample:
    sample_id: str
    provider: str
    dataset: str
    checksum: str
    storage_path: str | None
    metadata_only: bool
    registered_at: datetime


def register_sample(
    provider: str,
    dataset: str,
    path: str | Path,
    *,
    metadata_only: bool = True,
) -> LicensedSample:
    source = Path(path)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    checksum = digest.hexdigest()
    return LicensedSample(
        f"{provider}-{checksum[:16]}",
        provider,
        dataset,
        checksum,
        None if metadata_only else str(source.resolve()),
        metadata_only,
        datetime.now(UTC),
    )


class ScheduleFrequency(StrEnum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass(slots=True, frozen=True)
class ProviderSchedule:
    schedule_id: str
    provider: str
    dataset: str
    symbols: tuple[str, ...]
    frequency: ScheduleFrequency
    timezone: str
    next_run: datetime
    enabled: bool = True
    concurrency_limit: int = 1


@dataclass(slots=True)
class SchedulerService:
    schedules: dict[str, ProviderSchedule] = field(default_factory=dict)
    claimed_runs: set[tuple[str, str]] = field(default_factory=set)

    def add(self, schedule: ProviderSchedule) -> None:
        if schedule.schedule_id in self.schedules:
            raise ValueError("Duplicate schedule")
        self.schedules[schedule.schedule_id] = schedule

    def due(self, now: datetime) -> tuple[ProviderSchedule, ...]:
        return tuple(
            item
            for item in sorted(self.schedules.values(), key=lambda value: value.schedule_id)
            if item.enabled and item.next_run <= now
        )

    def claim(self, schedule_id: str, due_at: datetime) -> bool:
        key = (schedule_id, due_at.isoformat())
        if key in self.claimed_runs:
            return False
        self.claimed_runs.add(key)
        return True


@dataclass(slots=True)
class WorkerLease:
    job_id: str
    worker_id: str
    expires_at: datetime
    heartbeat_at: datetime
    attempts: int = 0
    dead_lettered: bool = False

    def heartbeat(self, now: datetime, duration: timedelta) -> None:
        if self.dead_lettered:
            raise ValueError("Dead-lettered jobs cannot heartbeat")
        self.heartbeat_at = now
        self.expires_at = now + duration


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    IMPAIRED = "impaired"
    UNAVAILABLE = "unavailable"
    CONFIGURATION_REQUIRED = "configuration_required"
    CREDENTIALS_INVALID = "credentials_invalid"
    DATA_QUALITY_DEGRADED = "data_quality_degraded"
    UNKNOWN = "unknown"


@dataclass(slots=True, frozen=True)
class ProviderHealth:
    provider: str
    status: HealthStatus
    score: float
    reasons: tuple[str, ...]
    metrics: dict[str, float]


def calculate_health(
    provider: str,
    metrics: dict[str, float],
    *,
    configured: bool = True,
    credentials_valid: bool = True,
) -> ProviderHealth:
    if not configured:
        return ProviderHealth(
            provider, HealthStatus.CONFIGURATION_REQUIRED, 0, ("configuration missing",), metrics
        )
    if not credentials_valid:
        return ProviderHealth(
            provider, HealthStatus.CREDENTIALS_INVALID, 0, ("credentials invalid",), metrics
        )
    penalty = sum(min(max(value, 0), 1) for value in metrics.values()) / max(len(metrics), 1)
    score = round(max(0.0, 1.0 - penalty), 6)
    status = (
        HealthStatus.HEALTHY
        if score >= 0.9
        else HealthStatus.DEGRADED
        if score >= 0.7
        else HealthStatus.IMPAIRED
    )
    return ProviderHealth(
        provider,
        status,
        score,
        tuple(sorted(name for name, value in metrics.items() if value > 0.1)),
        metrics,
    )


@dataclass(slots=True)
class Alert:
    fingerprint: str
    provider: str
    rule: str
    severity: str
    first_seen: datetime
    last_seen: datetime
    occurrences: int = 1
    acknowledged: bool = False
    resolved: bool = False


class AlertService:
    def __init__(self) -> None:
        self.alerts: dict[str, Alert] = {}

    def emit(self, provider: str, rule: str, severity: str, now: datetime) -> Alert:
        fingerprint = hashlib.sha256(f"{provider}:{rule}".encode()).hexdigest()
        alert = self.alerts.get(fingerprint)
        if alert and not alert.resolved:
            alert.last_seen = now
            alert.occurrences += 1
            alert.severity = max(alert.severity, severity)
            return alert
        alert = Alert(fingerprint, provider, rule, severity, now, now)
        self.alerts[fingerprint] = alert
        return alert

    def acknowledge(self, fingerprint: str) -> Alert:
        self.alerts[fingerprint].acknowledged = True
        return self.alerts[fingerprint]

    def resolve(self, fingerprint: str) -> Alert:
        self.alerts[fingerprint].resolved = True
        return self.alerts[fingerprint]


class RetentionAction(StrEnum):
    KEEP_FOREVER = "keep_forever"
    KEEP_DURATION = "keep_for_duration"
    KEEP_LATEST = "keep_latest_versions"
    ARCHIVE = "archive"
    DELETE_AFTER_CERTIFICATION = "delete_after_certification"


@dataclass(slots=True, frozen=True)
class RetentionPolicy:
    name: str
    action: RetentionAction
    duration_days: int | None = None
    latest_versions: int | None = None
    legal_hold: bool = False


@dataclass(slots=True, frozen=True)
class CleanupCandidate:
    path: str
    size_bytes: int
    checksum: str
    authorized: bool = False


def cleanup_plan(
    paths: tuple[Path, ...],
    protected_root: Path,
    *,
    authorize_deletion: bool = False,
) -> tuple[CleanupCandidate, ...]:
    root = protected_root.resolve()
    candidates = []
    for path in sorted(paths):
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or path.is_symlink():
            raise ValueError("Unsafe cleanup path")
        if path.is_file():
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            candidates.append(
                CleanupCandidate(str(resolved), path.stat().st_size, checksum, authorize_deletion)
            )
    return tuple(candidates)


def deterministic_checksum(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


class FreshnessStatus(StrEnum):
    CURRENT = "current"
    DELAYED = "delayed"
    STALE = "stale"
    MISSING = "missing"
    UNKNOWN = "unknown"


@dataclass(slots=True, frozen=True)
class FreshnessResult:
    provider: str
    dataset: str
    status: FreshnessStatus
    age_seconds: float | None


def calculate_freshness(
    provider: str,
    dataset: str,
    latest: datetime | None,
    now: datetime,
    expected: timedelta,
) -> FreshnessResult:
    if latest is None:
        return FreshnessResult(provider, dataset, FreshnessStatus.MISSING, None)
    age = max((now - latest).total_seconds(), 0)
    threshold = expected.total_seconds()
    status = FreshnessStatus.CURRENT
    if age > threshold * 2:
        status = FreshnessStatus.STALE
    elif age > threshold:
        status = FreshnessStatus.DELAYED
    return FreshnessResult(provider, dataset, status, age)


@dataclass(slots=True, frozen=True)
class SynchronizationGap:
    provider: str
    dataset: str
    symbol: str
    missing_dates: tuple[str, ...]
    reason: str
    remediation: str


class ReadinessStatus(StrEnum):
    READY = "ready"
    READY_WITH_WARNINGS = "ready_with_warnings"
    FIXTURE_ONLY = "fixture_only"
    CREDENTIALS_REQUIRED = "credentials_required"
    SAMPLE_VALIDATION_REQUIRED = "sample_validation_required"
    MAPPING_APPROVAL_REQUIRED = "mapping_approval_required"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass(slots=True, frozen=True)
class OperationalReadiness:
    provider: str
    status: ReadinessStatus
    blockers: tuple[str, ...]
    health: HealthStatus


def readiness(
    provider: str,
    health: ProviderHealth,
    *,
    fixture_transport: bool,
    credentials: CredentialStatus,
    sample_validated: bool,
    mapping_approved: bool,
) -> OperationalReadiness:
    blockers = []
    if not credentials.configured:
        blockers.append("credentials required")
    if not sample_validated:
        blockers.append("licensed sample validation required")
    if not mapping_approved:
        blockers.append("mapping approval required")
    if not blockers and health.status is HealthStatus.HEALTHY:
        status = ReadinessStatus.READY
    elif fixture_transport and not credentials.configured:
        status = ReadinessStatus.FIXTURE_ONLY
    elif not credentials.configured:
        status = ReadinessStatus.CREDENTIALS_REQUIRED
    elif not sample_validated:
        status = ReadinessStatus.SAMPLE_VALIDATION_REQUIRED
    elif not mapping_approved:
        status = ReadinessStatus.MAPPING_APPROVAL_REQUIRED
    else:
        status = ReadinessStatus.DEGRADED
    return OperationalReadiness(provider, status, tuple(blockers), health.status)
