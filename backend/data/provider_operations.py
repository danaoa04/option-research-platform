"""Provider-neutral operational records and deterministic in-memory service boundary."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ProviderJobStatus(StrEnum):
    PLANNED = "planned"
    REQUESTING = "requesting"
    THROTTLED = "throttled"
    IMPORTING = "importing"
    CERTIFYING = "certifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True, frozen=True)
class ProviderRequestRecord:
    provider: str
    request_id: str
    dataset: str
    request_checksum: str
    parameters: Mapping[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True, frozen=True)
class ProviderCheckpoint:
    provider: str
    job_id: str
    checkpoint_id: str
    ordinal: int
    continuation: str | None
    response_checksum: str
    completed: bool


@dataclass(slots=True, frozen=True)
class ProviderFailureRecord:
    provider: str
    job_id: str
    code: str
    message: str
    retryable: bool
    resolved: bool = False


@dataclass(slots=True)
class ProviderJob:
    provider: str
    job_id: str
    request_checksum: str
    status: ProviderJobStatus = ProviderJobStatus.PLANNED
    events: list[tuple[ProviderJobStatus, str]] = field(default_factory=list)
    cancelled: bool = False

    def transition(self, status: ProviderJobStatus) -> None:
        self.status = status
        self.events.append((status, datetime.now(UTC).isoformat()))


class ProviderOperationsService:
    """Storage-agnostic semantics used by persistence repositories and offline tests."""

    def __init__(self) -> None:
        self.jobs: dict[str, ProviderJob] = {}
        self.requests: dict[tuple[str, str], ProviderRequestRecord] = {}
        self.checkpoints: dict[tuple[str, str], ProviderCheckpoint] = {}
        self.failures: list[ProviderFailureRecord] = []

    def create_job(self, provider: str, parameters: Mapping[str, Any]) -> ProviderJob:
        canonical = json.dumps(parameters, sort_keys=True, separators=(",", ":"), default=str)
        checksum = hashlib.sha256(canonical.encode()).hexdigest()
        job_id = f"{provider}-{checksum[:16]}"
        job = self.jobs.setdefault(job_id, ProviderJob(provider, job_id, checksum))
        self.requests.setdefault(
            (provider, job_id),
            ProviderRequestRecord(
                provider, job_id, str(parameters.get("dataset", "")), checksum, dict(parameters)
            ),
        )
        return job

    def checkpoint(self, value: ProviderCheckpoint) -> None:
        key = (value.job_id, value.checkpoint_id)
        existing = self.checkpoints.get(key)
        if existing and existing.response_checksum != value.response_checksum:
            raise ValueError("Checkpoint response changed; create a new dataset version")
        self.checkpoints[key] = value

    def unresolved_failures(self, provider: str | None = None) -> tuple[ProviderFailureRecord, ...]:
        return tuple(
            failure
            for failure in self.failures
            if not failure.resolved and (provider is None or failure.provider == provider)
        )

    def cancel(self, job_id: str) -> ProviderJob:
        job = self.jobs[job_id]
        job.cancelled = True
        job.transition(ProviderJobStatus.CANCELLED)
        return job

    def resume(self, job_id: str) -> ProviderJob:
        job = self.jobs[job_id]
        if job.status not in {ProviderJobStatus.CANCELLED, ProviderJobStatus.FAILED}:
            raise ValueError("Only cancelled or failed jobs can be resumed")
        job.cancelled = False
        job.transition(ProviderJobStatus.PLANNED)
        return job
