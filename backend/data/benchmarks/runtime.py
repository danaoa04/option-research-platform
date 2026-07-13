"""Benchmark harness kept separate from unit tests to preserve normal test speed."""

from __future__ import annotations

import tempfile
import time
from dataclasses import dataclass
from datetime import date

from backend.data.cache.manager import CacheManager
from backend.data.models.manifest import build_dataset_manifest
from backend.data.providers.registry import ProviderRegistry
from backend.data.update.planner import DateRange, plan_incremental_update
from backend.data.validation.engine import ValidationEngine


@dataclass(slots=True, frozen=True)
class BenchmarkResult:
    """Single benchmark timing result."""

    name: str
    elapsed_seconds: float


def run_all_benchmarks(iterations: int = 100) -> list[BenchmarkResult]:
    """Execute all benchmark scenarios and return elapsed timings."""
    return [
        _benchmark_provider_lookup(iterations),
        _benchmark_manifest_serialization(iterations),
        _benchmark_cache_read_write(iterations),
        _benchmark_validation_throughput(iterations),
        _benchmark_update_planning(iterations),
    ]


def _benchmark_provider_lookup(iterations: int) -> BenchmarkResult:
    registry = ProviderRegistry()
    registry.register("a", object)
    registry.register("b", object)

    started = time.perf_counter()
    for _ in range(iterations):
        registry.get_provider_class("a")
        registry.get_provider_class("b")
    elapsed = time.perf_counter() - started
    return BenchmarkResult(name="provider_lookup", elapsed_seconds=elapsed)


def _benchmark_manifest_serialization(iterations: int) -> BenchmarkResult:
    manifest = build_dataset_manifest(
        provider="csv",
        dataset_name="bench",
        dataset_version="2026.07",
        schema_version="1.0",
        symbol_scope=["SPY", "QQQ", "IWM"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        row_count=500,
        source_metadata={"source": "benchmark"},
    )

    started = time.perf_counter()
    for _ in range(iterations):
        manifest.to_json()
    elapsed = time.perf_counter() - started
    return BenchmarkResult(name="manifest_serialization", elapsed_seconds=elapsed)


def _benchmark_cache_read_write(iterations: int) -> BenchmarkResult:
    with tempfile.TemporaryDirectory() as tempdir:
        cache = CacheManager(base_dir=tempdir)
        started = time.perf_counter()
        for idx in range(iterations):
            key = f"k-{idx}"
            cache.set(key, {"idx": idx}, manifest_checksum="deadbeef")
            cache.get(key)
        elapsed = time.perf_counter() - started
    return BenchmarkResult(name="cache_read_write", elapsed_seconds=elapsed)


def _benchmark_validation_throughput(iterations: int) -> BenchmarkResult:
    engine = ValidationEngine()
    records = [
        {
            "id": str(idx),
            "timestamp": "2026-01-05T00:00:00Z",
            "option_chain": [{"strike": 100.0, "expiration": "2026-02-20"}],
            "implied_volatility": 0.2,
            "delta": 0.3,
            "gamma": 0.02,
            "theta": -0.05,
            "vega": 0.1,
            "rho": 0.05,
            "underlying_price": 500.0,
        }
        for idx in range(max(iterations, 10))
    ]

    started = time.perf_counter()
    for _ in range(iterations):
        engine.validate_records(records)
    elapsed = time.perf_counter() - started
    return BenchmarkResult(name="validation_throughput", elapsed_seconds=elapsed)


def _benchmark_update_planning(iterations: int) -> BenchmarkResult:
    requested = DateRange(start=date(2026, 1, 1), end=date(2026, 3, 31))
    cached_ranges = [
        DateRange(start=date(2026, 1, 1), end=date(2026, 1, 15)),
        DateRange(start=date(2026, 2, 1), end=date(2026, 2, 10)),
    ]

    started = time.perf_counter()
    for _ in range(iterations):
        plan_incremental_update(requested, cached_ranges)
    elapsed = time.perf_counter() - started
    return BenchmarkResult(name="update_planning", elapsed_seconds=elapsed)
