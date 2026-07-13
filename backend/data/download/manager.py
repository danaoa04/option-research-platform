"""Download manager primitives that remain transport-agnostic and offline-testable."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol


class DownloadTransport(Protocol):
    """Protocol for injected transport implementations."""

    def download(self, request: DownloadRequest) -> DownloadResult:
        """Execute a single download attempt and return metadata about the attempt."""


@dataclass(slots=True, frozen=True)
class DownloadManagerConfig:
    """Retry/backoff/timeout behavior for a manager instance."""

    max_retries: int = 3
    base_backoff_seconds: float = 0.2
    max_backoff_seconds: float = 5.0
    timeout_seconds: float = 30.0


@dataclass(slots=True, frozen=True)
class DownloadResumeState:
    """State needed to resume partial downloads across attempts."""

    bytes_downloaded: int = 0
    etag: str | None = None
    last_modified: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())


@dataclass(slots=True, frozen=True)
class DownloadRequest:
    """Provider-neutral download request."""

    provider: str
    resource_id: str
    destination: Path
    timeout_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)
    resume_state: DownloadResumeState | None = None


@dataclass(slots=True, frozen=True)
class DownloadResult:
    """Result of a single transport download invocation."""

    succeeded: bool
    bytes_downloaded: int
    checksum: str | None = None
    resume_state: DownloadResumeState | None = None
    error: str | None = None


@dataclass(slots=True, frozen=True)
class DownloadAttempt:
    """Attempt-level metadata for auditability and diagnostics."""

    attempt_number: int
    timestamp: str
    succeeded: bool
    error: str | None = None


@dataclass(slots=True, frozen=True)
class DownloadExecution:
    """Structured output from manager.run_download."""

    request: DownloadRequest
    attempts: tuple[DownloadAttempt, ...]
    result: DownloadResult


class DownloadManager:
    """Retries, backoff, cancellation, and resumable metadata orchestration."""

    def __init__(
        self,
        config: DownloadManagerConfig | None = None,
        *,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.config = config or DownloadManagerConfig()
        self._sleeper = sleeper or time.sleep
        self._resume_state_by_key: dict[str, DownloadResumeState] = {}

    def run_download(
        self,
        *,
        provider: str,
        resource_id: str,
        destination: str | Path,
        transport: DownloadTransport,
        cancellation_hook: Callable[[], bool] | None = None,
        metadata: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> DownloadExecution:
        """Run a download workflow using an injected transport."""
        destination_path = Path(destination)
        key = self._download_key(
            provider=provider, resource_id=resource_id, destination=destination_path
        )
        resume_state = self._resume_state_by_key.get(key)

        attempts: list[DownloadAttempt] = []
        max_attempts = self.config.max_retries + 1

        for attempt_number in range(1, max_attempts + 1):
            if cancellation_hook and cancellation_hook():
                result = DownloadResult(
                    succeeded=False,
                    bytes_downloaded=resume_state.bytes_downloaded if resume_state else 0,
                    resume_state=resume_state,
                    error="cancelled",
                )
                attempts.append(
                    DownloadAttempt(
                        attempt_number=attempt_number,
                        timestamp=datetime.now(tz=UTC).isoformat(),
                        succeeded=False,
                        error="cancelled",
                    )
                )
                return DownloadExecution(
                    request=self._request(
                        provider,
                        resource_id,
                        destination_path,
                        metadata,
                        timeout_seconds,
                        resume_state,
                    ),
                    attempts=tuple(attempts),
                    result=result,
                )

            request = self._request(
                provider,
                resource_id,
                destination_path,
                metadata,
                timeout_seconds,
                resume_state,
            )
            result = transport.download(request)
            attempts.append(
                DownloadAttempt(
                    attempt_number=attempt_number,
                    timestamp=datetime.now(tz=UTC).isoformat(),
                    succeeded=result.succeeded,
                    error=result.error,
                )
            )

            if result.resume_state is not None:
                resume_state = result.resume_state
                self._resume_state_by_key[key] = result.resume_state

            if result.succeeded:
                self._resume_state_by_key.pop(key, None)
                return DownloadExecution(request=request, attempts=tuple(attempts), result=result)

            if attempt_number < max_attempts:
                self._sleeper(self._backoff_seconds(attempt_number))

        return DownloadExecution(
            request=self._request(
                provider, resource_id, destination_path, metadata, timeout_seconds, resume_state
            ),
            attempts=tuple(attempts),
            result=result,
        )

    def get_resume_state(
        self,
        *,
        provider: str,
        resource_id: str,
        destination: str | Path,
    ) -> DownloadResumeState | None:
        """Return the current resumable state for a download key."""
        key = self._download_key(
            provider=provider, resource_id=resource_id, destination=Path(destination)
        )
        return self._resume_state_by_key.get(key)

    def clear_resume_state(
        self, *, provider: str, resource_id: str, destination: str | Path
    ) -> None:
        """Clear persisted resumable metadata for a download key."""
        key = self._download_key(
            provider=provider, resource_id=resource_id, destination=Path(destination)
        )
        self._resume_state_by_key.pop(key, None)

    def _request(
        self,
        provider: str,
        resource_id: str,
        destination: Path,
        metadata: dict[str, Any] | None,
        timeout_seconds: float | None,
        resume_state: DownloadResumeState | None,
    ) -> DownloadRequest:
        return DownloadRequest(
            provider=provider,
            resource_id=resource_id,
            destination=destination,
            timeout_seconds=timeout_seconds or self.config.timeout_seconds,
            metadata=dict(metadata or {}),
            resume_state=resume_state,
        )

    def _backoff_seconds(self, attempt_number: int) -> float:
        value = self.config.base_backoff_seconds * (2 ** (attempt_number - 1))
        return float(min(value, self.config.max_backoff_seconds))

    def _download_key(self, *, provider: str, resource_id: str, destination: Path) -> str:
        value = f"{provider}:{resource_id}:{destination.as_posix()}".encode()
        return hashlib.sha256(value).hexdigest()
