from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.data.provider_runtime import (
    AlertService,
    CredentialStatus,
    FreshnessStatus,
    HealthStatus,
    NetworkMode,
    NetworkPolicy,
    ProviderSchedule,
    ReadinessStatus,
    ScheduleFrequency,
    SchedulerService,
    WorkerLease,
    calculate_freshness,
    calculate_health,
    cleanup_plan,
    readiness,
    register_sample,
)

NOW = datetime(2026, 7, 16, 12, tzinfo=UTC)


def test_network_policy_is_offline_by_default_and_metadata_is_distinct():
    with pytest.raises(PermissionError):
        NetworkPolicy().authorize("orats", network=True)
    policy = NetworkPolicy(NetworkMode.AUTHENTICATED_METADATA, ("orats",))
    policy.authorize("orats", network=True)
    with pytest.raises(PermissionError):
        policy.authorize("orats", network=True, download=True)


def test_sample_registration_never_retains_content_or_path_by_default(tmp_path):
    sample = tmp_path / "licensed.csv"
    sample.write_text("synthetic-user-content", encoding="utf-8")
    registration = register_sample("cboe", "user-dataset", sample)
    assert registration.storage_path is None
    assert "synthetic-user-content" not in repr(registration)


def test_scheduler_worker_health_freshness_and_readiness():
    schedule = ProviderSchedule(
        "daily-orats",
        "orats",
        "options",
        ("SPY",),
        ScheduleFrequency.DAILY,
        "America/New_York",
        NOW,
    )
    scheduler = SchedulerService()
    scheduler.add(schedule)
    assert scheduler.due(NOW) == (schedule,)
    assert scheduler.claim(schedule.schedule_id, NOW)
    assert not scheduler.claim(schedule.schedule_id, NOW)
    lease = WorkerLease("job", "worker", NOW + timedelta(minutes=1), NOW)
    lease.heartbeat(NOW + timedelta(seconds=30), timedelta(minutes=1))
    assert lease.expires_at == NOW + timedelta(seconds=90)
    health = calculate_health("orats", {"failure_rate": 0.0})
    assert health.status is HealthStatus.HEALTHY
    freshness = calculate_freshness(
        "orats", "options", NOW, NOW + timedelta(hours=3), timedelta(hours=1)
    )
    assert freshness.status is FreshnessStatus.STALE
    report = readiness(
        "orats",
        health,
        fixture_transport=True,
        credentials=CredentialStatus("orats", False, "environment"),
        sample_validated=False,
        mapping_approved=False,
    )
    assert report.status is ReadinessStatus.FIXTURE_ONLY


def test_alert_dedup_ack_resolution_and_cleanup_safety(tmp_path):
    alerts = AlertService()
    first = alerts.emit("polygon", "checksum_mismatch", "major", NOW)
    second = alerts.emit("polygon", "checksum_mismatch", "critical", NOW + timedelta(minutes=1))
    assert first.fingerprint == second.fingerprint and second.occurrences == 2
    assert alerts.acknowledge(first.fingerprint).acknowledged
    assert alerts.resolve(first.fingerprint).resolved
    candidate = tmp_path / "cache.bin"
    candidate.write_bytes(b"cache")
    plan = cleanup_plan((candidate,), tmp_path)
    assert not plan[0].authorized and candidate.exists()
