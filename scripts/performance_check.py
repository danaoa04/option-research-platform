"""Evaluate deterministic small-workload performance budgets."""

from __future__ import annotations

from backend.performance import BenchmarkStatus, default_readiness_report, run_small_benchmarks


def main() -> int:
    measurements = run_small_benchmarks()
    failures = sorted(
        measurement.benchmark_id
        for measurement in measurements.values()
        if measurement.status is BenchmarkStatus.FAIL
    )
    report = default_readiness_report(measurements)
    if failures:
        raise SystemExit(f"Blocking performance regressions: {', '.join(failures)}")
    blocked = [item.category for item in report.categories if item.status.value == "blocked"]
    if blocked:
        raise SystemExit(f"Performance readiness blocked: {', '.join(blocked)}")
    print("performance check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
