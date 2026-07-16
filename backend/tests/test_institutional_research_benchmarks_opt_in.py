from __future__ import annotations

from backend.research import InstitutionalResearchBenchmarkRunner


def test_institutional_research_benchmarks_are_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("RUN_INSTITUTIONAL_RESEARCH_BENCHMARKS", raising=False)
    assert InstitutionalResearchBenchmarkRunner().run_all() == []
