"""Performance workload catalogues, measurements, and readiness reporting."""

from __future__ import annotations

import json
import os
import platform
import resource
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from time import perf_counter
from typing import Any

from backend.database.benchmarks.runtime import run_database_benchmarks
from backend.optimization import OptimizationBenchmarkRunner
from backend.portfolio import PortfolioBenchmarkRunner
from backend.release.config import load_release_config
from backend.release.manifest import ReadinessStatus
from backend.release.provenance import collect_provenance


class WorkloadProfileId(StrEnum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    VERY_LARGE = "very_large"
    ENDURANCE = "endurance"


@dataclass(slots=True, frozen=True)
class WorkloadProfile:
    profile: WorkloadProfileId
    symbols: int
    sessions: int
    expirations: int
    strikes: int
    option_contracts: int
    quotes: int
    trades: int
    strategies: int
    backtest_days: int
    optimizer_candidates: int
    cpcv_folds: int
    scenario_cells: int
    replay_events: int
    surface_nodes: int
    report_rows: int


@dataclass(slots=True, frozen=True)
class PerformanceProfile:
    hardware: str
    os_name: str
    release_profile: str
    warm_state: str


@dataclass(slots=True, frozen=True)
class BenchmarkMetadata:
    benchmark_id: str
    application_version: str
    git_commit: str
    dirty: bool
    hardware: str
    cpu: str
    memory_gb: float
    os_name: str
    python_version: str
    rust_version: str
    node_version: str
    workload_checksum: str
    random_seed: int
    started_at: str
    duration_seconds: float
    peak_memory_mb: float
    result_checksum: str


class BenchmarkStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass(slots=True, frozen=True)
class PerformanceBudget:
    benchmark_id: str
    profile: WorkloadProfileId
    performance_profile: PerformanceProfile
    pass_threshold_seconds: float
    warn_threshold_seconds: float
    fail_threshold_seconds: float


@dataclass(slots=True, frozen=True)
class BenchmarkMeasurement:
    benchmark_id: str
    duration_seconds: float
    profile: WorkloadProfileId
    status: BenchmarkStatus
    metadata: BenchmarkMetadata


class RegressionStatus(StrEnum):
    IMPROVED = "improved"
    STABLE = "stable"
    WARNING_REGRESSION = "warning_regression"
    BLOCKING_REGRESSION = "blocking_regression"
    INCOMPARABLE = "incomparable"


@dataclass(slots=True, frozen=True)
class PerformanceCategory:
    category: str
    status: ReadinessStatus
    evidence: str
    limitation: str | None = None


@dataclass(slots=True, frozen=True)
class PerformanceReadinessReport:
    application_version: str
    generated_at: str
    categories: tuple[PerformanceCategory, ...]

    @property
    def release_candidate_ready(self) -> bool:
        blockers = {ReadinessStatus.BLOCKED, ReadinessStatus.INCOMPLETE}
        return not any(item.status in blockers for item in self.categories)

    def serialize(self) -> dict[str, Any]:
        return {
            "application_version": self.application_version,
            "categories": [asdict(item) for item in self.categories],
            "generated_at": self.generated_at,
            "release_candidate_ready": self.release_candidate_ready,
        }


@dataclass(slots=True, frozen=True)
class BenchmarkArtifactSet:
    benchmark_summary: dict[str, Any]
    workload_manifest: dict[str, Any]
    backtest_benchmarks: dict[str, Any]
    optimizer_benchmarks: dict[str, Any]
    database_benchmarks: dict[str, Any]
    frontend_benchmarks: dict[str, Any]
    webgl_benchmarks: dict[str, Any]
    endurance_results: dict[str, Any]
    resource_usage: dict[str, Any]
    performance_readiness: dict[str, Any]


@dataclass(slots=True, frozen=True)
class GridLimit:
    rows: int
    columns: int
    hard_limit: int
    warning_limit: int


@dataclass(slots=True, frozen=True)
class CancellationMatrixEntry:
    category: str
    cancellation_acknowledged: bool
    resources_released: bool
    terminal_state: str


@dataclass(slots=True)
class ResumableWorkload:
    total_units: int
    checkpoint_interval: int = 100

    def run(
        self,
        *,
        cancel_after: int | None = None,
        resume_state: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        processed = int(resume_state["processed"]) if resume_state else 0
        checkpoints = list(resume_state["checkpoints"]) if resume_state else []
        started = perf_counter()
        while processed < self.total_units:
            processed += 1
            if processed % self.checkpoint_interval == 0:
                checkpoints.append(self._checkpoint(processed))
            if cancel_after is not None and processed >= cancel_after:
                return {
                    "cancelled": True,
                    "checkpoints": checkpoints,
                    "duration_seconds": perf_counter() - started,
                    "processed": processed,
                    "result_checksum": _checksum(
                        {"processed": processed, "checkpoints": checkpoints}
                    ),
                }
        return {
            "cancelled": False,
            "checkpoints": checkpoints,
            "duration_seconds": perf_counter() - started,
            "processed": processed,
            "result_checksum": _checksum({"processed": processed, "checkpoints": checkpoints}),
        }

    def _checkpoint(self, processed: int) -> dict[str, Any]:
        return {
            "checksum": _checksum({"processed": processed, "total_units": self.total_units}),
            "processed": processed,
            "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat(),
        }


def default_profiles() -> dict[WorkloadProfileId, WorkloadProfile]:
    return {
        WorkloadProfileId.TINY: WorkloadProfile(
            WorkloadProfileId.TINY, 1, 1, 2, 4, 16, 32, 0, 1, 5, 10, 2, 16, 64, 15, 25
        ),
        WorkloadProfileId.SMALL: WorkloadProfile(
            WorkloadProfileId.SMALL,
            2,
            5,
            4,
            8,
            128,
            512,
            64,
            2,
            20,
            100,
            3,
            64,
            512,
            64,
            100,
        ),
        WorkloadProfileId.MEDIUM: WorkloadProfile(
            WorkloadProfileId.MEDIUM,
            4,
            21,
            6,
            16,
            768,
            3_072,
            512,
            5,
            90,
            1_000,
            5,
            256,
            5_000,
            256,
            500,
        ),
        WorkloadProfileId.LARGE: WorkloadProfile(
            WorkloadProfileId.LARGE,
            8,
            63,
            12,
            32,
            6_144,
            24_576,
            4_096,
            10,
            365,
            10_000,
            8,
            2_048,
            25_000,
            2_048,
            2_000,
        ),
        WorkloadProfileId.VERY_LARGE: WorkloadProfile(
            WorkloadProfileId.VERY_LARGE,
            16,
            252,
            16,
            48,
            24_576,
            98_304,
            16_384,
            20,
            730,
            10_000,
            12,
            8_192,
            100_000,
            8_192,
            10_000,
        ),
        WorkloadProfileId.ENDURANCE: WorkloadProfile(
            WorkloadProfileId.ENDURANCE,
            8,
            1_000,
            12,
            32,
            6_144,
            250_000,
            50_000,
            20,
            1_500,
            10_000,
            12,
            20_000,
            100_000,
            4_096,
            20_000,
        ),
    }


def default_budgets() -> dict[str, PerformanceBudget]:
    profile = PerformanceProfile(
        hardware="local development machine",
        os_name=platform.system().lower(),
        release_profile="development",
        warm_state="warm",
    )
    return {
        "chain_generation": PerformanceBudget(
            "chain_generation", WorkloadProfileId.SMALL, profile, 0.05, 0.1, 0.25
        ),
        "chain_query": PerformanceBudget(
            "chain_query", WorkloadProfileId.SMALL, profile, 0.02, 0.05, 0.1
        ),
        "serialization": PerformanceBudget(
            "serialization", WorkloadProfileId.SMALL, profile, 0.02, 0.05, 0.1
        ),
        "database_batch_inserts": PerformanceBudget(
            "database_batch_inserts", WorkloadProfileId.SMALL, profile, 0.2, 0.5, 1.0
        ),
        "database_option_chain_queries": PerformanceBudget(
            "database_option_chain_queries", WorkloadProfileId.SMALL, profile, 0.2, 0.5, 1.0
        ),
        "database_quote_range_queries": PerformanceBudget(
            "database_quote_range_queries", WorkloadProfileId.SMALL, profile, 0.2, 0.5, 1.0
        ),
        "optimizer_candidate_generation": PerformanceBudget(
            "optimizer_candidate_generation", WorkloadProfileId.SMALL, profile, 0.2, 0.75, 1.5
        ),
        "portfolio_constraint_filtering": PerformanceBudget(
            "portfolio_constraint_filtering", WorkloadProfileId.SMALL, profile, 0.4, 1.0, 2.0
        ),
        "resume_workload": PerformanceBudget(
            "resume_workload", WorkloadProfileId.SMALL, profile, 0.05, 0.1, 0.25
        ),
    }


def collect_metadata(
    benchmark_id: str,
    workload: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    duration_seconds: float,
    random_seed: int,
) -> BenchmarkMetadata:
    provenance = collect_provenance("development")
    max_rss_kb = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    memory_mb = round(max_rss_kb / 1024.0, 3)
    return BenchmarkMetadata(
        benchmark_id=benchmark_id,
        application_version=load_release_config().versions.application_version,
        git_commit=provenance.git_commit,
        dirty=provenance.dirty,
        hardware="local development machine",
        cpu=platform.processor() or platform.machine(),
        memory_gb=round(_physical_memory_bytes() / (1024**3), 3),
        os_name=platform.platform(),
        python_version=provenance.python_version,
        rust_version=provenance.rust_version,
        node_version=provenance.node_version,
        workload_checksum=_checksum(workload),
        random_seed=random_seed,
        started_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        duration_seconds=round(duration_seconds, 6),
        peak_memory_mb=memory_mb,
        result_checksum=_checksum(result),
    )


def generate_synthetic_chain(
    profile: WorkloadProfile,
    *,
    seed: int = 7,
) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    base = 400 + seed
    symbols = [f"SYM{index:02d}" for index in range(profile.symbols)]
    for symbol_index, symbol in enumerate(symbols):
        for expiration_index in range(profile.expirations):
            expiration = (
                datetime(2026, 1, 16, tzinfo=UTC) + timedelta(days=7 * expiration_index)
            ).date()
            for strike_index in range(profile.strikes):
                strike = float(base + symbol_index * 5 + strike_index * 5)
                for option_type in ("C", "P"):
                    iv = round(0.18 + expiration_index * 0.01 + strike_index * 0.001, 6)
                    delta = (
                        round(0.5 - strike_index * 0.03, 6)
                        if option_type == "C"
                        else round(-0.5 + strike_index * 0.03, 6)
                    )
                    strike_code = f"{int(strike * 1000):08d}"
                    record = {
                        "symbol": symbol,
                        "expiration": expiration.isoformat(),
                        "strike": strike,
                        "option_type": option_type,
                        "option_identifier": (
                            f"{symbol}{expiration.strftime('%y%m%d')}{option_type}{strike_code}"
                        ),
                        "quote_timestamp": datetime(2026, 1, 15, 15, 30, tzinfo=UTC).isoformat(),
                        "bid": round(max(0.1, 5.0 - strike_index * 0.2), 4),
                        "ask": round(max(0.15, 5.2 - strike_index * 0.2), 4),
                        "last": round(max(0.12, 5.1 - strike_index * 0.2), 4),
                        "volume": 100 + strike_index * 3,
                        "open_interest": 500 + expiration_index * 10 + strike_index * 2,
                        "delta": delta,
                        "gamma": round(0.01 + strike_index * 0.0005, 6),
                        "theta": round(-0.02 - expiration_index * 0.001, 6),
                        "vega": round(0.12 + expiration_index * 0.002, 6),
                        "implied_volatility": iv,
                        "stale": strike_index == profile.strikes - 1 and option_type == "P",
                        "adjusted_contract": expiration_index == profile.expirations - 1
                        and strike_index == profile.strikes - 1,
                    }
                    records.append(record)
    return tuple(records[: profile.option_contracts])


def paginate_chain(
    records: Sequence[Mapping[str, Any]],
    *,
    page: int = 1,
    page_size: int = 100,
    symbol: str | None = None,
    expiration: str | None = None,
    min_delta: float | None = None,
    sort_key: str = "strike",
) -> dict[str, Any]:
    if page < 1:
        raise ValueError("page must be at least 1")
    if page_size < 1 or page_size > 500:
        raise ValueError("page_size must be between 1 and 500")
    filtered = [
        dict(record)
        for record in records
        if (symbol is None or record["symbol"] == symbol)
        and (expiration is None or record["expiration"] == expiration)
        and (min_delta is None or abs(float(record["delta"])) >= min_delta)
    ]
    ordered = sorted(filtered, key=lambda item: (item[sort_key], item["option_identifier"]))
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": ordered[start:end],
        "page": page,
        "page_size": page_size,
        "total_items": len(ordered),
        "total_pages": (len(ordered) + page_size - 1) // page_size,
    }


def enforce_payload_limit(value: Any, *, maximum_bytes: int) -> int:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    size = len(encoded)
    if size > maximum_bytes:
        raise ValueError(f"payload exceeds limit: {size} > {maximum_bytes}")
    return size


def enforce_worker_limit(
    requested: int,
    *,
    cpu_count: int | None = None,
    hard_limit: int = 8,
) -> int:
    available = cpu_count or max(_cpu_count(), 1)
    if requested < 1:
        raise ValueError("worker count must be at least 1")
    return min(requested, hard_limit, available)


def enforce_grid_limit(limit: GridLimit) -> dict[str, Any]:
    cells = limit.rows * limit.columns
    if cells > limit.hard_limit:
        raise ValueError("grid size exceeds hard limit")
    return {
        "cells": cells,
        "status": "warning" if cells > limit.warning_limit else "ok",
    }


def compare_regressions(
    baseline_seconds: float | None,
    current_seconds: float | None,
    *,
    warning_ratio: float = 0.1,
    blocking_ratio: float = 0.25,
) -> RegressionStatus:
    if baseline_seconds is None or current_seconds is None or baseline_seconds <= 0:
        return RegressionStatus.INCOMPARABLE
    change = (current_seconds - baseline_seconds) / baseline_seconds
    if change <= -warning_ratio:
        return RegressionStatus.IMPROVED
    if change >= blocking_ratio:
        return RegressionStatus.BLOCKING_REGRESSION
    if change >= warning_ratio:
        return RegressionStatus.WARNING_REGRESSION
    return RegressionStatus.STABLE


def run_small_benchmarks() -> dict[str, BenchmarkMeasurement]:
    budgets = default_budgets()
    profiles = default_profiles()
    workload = profiles[WorkloadProfileId.SMALL]
    chain = generate_synthetic_chain(workload)
    measurements: dict[str, BenchmarkMeasurement] = {}

    started = perf_counter()
    _ = generate_synthetic_chain(workload)
    duration = perf_counter() - started
    measurements["chain_generation"] = _measurement(
        "chain_generation",
        duration,
        workload,
        {"records": len(chain)},
        budgets["chain_generation"],
    )

    started = perf_counter()
    page = paginate_chain(chain, page=1, page_size=50, symbol=chain[0]["symbol"], min_delta=0.2)
    duration = perf_counter() - started
    measurements["chain_query"] = _measurement(
        "chain_query",
        duration,
        workload,
        {"returned": len(page["items"])},
        budgets["chain_query"],
    )

    started = perf_counter()
    payload_size = enforce_payload_limit(page, maximum_bytes=64_000)
    duration = perf_counter() - started
    measurements["serialization"] = _measurement(
        "serialization",
        duration,
        workload,
        {"payload_size": payload_size},
        budgets["serialization"],
    )

    for result in run_database_benchmarks(50):
        budget_key = f"database_{result.name}"
        if budget_key not in budgets:
            continue
        measurements[result.name] = _measurement(
            result.name,
            result.elapsed_seconds,
            workload,
            {"elapsed_seconds": result.elapsed_seconds},
            budgets[budget_key],
        )

    optimization_results = OptimizationBenchmarkRunner.default().run_all((100,))
    for optimization_result in optimization_results:
        if optimization_result.name == "candidate_generation":
            measurements["optimizer_candidate_generation"] = _measurement(
                "optimizer_candidate_generation",
                optimization_result.elapsed_seconds,
                workload,
                {"input_size": optimization_result.input_size},
                budgets["optimizer_candidate_generation"],
            )
            break

    portfolio_results = PortfolioBenchmarkRunner.default().run_all((100,))
    for portfolio_result in portfolio_results:
        if portfolio_result.name == "constraint_filtering":
            measurements["portfolio_constraint_filtering"] = _measurement(
                "portfolio_constraint_filtering",
                portfolio_result.elapsed_seconds,
                workload,
                {"input_size": portfolio_result.input_size},
                budgets["portfolio_constraint_filtering"],
            )
            break

    resumable = ResumableWorkload(total_units=500, checkpoint_interval=100)
    partial = resumable.run(cancel_after=250)
    resumed = resumable.run(
        resume_state={"processed": partial["processed"], "checkpoints": partial["checkpoints"]}
    )
    measurements["resume_workload"] = _measurement(
        "resume_workload",
        partial["duration_seconds"] + resumed["duration_seconds"],
        workload,
        {"processed": resumed["processed"], "cancelled": partial["cancelled"]},
        budgets["resume_workload"],
    )
    return measurements


def build_artifact_set(measurements: Mapping[str, BenchmarkMeasurement]) -> BenchmarkArtifactSet:
    profiles = default_profiles()
    small_profile = asdict(profiles[WorkloadProfileId.SMALL])
    readiness = default_readiness_report(measurements).serialize()
    summary = {
        name: {
            "duration_seconds": item.duration_seconds,
            "profile": item.profile.value,
            "status": item.status.value,
        }
        for name, item in sorted(measurements.items())
    }
    resource_usage = {
        name: {
            "cpu": item.metadata.cpu,
            "memory_gb": item.metadata.memory_gb,
            "peak_memory_mb": item.metadata.peak_memory_mb,
        }
        for name, item in sorted(measurements.items())
    }
    return BenchmarkArtifactSet(
        benchmark_summary={"benchmarks": summary},
        workload_manifest={
            "profiles": {key.value: asdict(value) for key, value in profiles.items()}
        },
        backtest_benchmarks={
            "status": "unvalidated",
            "reason": "heavy opt-in suites remain separate",
        },
        optimizer_benchmarks={"benchmarks": _subset(summary, "optimizer")},
        database_benchmarks={"benchmarks": _subset(summary, "database")},
        frontend_benchmarks={
            "status": "unvalidated",
            "limits": {
                "route_chunk_tracking": "documented",
                "virtualization_threshold": 250,
            },
        },
        webgl_benchmarks={
            "status": "unvalidated",
            "tested_node_profile": small_profile["surface_nodes"],
            "hard_limit": 5000,
        },
        endurance_results={
            "status": "unvalidated",
            "executed": False,
            "reason": "opt-in endurance runs are intentionally excluded from standard checks",
        },
        resource_usage=resource_usage,
        performance_readiness=readiness,
    )


def default_readiness_report(
    measurements: Mapping[str, BenchmarkMeasurement],
) -> PerformanceReadinessReport:
    version = load_release_config().versions.application_version
    categories = (
        _category("chain_ingestion", "chain_generation", measurements),
        _category("chain_querying", "chain_query", measurements),
        _category("database", "batch_inserts", measurements),
        _category("backtesting", None, measurements, "small deterministic harness only"),
        _category("optimizer", "optimizer_candidate_generation", measurements),
        _category("walk_forward", None, measurements, "deferred heavy benchmark tier"),
        _category("cpcv", None, measurements, "deferred heavy benchmark tier"),
        _category("portfolio", "portfolio_constraint_filtering", measurements),
        _category("scenarios", None, measurements, "grid-size guards only"),
        _category("replay", None, measurements, "deferred heavy benchmark tier"),
        _category("reports", "serialization", measurements),
        _category(
            "volatility_surfaces",
            None,
            measurements,
            "frontend/WebGL prep remains local-only",
        ),
        _category("webgl", None, measurements, "fallback and node-limit guards only"),
        _category("frontend", None, measurements, "route timing remains unvalidated"),
        _category("sidecar", None, measurements, "startup endurance not executed"),
        _category("cancellation", "resume_workload", measurements),
        _category(
            "crash_recovery",
            None,
            measurements,
            "covered by prior recovery gates, not stressed here",
        ),
        _category("endurance", None, measurements, "opt-in only and not executed"),
        _category("memory", None, measurements, "metadata captured; pressure suite not executed"),
        _category("disk", None, measurements, "pressure suite not executed"),
        _category("cpu", None, measurements, "pressure suite not executed"),
        _category("regression_monitoring", "serialization", measurements),
    )
    return PerformanceReadinessReport(
        application_version=version,
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        categories=categories,
    )


def _measurement(
    benchmark_id: str,
    duration_seconds: float,
    workload: WorkloadProfile,
    result: Mapping[str, Any],
    budget: PerformanceBudget,
) -> BenchmarkMeasurement:
    status = _budget_status(duration_seconds, budget)
    metadata = collect_metadata(
        benchmark_id,
        asdict(workload),
        result,
        duration_seconds=duration_seconds,
        random_seed=7,
    )
    return BenchmarkMeasurement(
        benchmark_id=benchmark_id,
        duration_seconds=round(duration_seconds, 6),
        profile=workload.profile,
        status=status,
        metadata=metadata,
    )


def _budget_status(duration_seconds: float, budget: PerformanceBudget) -> BenchmarkStatus:
    if duration_seconds <= budget.pass_threshold_seconds:
        return BenchmarkStatus.PASS
    if duration_seconds <= budget.warn_threshold_seconds:
        return BenchmarkStatus.WARN
    return BenchmarkStatus.FAIL


def _category(
    category: str,
    evidence_key: str | None,
    measurements: Mapping[str, BenchmarkMeasurement],
    limitation: str | None = None,
) -> PerformanceCategory:
    if evidence_key is None or evidence_key not in measurements:
        return PerformanceCategory(
            category,
            ReadinessStatus.UNVALIDATED,
            "not measured",
            limitation,
        )
    measurement = measurements[evidence_key]
    status = (
        ReadinessStatus.READY
        if measurement.status is BenchmarkStatus.PASS
        else ReadinessStatus.READY_WITH_WARNINGS
        if measurement.status is BenchmarkStatus.WARN
        else ReadinessStatus.BLOCKED
    )
    return PerformanceCategory(
        category,
        status,
        f"{measurement.benchmark_id}:{measurement.duration_seconds:.6f}s",
        limitation,
    )


def _subset(summary: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    return {name: value for name, value in summary.items() if prefix in name}


def _checksum(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


def _cpu_count() -> int:
    count = os.cpu_count()
    return count if count is not None else 1


def _physical_memory_bytes() -> int:
    try:
        pages = resource.getpagesize()
        return pages * int(resource.getrlimit(resource.RLIMIT_DATA)[0] or 0) or 8 * 1024**3
    except (OSError, ValueError):
        return 8 * 1024**3
