"""Deterministic schema-specific provider monitoring calculations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ProviderMonitoringSnapshot:
    provider: str
    request_count: int
    failure_rate: float
    retry_rate: float
    rate_limit_pressure: float
    missing_batches: int
    stalled_continuations: int
    schema_changes: int
    quarantine_rate: float
    divergence_rate: float
    unresolved_identity_rate: float
    checksum_mismatches: int
    alerts: tuple[str, ...]


def calculate_monitoring(
    provider: str,
    *,
    requests: int,
    failures: int = 0,
    retries: int = 0,
    rate_limit_used: int = 0,
    rate_limit_capacity: int = 0,
    missing_batches: int = 0,
    stalled_continuations: int = 0,
    schema_changes: int = 0,
    quarantined: int = 0,
    records: int = 0,
    divergences: int = 0,
    comparisons: int = 0,
    unresolved: int = 0,
    identities: int = 0,
    checksum_mismatches: int = 0,
) -> ProviderMonitoringSnapshot:
    def ratio(value: int, total: int) -> float:
        return value / total if total else 0.0

    metrics = {
        "failure rate": ratio(failures, requests),
        "retry rate": ratio(retries, requests),
        "rate-limit pressure": ratio(rate_limit_used, rate_limit_capacity),
        "quarantine rate": ratio(quarantined, records),
        "divergence rate": ratio(divergences, comparisons),
        "unresolved identity rate": ratio(unresolved, identities),
    }
    alerts = [name for name, value in metrics.items() if value > 0.1]
    alerts.extend("missing batches" for _ in range(bool(missing_batches)))
    alerts.extend("stalled continuation" for _ in range(bool(stalled_continuations)))
    alerts.extend("schema changed" for _ in range(bool(schema_changes)))
    alerts.extend("checksum mismatch" for _ in range(bool(checksum_mismatches)))
    return ProviderMonitoringSnapshot(
        provider,
        requests,
        metrics["failure rate"],
        metrics["retry rate"],
        metrics["rate-limit pressure"],
        missing_batches,
        stalled_continuations,
        schema_changes,
        metrics["quarantine rate"],
        metrics["divergence rate"],
        metrics["unresolved identity rate"],
        checksum_mismatches,
        tuple(sorted(set(alerts))),
    )
