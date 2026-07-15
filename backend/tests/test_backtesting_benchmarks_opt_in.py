from __future__ import annotations

from backend.backtesting.benchmarks import BacktestBenchmarkRunner


def test_backtesting_benchmarks_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("RUN_BACKTEST_BENCHMARKS", raising=False)
    runner = BacktestBenchmarkRunner.default()
    assert runner.run_all() == []


def test_backtesting_benchmarks_run_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("RUN_BACKTEST_BENCHMARKS", "1")
    runner = BacktestBenchmarkRunner.default()
    results = runner.run_all()
    assert len(results) == 4
    assert all(item.elapsed_seconds >= 0.0 for item in results)
