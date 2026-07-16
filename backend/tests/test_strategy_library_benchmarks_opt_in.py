from __future__ import annotations

from backend.backtesting.strategy_library_benchmarks import StrategyLibraryBenchmarkRunner


def test_strategy_library_benchmarks_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("RUN_STRATEGY_LIBRARY_BENCHMARKS", raising=False)
    runner = StrategyLibraryBenchmarkRunner()
    assert runner.run_all() == []


def test_strategy_library_benchmarks_run_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("RUN_STRATEGY_LIBRARY_BENCHMARKS", "1")
    runner = StrategyLibraryBenchmarkRunner()
    results = runner.run_all()
    assert len(results) == 9
    assert all(item.elapsed_seconds >= 0.0 for item in results)
