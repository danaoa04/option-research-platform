from __future__ import annotations

import os

import pytest

from backend.research import CalendarResearchBenchmarkRunner, CalendarResearchEngine


@pytest.mark.skipif(
    os.getenv("RUN_OPT_IN_BENCHMARKS") != "1",
    reason="opt-in benchmark suite is disabled by default",
)
def test_opt_in_calendar_research_benchmarks_run() -> None:
    runner = CalendarResearchBenchmarkRunner(engine=CalendarResearchEngine.default())
    results = runner.run_all((1000,))

    assert results
    assert all(result.input_size == 1000 for result in results)
    assert all(result.elapsed_seconds >= 0.0 for result in results)
