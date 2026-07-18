from __future__ import annotations

from backend.performance import (
    BenchmarkStatus,
    GridLimit,
    ResumableWorkload,
    WorkloadProfileId,
    build_artifact_set,
    collect_metadata,
    compare_regressions,
    default_budgets,
    default_profiles,
    default_readiness_report,
    enforce_grid_limit,
    enforce_payload_limit,
    enforce_worker_limit,
    generate_synthetic_chain,
    paginate_chain,
    run_small_benchmarks,
)
from backend.performance.runtime import RegressionStatus
from backend.release.manifest import ReadinessStatus


def test_workload_profiles_and_synthetic_chain_are_deterministic() -> None:
    profiles = default_profiles()
    chain = generate_synthetic_chain(profiles[next(iter(profiles))])

    assert profiles[WorkloadProfileId.TINY].option_contracts == 16
    assert len(chain) == profiles[WorkloadProfileId.TINY].option_contracts
    assert chain[0]["option_identifier"] == "SYM00260116C00407000"


def test_metadata_pagination_and_payload_limits() -> None:
    profile = default_profiles()[WorkloadProfileId.SMALL]
    chain = generate_synthetic_chain(profile)
    page = paginate_chain(chain, page=1, page_size=25, symbol=chain[0]["symbol"], min_delta=0.2)
    metadata = collect_metadata(
        "chain_query",
        {"records": len(chain)},
        {"returned": len(page["items"])},
        duration_seconds=0.01,
        random_seed=7,
    )

    assert page["total_items"] >= len(page["items"])
    assert metadata.benchmark_id == "chain_query"
    assert enforce_payload_limit(page, maximum_bytes=64_000) > 0


def test_budget_regression_worker_and_grid_guards() -> None:
    limited = enforce_worker_limit(32, cpu_count=6, hard_limit=8)
    grid = enforce_grid_limit(GridLimit(rows=10, columns=10, hard_limit=200, warning_limit=80))

    assert limited == 6
    assert grid["status"] == "warning"
    assert compare_regressions(1.0, 0.85) is RegressionStatus.IMPROVED
    assert compare_regressions(1.0, 1.3) is RegressionStatus.BLOCKING_REGRESSION
    assert compare_regressions(None, 1.0) is RegressionStatus.INCOMPARABLE


def test_resumable_workload_supports_cancellation_and_resume() -> None:
    workload = ResumableWorkload(total_units=250, checkpoint_interval=50)
    cancelled = workload.run(cancel_after=125)
    resumed = workload.run(
        resume_state={"processed": cancelled["processed"], "checkpoints": cancelled["checkpoints"]}
    )

    assert cancelled["cancelled"] is True
    assert len(cancelled["checkpoints"]) == 2
    assert resumed["cancelled"] is False
    assert resumed["processed"] == 250


def test_small_benchmark_runner_and_readiness_are_deterministic() -> None:
    measurements = run_small_benchmarks()
    artifacts = build_artifact_set(measurements)
    readiness = default_readiness_report(measurements)
    budgets = default_budgets()

    assert measurements
    assert all(item.status in set(BenchmarkStatus) for item in measurements.values())
    assert "chain_generation" in measurements
    assert artifacts.performance_readiness["release_candidate_ready"] is True
    assert any(item.category == "endurance" for item in readiness.categories)
    assert any(item.status is ReadinessStatus.UNVALIDATED for item in readiness.categories)
    assert "resume_workload" in budgets
