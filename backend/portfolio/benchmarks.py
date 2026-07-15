"""Opt-in deterministic portfolio benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from .allocation import PortfolioAllocator
from .models import (
    AllocationProblem,
    CandidateExposure,
    CandidateInput,
    CandidateStats,
    CandidateValidationSnapshot,
    ConstraintDefinition,
    ConstraintSeverity,
    ConstructionMethod,
    EligibilityPolicy,
    ObjectiveDefinition,
    ObjectiveDirection,
    ObjectiveMode,
    SizingPolicy,
)


@dataclass(slots=True, frozen=True)
class PortfolioBenchmarkResult:
    name: str
    input_size: int
    elapsed_seconds: float


@dataclass(slots=True)
class PortfolioBenchmarkRunner:
    allocator: PortfolioAllocator

    @classmethod
    def default(cls) -> PortfolioBenchmarkRunner:
        return cls(allocator=PortfolioAllocator.default())

    def run_all(
        self, sizes: tuple[int, ...] = (100, 1000, 10000)
    ) -> list[PortfolioBenchmarkResult]:
        output: list[PortfolioBenchmarkResult] = []
        for size in sizes:
            candidates = self._candidates(size)
            problem = self._problem(candidates)
            output.append(self._bench("constraint_filtering", size, candidates, problem))
            output.append(self._bench("greedy_allocation", size, candidates, problem))
            output.append(self._bench("risk_contributions", size, candidates, problem))
            output.append(self._bench("scenario_aggregation", size, candidates, problem))
        return output

    def _bench(
        self,
        name: str,
        size: int,
        candidates: tuple[CandidateInput, ...],
        problem: AllocationProblem,
    ) -> PortfolioBenchmarkResult:
        started = perf_counter()
        _ = self.allocator.construct(
            run_id=f"benchmark-{name}-{size}",
            candidates=candidates,
            problem=problem,
            construction_method=ConstructionMethod.CONSTRAINED_GREEDY,
            sizing_policy=SizingPolicy.INVERSE_VOLATILITY,
            scenarios=(),
        )
        return PortfolioBenchmarkResult(
            name=name, input_size=size, elapsed_seconds=perf_counter() - started
        )

    def _problem(self, candidates: tuple[CandidateInput, ...]) -> AllocationProblem:
        return AllocationProblem(
            problem_id="portfolio-benchmark",
            eligible_candidates=candidates,
            available_capital=1_000_000.0,
            reserve_cash=50_000.0,
            objectives=(
                ObjectiveDefinition(
                    name="maximize_robustness_adjusted_return",
                    direction=ObjectiveDirection.MAXIMIZE,
                    weight=1.0,
                    metric_key="expected_return",
                ),
            ),
            hard_constraints=(
                ConstraintDefinition(
                    name="max_portfolio_vega",
                    metric_key="portfolio_vega",
                    operator="<=",
                    threshold=2.0,
                    severity=ConstraintSeverity.HARD,
                ),
            ),
            soft_constraints=(
                ConstraintDefinition(
                    name="min_liquidity",
                    metric_key="liquidity",
                    operator=">=",
                    threshold=0.2,
                    severity=ConstraintSeverity.SOFT,
                    penalty=0.02,
                ),
            ),
            rebalance_policy={"frequency": "monthly"},
            position_size_granularity=0.01,
            margin_policy_placeholder={"policy": "placeholder"},
            regime_policy={"max_single_regime": 0.7},
            diversification_policy={"max_weight_per_strategy": 0.15},
            portfolio_risk_limits={"max_drawdown": 0.2, "max_expected_shortfall": 0.15},
            dataset_manifests=(1,),
            software_git_commit="benchmark",
            objective_mode=ObjectiveMode.WEIGHTED,
            metadata={
                "eligibility_policy": EligibilityPolicy(
                    allowed_promotions=("validated", "robust", "production_candidate"),
                    minimum_robustness=0.4,
                    maximum_pbo=0.5,
                    minimum_deflated_sharpe=0.2,
                    minimum_out_of_sample_folds=3,
                    maximum_calibration_error=0.3,
                    minimum_sample_size=50,
                    minimum_parameter_stability=0.3,
                    minimum_regime_coverage=0.3,
                    minimum_stress_resilience=0.2,
                    minimum_liquidity=0.2,
                    minimum_data_quality=0.2,
                ),
            },
        )

    def _candidates(self, size: int) -> tuple[CandidateInput, ...]:
        output: list[CandidateInput] = []
        now = datetime.utcnow()
        for index in range(size):
            candidate_id = f"candidate-{index:05d}"
            output.append(
                CandidateInput(
                    candidate_id=candidate_id,
                    validation=CandidateValidationSnapshot(
                        candidate_id=candidate_id,
                        promotion_status="validated",
                        robustness_score=0.5 + (index % 10) * 0.01,
                        pbo=0.2,
                        deflated_sharpe=0.5,
                        out_of_sample_fold_count=5,
                        calibration_error=0.1,
                        sample_size=200,
                        parameter_stability=0.6,
                        regime_coverage=0.7,
                        stress_degradation=0.5,
                        liquidity=0.8,
                        data_quality=0.9,
                    ),
                    exposure=CandidateExposure(
                        candidate_id=candidate_id,
                        delta=((index % 7) - 3) / 10.0,
                        gamma=((index % 5) - 2) / 20.0,
                        theta=0.05,
                        vega=((index % 11) - 5) / 20.0,
                        rho=0.01,
                        vanna=0.0,
                        charm=0.0,
                        sector=f"sector-{index % 6}",
                        industry=f"industry-{index % 12}",
                        symbol=f"SYM{index % 40}",
                        index_exposure="SPY",
                        expiration_bucket=f"{30 + (index % 4) * 30}d",
                        strategy_family=f"family-{index % 5}",
                        volatility_regime=("low", "medium", "high")[index % 3],
                        term_structure_regime=("contango", "backwardation")[index % 2],
                        event_exposure=0.1,
                        earnings_exposure=0.05,
                        capital_requirement=5000.0,
                        expected_shortfall=0.08,
                        maximum_drawdown=0.12,
                        liquidity_score=0.8,
                        model_risk_score=0.2,
                    ),
                    stats=CandidateStats(
                        candidate_id=candidate_id,
                        expected_return=0.12,
                        expected_value=0.08,
                        sharpe=1.1,
                        sortino=1.4,
                        calmar=0.9,
                        theta_income=0.05,
                        volatility=0.15,
                        expected_shortfall=0.08,
                        tail_loss=0.1,
                        maximum_drawdown=0.12,
                        turnover=0.2,
                        capital_usage=0.04,
                        downside_deviation=0.09,
                        liquidity_risk=0.2,
                        model_risk=0.2,
                        regime_exposure={"low": 0.5, "high": 0.5},
                    ),
                    returns=tuple(0.01 for _ in range(60)),
                    pnl=tuple(10.0 for _ in range(60)),
                    underlying_returns=tuple(0.005 for _ in range(60)),
                    drawdowns=tuple(0.02 for _ in range(60)),
                    tail_losses=tuple(0.03 for _ in range(60)),
                    timestamps=tuple(now for _ in range(60)),
                )
            )
        return tuple(output)
