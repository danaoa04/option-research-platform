from __future__ import annotations

import pytest

from backend.research import (
    AttributionEngine,
    PortfolioAnalyticsEngine,
    PortfolioDiagnosticsEngine,
    ResearchObservation,
    ResearchScoreEngine,
    RobustnessEngine,
    StrategyComparisonEngine,
    audit_decision,
)


def _observations() -> tuple[ResearchObservation, ...]:
    return (
        ResearchObservation(
            return_value=0.02,
            pnl=20,
            benchmark_return=0.01,
            capital=100,
            margin=50,
            turnover=0.1,
            holding_period_days=10,
            rolled=True,
            survived_scenario=True,
            dimensions={
                "symbol": "SPY",
                "underlying": "SPY",
                "strategy": "calendar",
                "strategy_family": "time_spread",
                "expiration": "2026-08",
                "volatility_regime": "high",
                "earnings_regime": "none",
                "term_structure": "contango",
                "management_policy": "standard",
                "roll_policy": "theta",
                "execution_policy": "mid",
                "broker_policy": "research",
                "scenario": "base",
                "calendar_period": "2026-07",
                "sector": "index",
                "direction": "neutral",
            },
        ),
        ResearchObservation(
            return_value=-0.01,
            pnl=-10,
            benchmark_return=-0.02,
            capital=100,
            margin=50,
            turnover=0.2,
            holding_period_days=12,
            assigned=True,
            survived_scenario=False,
            dimensions={"symbol": "QQQ", "strategy": "calendar", "sector": "index"},
        ),
    )


def test_institutional_analytics_attribution_and_diagnostics_are_deterministic() -> None:
    observations = _observations()
    analytics = PortfolioAnalyticsEngine().compute(observations, rolling_window=2)
    assert analytics.metrics["average_win"] == 20
    assert analytics.metrics["assignment_frequency"] == 0.5
    assert analytics.rolling["sharpe"]

    attribution = AttributionEngine().summarize(observations)
    assert attribution["symbol"]["SPY"]["pnl"] == 20
    assert attribution["strategy"]["calendar"]["count"] == 2

    diagnostics = PortfolioDiagnosticsEngine().evaluate(observations)
    assert diagnostics["expiration_concentration"] == 1.0


def test_robustness_score_comparison_and_decision_audit() -> None:
    robustness = RobustnessEngine().evaluate(
        parameter_scores=(0.8, 0.9),
        cpcv_sharpes=(1.1, 0.8),
        walk_forward_scores=(0.7, 0.9),
        stress_survival=(True, False),
    )
    assert robustness.metrics["pbo"] == 0.0
    assert robustness.metrics["confidence_score"] is not None

    incomplete = ResearchScoreEngine().score({"robustness": 0.9})
    assert incomplete.score is None
    complete = ResearchScoreEngine().score({key: 0.8 for key in ResearchScoreEngine.weights})
    assert complete.score == 0.8

    comparison = StrategyComparisonEngine().compare({"a": {"sharpe": 1.0}, "b": {"sharpe": 1.2}})
    assert comparison["a"]["b"]["sharpe"] == pytest.approx(0.2)
    audit = audit_decision(
        why=("liquidity passed",),
        alternatives=(),
        confidence=None,
        assumptions=("offline",),
        supporting_data={"spread": 0.1},
        rejected_alternatives=(),
        uncertainty=("sample size",),
    )
    assert audit["confidence"] is None
