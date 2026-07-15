from __future__ import annotations

from backend.backtesting.execution_benchmarks import ExecutionBenchmarkRunner


def test_execution_benchmarks_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("RUN_EXECUTION_BENCHMARKS", raising=False)
    runner = ExecutionBenchmarkRunner()
    assert runner.run_all() == []


def test_execution_benchmarks_run_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("RUN_EXECUTION_BENCHMARKS", "1")
    runner = ExecutionBenchmarkRunner()
    results = runner.run_all()
    assert len(results) == 6
    assert all(item.elapsed_seconds >= 0.0 for item in results)
