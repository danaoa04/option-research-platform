from __future__ import annotations

import os

import pytest

from backend.optimization import OptimizationBenchmarkRunner


@pytest.mark.skipif(
    os.getenv("RUN_OPT_IN_BENCHMARKS") != "1",
    reason="opt-in benchmark suite is disabled by default",
)
def test_opt_in_optimization_benchmarks_run() -> None:
    runner = OptimizationBenchmarkRunner.default()
    results = runner.run_all((1000,))

    assert results
    assert all(result.input_size == 1000 for result in results)
    assert all(result.elapsed_seconds >= 0.0 for result in results)
