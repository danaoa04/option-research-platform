"""Offline, explainable institutional research analytics.

The module deliberately accepts plain, recorded observations.  It never invents
missing inputs: unavailable score components remain unavailable and are called
out in the returned evidence.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from statistics import fmean
from typing import Any, cast


def _mean(values: Iterable[float]) -> float:
    values = tuple(values)
    return fmean(values) if values else 0.0


def _sample_std(values: Iterable[float]) -> float:
    values = tuple(values)
    if len(values) < 2:
        return 0.0
    average = _mean(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / (len(values) - 1))


def _ratio(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0.0 else numerator / denominator


@dataclass(frozen=True, slots=True)
class ResearchObservation:
    """One realized period/trade, with dimensions retained for attribution."""

    return_value: float
    pnl: float = 0.0
    benchmark_return: float | None = None
    capital: float = 0.0
    margin: float = 0.0
    turnover: float = 0.0
    holding_period_days: float = 0.0
    assigned: bool = False
    rolled: bool = False
    survived_scenario: bool | None = None
    dimensions: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnalyticsSnapshot:
    metrics: dict[str, float]
    rolling: dict[str, tuple[float, ...]]
    evidence: dict[str, Any]


class PortfolioAnalyticsEngine:
    """Computes period-aware portfolio metrics from deterministic observations."""

    def compute(
        self,
        observations: tuple[ResearchObservation, ...],
        *,
        periods_per_year: int = 252,
        rolling_window: int = 20,
        risk_free_rate: float = 0.0,
    ) -> AnalyticsSnapshot:
        returns = tuple(item.return_value for item in observations)
        pnl = tuple(item.pnl for item in observations)
        count = len(returns)
        annualized_return = _mean(returns) * periods_per_year
        total_growth = math.prod(1.0 + value for value in returns) if returns else 1.0
        cagr = total_growth ** (periods_per_year / count) - 1.0 if count else 0.0
        volatility = _sample_std(returns) * math.sqrt(periods_per_year)
        downside = math.sqrt(
            _mean(min(0.0, item - risk_free_rate / periods_per_year) ** 2 for item in returns)
        ) * math.sqrt(periods_per_year)
        excess = annualized_return - risk_free_rate
        sharpe = _ratio(excess, volatility)
        sortino = _ratio(excess, downside)
        equity = _equity(returns)
        drawdown = _max_drawdown(equity)
        winners, losers = [item for item in pnl if item > 0], [item for item in pnl if item < 0]
        avg_win, avg_loss = _mean(winners), _mean(losers)
        gain_loss = _ratio(sum(winners), abs(sum(losers)))
        expectancy = _mean(pnl)
        win_rate = _ratio(len(winners), count)
        loss_rate = _ratio(len(losers), count)
        payoff = _ratio(avg_win, abs(avg_loss))
        kelly = win_rate - _ratio(loss_rate, payoff) if payoff else 0.0
        benchmark = tuple(item.benchmark_return for item in observations)
        paired = tuple(
            (actual, base)
            for actual, base in zip(returns, benchmark, strict=True)
            if base is not None
        )
        beta = _beta(paired)
        benchmark_mean = _mean(base for _, base in paired)
        alpha = (
            annualized_return
            - (risk_free_rate + beta * (benchmark_mean * periods_per_year - risk_free_rate))
            if paired
            else 0.0
        )
        tracking_error = _sample_std(actual - base for actual, base in paired) * math.sqrt(
            periods_per_year
        )
        information_ratio = (
            _ratio((annualized_return - benchmark_mean * periods_per_year), tracking_error)
            if paired
            else 0.0
        )
        upside_capture = _ratio(
            _mean(actual for actual, base in paired if base > 0),
            _mean(base for _, base in paired if base > 0),
        )
        downside_capture = _ratio(
            _mean(actual for actual, base in paired if base < 0),
            _mean(base for _, base in paired if base < 0),
        )
        metrics = {
            "cagr": cagr,
            "annual_return": annualized_return,
            "monthly_return": annualized_return / 12,
            "sharpe": sharpe,
            "sortino": sortino,
            "calmar": _ratio(cagr, drawdown),
            "omega": _ratio(
                sum(max(0.0, item) for item in returns),
                abs(sum(min(0.0, item) for item in returns)),
            ),
            "information_ratio": information_ratio,
            "treynor": _ratio(excess, beta),
            "jensen_alpha": alpha,
            "beta": beta,
            "downside_deviation": downside,
            "upside_capture": upside_capture,
            "downside_capture": downside_capture,
            "recovery_factor": _ratio(sum(pnl), drawdown),
            "ulcer_index": _ulcer_index(equity),
            "mar_ratio": _ratio(cagr, drawdown),
            "gain_loss_ratio": gain_loss,
            "expectancy": expectancy,
            "kelly_fraction": kelly,
            "payoff_ratio": payoff,
            "average_win": avg_win,
            "average_loss": avg_loss,
            "largest_winner": max(winners, default=0.0),
            "largest_loser": min(losers, default=0.0),
            "average_holding_period": _mean(item.holding_period_days for item in observations),
            "turnover": _mean(item.turnover for item in observations),
            "capital_efficiency": _ratio(sum(pnl), sum(item.capital for item in observations)),
            "margin_efficiency": _ratio(sum(pnl), sum(item.margin for item in observations)),
            "assignment_frequency": _ratio(sum(item.assigned for item in observations), count),
            "roll_frequency": _ratio(sum(item.rolled for item in observations), count),
            "scenario_survival_score": _ratio(
                sum(item.survived_scenario is True for item in observations),
                sum(item.survived_scenario is not None for item in observations),
            ),
        }
        rolling = {
            "return": _rolling(returns, rolling_window, _mean),
            "sharpe": _rolling(
                returns,
                rolling_window,
                lambda x: _ratio(
                    _mean(x) * periods_per_year - risk_free_rate,
                    _sample_std(x) * math.sqrt(periods_per_year),
                ),
            ),
            "sortino": _rolling(
                returns,
                rolling_window,
                lambda x: _ratio(
                    _mean(x) * periods_per_year - risk_free_rate,
                    math.sqrt(_mean(min(0.0, value) ** 2 for value in x))
                    * math.sqrt(periods_per_year),
                ),
            ),
        }
        return AnalyticsSnapshot(
            metrics=metrics,
            rolling=rolling,
            evidence={
                "observation_count": count,
                "benchmark_observation_count": len(paired),
                "periods_per_year": periods_per_year,
            },
        )


class AttributionEngine:
    dimensions = (
        "underlying",
        "strategy",
        "strategy_family",
        "symbol",
        "expiration",
        "volatility_regime",
        "earnings_regime",
        "term_structure",
        "management_policy",
        "roll_policy",
        "execution_policy",
        "broker_policy",
        "scenario",
        "calendar_period",
    )

    def summarize(
        self, observations: tuple[ResearchObservation, ...]
    ) -> dict[str, dict[str, dict[str, float]]]:
        result: dict[str, dict[str, dict[str, float]]] = {}
        for dimension in self.dimensions:
            buckets: dict[str, list[ResearchObservation]] = defaultdict(list)
            for item in observations:
                if value := item.dimensions.get(dimension):
                    buckets[value].append(item)
            result[dimension] = {
                key: {
                    "pnl": sum(item.pnl for item in values),
                    "return": _mean(item.return_value for item in values),
                    "count": float(len(values)),
                }
                for key, values in sorted(buckets.items())
            }
        return result


@dataclass(frozen=True, slots=True)
class RobustnessReport:
    metrics: dict[str, float | None]
    evidence: dict[str, Any]


class RobustnessEngine:
    def evaluate(
        self,
        *,
        parameter_scores: tuple[float, ...] = (),
        cpcv_sharpes: tuple[float, ...] = (),
        walk_forward_scores: tuple[float, ...] = (),
        regime_scores: tuple[float, ...] = (),
        earnings_scores: tuple[float, ...] = (),
        liquidity_scores: tuple[float, ...] = (),
        stress_survival: tuple[bool, ...] = (),
        complexity: float | None = None,
    ) -> RobustnessReport:
        stability = (
            _ratio(_mean(parameter_scores), _mean(abs(score) for score in parameter_scores))
            if parameter_scores
            else None
        )
        pbo = (
            _ratio(sum(score <= 0 for score in cpcv_sharpes), len(cpcv_sharpes))
            if cpcv_sharpes
            else None
        )
        observed_sharpe = _mean(cpcv_sharpes)
        deflated = (
            observed_sharpe
            - math.sqrt(2 * math.log(max(1, len(cpcv_sharpes))))
            / math.sqrt(max(1, len(cpcv_sharpes)))
            if cpcv_sharpes
            else None
        )
        metrics = {
            "parameter_neighbourhood_stability": stability,
            "cpcv_summary": _mean(cpcv_sharpes) if cpcv_sharpes else None,
            "pbo": pbo,
            "deflated_sharpe": deflated,
            "walk_forward_summary": _mean(walk_forward_scores) if walk_forward_scores else None,
            "temporal_stability": _stability(walk_forward_scores),
            "volatility_regime_stability": _stability(regime_scores),
            "earnings_robustness": _mean(earnings_scores) if earnings_scores else None,
            "liquidity_robustness": _mean(liquidity_scores) if liquidity_scores else None,
            "stress_survivability": _ratio(sum(stress_survival), len(stress_survival))
            if stress_survival
            else None,
            "complexity_penalty": complexity,
            "overfitting_score": _mean(value for value in (pbo, complexity) if value is not None)
            if pbo is not None or complexity is not None
            else None,
        }
        present = [
            value for value in metrics.values() if value is not None and math.isfinite(value)
        ]
        metrics["confidence_score"] = _mean(present) if present else None
        return RobustnessReport(
            metrics=metrics,
            evidence={
                "missing_inputs": tuple(key for key, value in metrics.items() if value is None),
                "sample_sizes": {
                    "parameter": len(parameter_scores),
                    "cpcv": len(cpcv_sharpes),
                    "walk_forward": len(walk_forward_scores),
                },
            },
        )


@dataclass(frozen=True, slots=True)
class ResearchScore:
    score: float | None
    components: Mapping[str, float | None]
    missing_components: tuple[str, ...]
    explanation: tuple[str, ...]


class ResearchScoreEngine:
    weights = {
        "robustness": 0.15,
        "reproducibility": 0.1,
        "execution_realism": 0.1,
        "liquidity": 0.1,
        "scenario_survival": 0.1,
        "data_quality": 0.1,
        "statistical_confidence": 0.1,
        "optimization_stability": 0.1,
        "parameter_sensitivity": 0.15,
    }

    def score(self, components: dict[str, float | None]) -> ResearchScore:
        normalized = {key: components.get(key) for key in self.weights}
        missing = tuple(key for key, value in normalized.items() if value is None)
        if missing:
            return ResearchScore(
                None, normalized, missing, ("Score unavailable: required evidence is missing.",)
            )
        bounded: dict[str, float] = {
            key: min(1.0, max(0.0, cast(float, value))) for key, value in normalized.items()
        }
        return ResearchScore(
            sum(bounded[key] * self.weights[key] for key in self.weights),
            bounded,
            (),
            tuple(
                f"{key} contributed {bounded[key] * self.weights[key]:.3f}." for key in self.weights
            ),
        )


class PortfolioDiagnosticsEngine:
    def evaluate(self, observations: tuple[ResearchObservation, ...]) -> dict[str, float]:
        dimensions = {
            name: [item.dimensions.get(name, "") for item in observations]
            for name in (
                "symbol",
                "strategy",
                "expiration",
                "volatility_regime",
                "earnings_regime",
                "sector",
            )
        }
        concentration = {name: _hhi(values) for name, values in dimensions.items()}
        return {
            "hidden_concentration": max(concentration.values(), default=0.0),
            "duplicate_exposure": _duplicate_rate(
                tuple(
                    item.dimensions.get("symbol", "") + item.dimensions.get("strategy", "")
                    for item in observations
                )
            ),
            "directional_overlap": _hhi(
                tuple(item.dimensions.get("direction", "") for item in observations)
            ),
            "volatility_overlap": concentration["volatility_regime"],
            "theta_overlap": _hhi(
                tuple(item.dimensions.get("theta_bucket", "") for item in observations)
            ),
            "gamma_clustering": _hhi(
                tuple(item.dimensions.get("gamma_bucket", "") for item in observations)
            ),
            "assignment_clustering": _hhi(
                tuple(item.dimensions.get("assignment_bucket", "") for item in observations)
            ),
            "earnings_clustering": concentration["earnings_regime"],
            "liquidity_concentration": _hhi(
                tuple(item.dimensions.get("liquidity_bucket", "") for item in observations)
            ),
            "sector_concentration": concentration["sector"],
            "expiration_concentration": concentration["expiration"],
        }


class StrategyComparisonEngine:
    def compare(
        self, candidates: dict[str, dict[str, float]]
    ) -> dict[str, dict[str, dict[str, float]]]:
        keys = sorted({key for values in candidates.values() for key in values})
        return {
            left: {
                right: {
                    key: candidates[right].get(key, 0.0) - candidates[left].get(key, 0.0)
                    for key in keys
                }
                for right in candidates
                if right != left
            }
            for left in candidates
        }


def audit_decision(
    *,
    why: tuple[str, ...],
    alternatives: tuple[dict[str, Any], ...],
    confidence: float | None,
    assumptions: tuple[str, ...],
    supporting_data: dict[str, Any],
    rejected_alternatives: tuple[dict[str, Any], ...],
    uncertainty: tuple[str, ...],
) -> dict[str, Any]:
    """A complete audit shape; confidence must be supplied by measured evidence."""
    return {
        "why": why,
        "alternatives": alternatives,
        "confidence": confidence,
        "assumptions": assumptions,
        "supporting_data": supporting_data,
        "rejected_alternatives": rejected_alternatives,
        "uncertainty": uncertainty,
    }


def _equity(returns: tuple[float, ...]) -> tuple[float, ...]:
    result, value = [1.0], 1.0
    for item in returns:
        value *= 1 + item
        result.append(value)
    return tuple(result)


def _max_drawdown(equity: tuple[float, ...]) -> float:
    peak, result = 1.0, 0.0
    for value in equity:
        peak = max(peak, value)
        result = max(result, _ratio(peak - value, peak))
    return result


def _ulcer_index(equity: tuple[float, ...]) -> float:
    peak = 1.0
    squares: list[float] = []
    for value in equity:
        peak = max(peak, value)
        squares.append(_ratio(peak - value, peak) ** 2)
    return math.sqrt(_mean(squares))


def _beta(paired: tuple[tuple[float, float], ...]) -> float:
    if len(paired) < 2:
        return 0.0
    actual, benchmark = zip(*paired, strict=True)
    mean = _mean(benchmark)
    return _ratio(
        sum((a - _mean(actual)) * (b - mean) for a, b in paired),
        sum((b - mean) ** 2 for b in benchmark),
    )


def _rolling(values: tuple[float, ...], window: int, function: Any) -> tuple[float, ...]:
    return (
        tuple(function(values[index - window : index]) for index in range(window, len(values) + 1))
        if window > 0
        else ()
    )


def _stability(values: tuple[float, ...]) -> float | None:
    return _ratio(_mean(values), _mean(abs(value) for value in values)) if values else None


def _hhi(values: tuple[str, ...] | list[str]) -> float:
    values = tuple(value for value in values if value)
    return _ratio(sum(values.count(value) ** 2 for value in set(values)), len(values) ** 2)


def _duplicate_rate(values: tuple[str, ...]) -> float:
    return _ratio(len(values) - len(set(values)), len(values))
