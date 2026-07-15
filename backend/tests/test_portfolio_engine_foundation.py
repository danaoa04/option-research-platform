from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.portfolio import (
    AllocationProblem,
    CandidateExposure,
    CandidateInput,
    CandidateStats,
    CandidateValidationSnapshot,
    ConstraintDefinition,
    ConstraintSeverity,
    ConstructionMethod,
    CorrelationEngine,
    CorrelationKind,
    EligibilityEngine,
    EligibilityPolicy,
    ExposureAggregator,
    ObjectiveDefinition,
    ObjectiveDirection,
    ObjectiveMode,
    PortfolioAllocator,
    SizingPolicy,
)


def _candidate(
    candidate_id: str,
    *,
    robustness: float = 0.8,
    promotion_status: str = "validated",
    returns: tuple[float, ...] = (0.01, -0.005, 0.012, 0.004),
    timestamps: tuple[datetime, ...] | None = None,
) -> CandidateInput:
    now = datetime(2026, 2, 1, tzinfo=UTC)
    return CandidateInput(
        candidate_id=candidate_id,
        validation=CandidateValidationSnapshot(
            candidate_id=candidate_id,
            promotion_status=promotion_status,
            robustness_score=robustness,
            pbo=0.1,
            deflated_sharpe=0.8,
            out_of_sample_fold_count=5,
            calibration_error=0.05,
            sample_size=200,
            parameter_stability=0.8,
            regime_coverage=0.8,
            stress_degradation=0.8,
            liquidity=0.8,
            data_quality=0.8,
        ),
        exposure=CandidateExposure(
            candidate_id=candidate_id,
            delta=0.2,
            gamma=0.05,
            theta=0.03,
            vega=0.08,
            rho=0.01,
            vanna=0.0,
            charm=0.0,
            sector="technology",
            industry="software",
            symbol=f"SYM-{candidate_id}",
            index_exposure="SPY",
            expiration_bucket="30d",
            strategy_family="calendar",
            volatility_regime="medium",
            term_structure_regime="contango",
            event_exposure=0.02,
            earnings_exposure=0.01,
            capital_requirement=5_000.0,
            expected_shortfall=0.08,
            maximum_drawdown=0.12,
            liquidity_score=0.9,
            model_risk_score=0.2,
        ),
        stats=CandidateStats(
            candidate_id=candidate_id,
            expected_return=0.12,
            expected_value=0.09,
            sharpe=1.1,
            sortino=1.4,
            calmar=0.9,
            theta_income=0.04,
            volatility=0.15,
            expected_shortfall=0.08,
            tail_loss=0.1,
            maximum_drawdown=0.12,
            turnover=0.2,
            capital_usage=0.2,
            downside_deviation=0.09,
            liquidity_risk=0.2,
            model_risk=0.2,
            regime_exposure={"low": 0.4, "high": 0.6},
        ),
        returns=returns,
        pnl=tuple(value * 1000 for value in returns),
        underlying_returns=tuple(value * 0.8 for value in returns),
        drawdowns=(0.03, 0.05, 0.04, 0.02),
        tail_losses=(0.04, 0.06, 0.05, 0.03),
        timestamps=timestamps if timestamps is not None else (now, now, now, now),
    )


def _policy() -> EligibilityPolicy:
    return EligibilityPolicy(
        allowed_promotions=("validated",),
        minimum_robustness=0.6,
        maximum_pbo=0.2,
        minimum_deflated_sharpe=0.3,
        minimum_out_of_sample_folds=3,
        maximum_calibration_error=0.2,
        minimum_sample_size=100,
        minimum_parameter_stability=0.5,
        minimum_regime_coverage=0.5,
        minimum_stress_resilience=0.5,
        minimum_liquidity=0.5,
        minimum_data_quality=0.5,
    )


def _problem(candidates: tuple[CandidateInput, ...], *, as_of: datetime) -> AllocationProblem:
    return AllocationProblem(
        problem_id="portfolio-foundation",
        eligible_candidates=candidates,
        available_capital=250_000.0,
        reserve_cash=25_000.0,
        objectives=(
            ObjectiveDefinition(
                name="max_return",
                direction=ObjectiveDirection.MAXIMIZE,
                metric_key="expected_return",
                weight=1.0,
            ),
        ),
        hard_constraints=(
            ConstraintDefinition(
                name="max_portfolio_vega",
                metric_key="portfolio_vega",
                operator="<=",
                threshold=1.0,
                severity=ConstraintSeverity.HARD,
            ),
        ),
        soft_constraints=(
            ConstraintDefinition(
                name="min_liquidity",
                metric_key="liquidity",
                operator=">=",
                threshold=0.5,
                severity=ConstraintSeverity.SOFT,
                penalty=0.02,
            ),
        ),
        rebalance_policy={"frequency": "monthly"},
        position_size_granularity=0.01,
        margin_policy_placeholder={"mode": "research-only"},
        regime_policy={"max_single_regime": 0.75},
        diversification_policy={"max_weight_per_strategy": 0.5, "min_weight_per_strategy": 0.0},
        portfolio_risk_limits={"max_drawdown": 0.25},
        dataset_manifests=(101, 102),
        software_git_commit="abc123",
        objective_mode=ObjectiveMode.WEIGHTED,
        metadata={"eligibility_policy": _policy(), "as_of_timestamp": as_of},
    )


def test_eligibility_filters_and_reasons() -> None:
    engine = EligibilityEngine()
    good = _candidate("good")
    bad = _candidate("bad", promotion_status="explore", robustness=0.4)

    eligible, rejected = engine.filter_candidates((good, bad), _policy())

    assert [item.candidate_id for item in eligible] == ["good"]
    assert len(rejected) == 1
    assert rejected[0].candidate_id == "bad"
    assert "promotion_status" in rejected[0].reasons
    assert "minimum_robustness" in rejected[0].reasons


def test_exposure_aggregation_outputs_totals_and_categories() -> None:
    aggregator = ExposureAggregator()
    first = _candidate("a")
    second = _candidate("b")
    allocations = (
        # Weights sum to 1 for straightforward deterministic checks.
        type("Alloc", (), {"candidate_id": "a", "weight": 0.6})(),
        type("Alloc", (), {"candidate_id": "b", "weight": 0.4})(),
    )

    normalized = aggregator.normalize(first.exposure)
    portfolio = aggregator.aggregate_portfolio_exposure((first, second), allocations)

    assert normalized["sector"] == "technology"
    assert portfolio["totals"]["delta"] == pytest.approx(0.2)
    assert "symbol" in portfolio["categories"]


def test_correlation_sparse_warning_and_matrix_shape() -> None:
    corr = CorrelationEngine(min_samples=10)
    a = _candidate("a", returns=(0.01, 0.02, 0.03))
    b = _candidate("b", returns=(0.01, 0.01, 0.01))

    estimates = corr.estimate((a, b), CorrelationKind.STRATEGY_RETURN)
    matrix = corr.matrix(estimates)

    assert estimates
    assert any(item.sparse_warning for item in estimates)
    assert set(matrix.keys()) == {"a", "b"}
    assert matrix["a"]["a"] == 1.0


def test_construct_enforces_no_lookahead() -> None:
    allocator = PortfolioAllocator.default()
    as_of = datetime(2026, 2, 1, tzinfo=UTC)
    future = datetime(2026, 2, 2, tzinfo=UTC)
    candidate = _candidate("future", timestamps=(future,))
    problem = _problem((candidate,), as_of=as_of)

    with pytest.raises(ValueError, match="no-look-ahead"):
        allocator.construct(
            run_id="run-no-lookahead",
            candidates=(candidate,),
            problem=problem,
            construction_method=ConstructionMethod.CONSTRAINED_GREEDY,
            sizing_policy=SizingPolicy.EQUAL_WEIGHT,
        )


def test_allocator_constructs_deterministic_allocations() -> None:
    allocator = PortfolioAllocator.default()
    as_of = datetime(2026, 2, 1, tzinfo=UTC)
    candidates = (_candidate("a"), _candidate("b"))
    problem = _problem(candidates, as_of=as_of)

    result_one = allocator.construct(
        run_id="run-1",
        candidates=candidates,
        problem=problem,
        construction_method=ConstructionMethod.CONSTRAINED_GREEDY,
        sizing_policy=SizingPolicy.INVERSE_VOLATILITY,
    )
    result_two = allocator.construct(
        run_id="run-1",
        candidates=candidates,
        problem=problem,
        construction_method=ConstructionMethod.CONSTRAINED_GREEDY,
        sizing_policy=SizingPolicy.INVERSE_VOLATILITY,
    )

    assert result_one.selected_allocations
    assert [item.candidate_id for item in result_one.selected_allocations] == ["a", "b"]
    assert result_one.checksum == result_two.checksum
    assert not result_one.failures
