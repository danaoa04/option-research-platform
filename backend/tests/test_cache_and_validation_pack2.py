from __future__ import annotations

import json
from pathlib import Path

from backend.data.cache.manager import CacheManager
from backend.data.validation.engine import (
    ValidationEngine,
    ValidationMode,
    ValidationPolicy,
    ValidationSeverity,
)


def test_cache_manager_integrity_invalidation_and_cleanup(tmp_path: Path) -> None:
    cache = CacheManager(base_dir=tmp_path)
    cache.set("ok", {"value": 1}, manifest_checksum="m1")
    cache.set("drop", {"value": 2}, manifest_checksum="m2")

    assert cache.verify_integrity("ok", manifest_checksum="m1") is True
    assert cache.verify_integrity("ok", manifest_checksum="different") is False

    report = cache.invalidate(lambda entry: entry.cache_key == "drop")
    assert report.removed_invalidated == 1
    assert cache.contains("drop") is False

    bad_file = tmp_path / "corrupt.json"
    bad_file.write_text("{not-json", encoding="utf-8")

    cleanup = cache.cleanup()
    assert cleanup.removed_corrupt >= 1


def test_cache_manager_drops_corrupt_entry_on_read(tmp_path: Path) -> None:
    cache = CacheManager(base_dir=tmp_path)
    cache.set("sample", {"value": 10})

    hashed = next(tmp_path.glob("*.json"))
    payload = json.loads(hashed.read_text(encoding="utf-8"))
    payload["payload"] = {"value": 999}
    hashed.write_text(json.dumps(payload), encoding="utf-8")

    assert cache.get("sample") is None


def test_validation_engine_supports_collect_all_and_fail_fast() -> None:
    records = [
        {
            "id": "1",
            "timestamp": "bad",
            "option_chain": [{"strike": 0.0, "expiration": ""}],
            "implied_volatility": 1.3,
            "delta": 2.0,
            "gamma": 0.1,
            "theta": -0.1,
            "vega": 0.2,
            "rho": 0.1,
            "underlying_price": 10.0,
        },
    ]

    engine = ValidationEngine()
    collect_report = engine.validate_records(records)
    assert collect_report.summary.total_records == 1
    assert collect_report.summary.total_issues >= 3
    assert collect_report.summary.by_code["invalid_strike"] >= 1

    fail_fast_policy = ValidationPolicy(
        mode=ValidationMode.FAIL_FAST,
        fail_on_severities={ValidationSeverity.CRITICAL},
        severity_overrides={"invalid_strike": ValidationSeverity.CRITICAL},
    )
    fail_fast_report = engine.validate_records(records, policy=fail_fast_policy)

    assert fail_fast_report.mode == ValidationMode.FAIL_FAST
    assert len(fail_fast_report.issues) == 1
    assert fail_fast_report.issues[0].code == "invalid_strike"
