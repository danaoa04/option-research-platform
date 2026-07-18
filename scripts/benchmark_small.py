"""Generate deterministic small-workload performance artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from backend.performance import build_artifact_set, run_small_benchmarks

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "release-artifacts" / "performance"


def main() -> int:
    measurements = run_small_benchmarks()
    artifacts = build_artifact_set(measurements)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    payloads = {
        "benchmark-summary.json": artifacts.benchmark_summary,
        "workload-manifest.json": artifacts.workload_manifest,
        "backtest-benchmarks.json": artifacts.backtest_benchmarks,
        "optimizer-benchmarks.json": artifacts.optimizer_benchmarks,
        "database-benchmarks.json": artifacts.database_benchmarks,
        "frontend-benchmarks.json": artifacts.frontend_benchmarks,
        "WebGL-benchmarks.json": artifacts.webgl_benchmarks,
        "endurance-results.json": artifacts.endurance_results,
        "resource-usage.json": artifacts.resource_usage,
        "performance-readiness.json": artifacts.performance_readiness,
    }
    for name, value in payloads.items():
        (ARTIFACTS / name).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(ARTIFACTS.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
