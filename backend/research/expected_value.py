"""Expected-value and distribution analytics for historical and model outcomes."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ExpectedValueResult:
    label: str
    expected_pnl: float
    median_pnl: float
    expected_return_on_capital: float
    average_winner: float
    average_loser: float
    payoff_variance: float
    downside_deviation: float
    expected_shortfall: float
    tail_loss_percentile_95: float
    tail_loss_percentile_99: float
    profit_factor: float
    payoff_skewness: float
    payoff_kurtosis: float


@dataclass(slots=True, frozen=True)
class ExpectedValueComparison:
    historical: ExpectedValueResult
    model_estimated: ExpectedValueResult


@dataclass(slots=True)
class ExpectedValueEngine:
    def compare(
        self,
        *,
        historical_pnls: list[float],
        model_pnls: list[float],
        capital_base: float,
    ) -> ExpectedValueComparison:
        return ExpectedValueComparison(
            historical=self._summarize(
                "historical_expected_value",
                historical_pnls,
                capital_base,
            ),
            model_estimated=self._summarize(
                "model_estimated_expected_value",
                model_pnls,
                capital_base,
            ),
        )

    def _summarize(self, label: str, pnls: list[float], capital_base: float) -> ExpectedValueResult:
        if not pnls:
            raise ValueError("pnl series cannot be empty")
        sorted_values = sorted(pnls)
        mean = sum(pnls) / len(pnls)
        median = _median(sorted_values)
        variance = _variance(pnls)
        winners = [value for value in pnls if value > 0.0]
        losers = [value for value in pnls if value < 0.0]

        downside = math.sqrt(
            sum((min(value, 0.0) - 0.0) ** 2 for value in pnls) / max(len(pnls) - 1, 1)
        )
        expected_shortfall = _expected_shortfall(sorted_values, alpha=0.95)
        tail_95 = _percentile(sorted_values, 0.05)
        tail_99 = _percentile(sorted_values, 0.01)
        loss_abs = abs(sum(losers))
        profit_factor = (sum(winners) / loss_abs) if loss_abs > 0.0 else float("inf")

        stdev = math.sqrt(max(variance, 1e-12))
        skew = sum(((value - mean) / stdev) ** 3 for value in pnls) / len(pnls)
        kurt = sum(((value - mean) / stdev) ** 4 for value in pnls) / len(pnls)

        return ExpectedValueResult(
            label=label,
            expected_pnl=mean,
            median_pnl=median,
            expected_return_on_capital=mean / max(capital_base, 1e-12),
            average_winner=(sum(winners) / len(winners)) if winners else 0.0,
            average_loser=(sum(losers) / len(losers)) if losers else 0.0,
            payoff_variance=variance,
            downside_deviation=downside,
            expected_shortfall=expected_shortfall,
            tail_loss_percentile_95=tail_95,
            tail_loss_percentile_99=tail_99,
            profit_factor=profit_factor,
            payoff_skewness=skew,
            payoff_kurtosis=kurt,
        )


def _median(values: list[float]) -> float:
    n = len(values)
    mid = n // 2
    if n % 2 == 0:
        return (values[mid - 1] + values[mid]) / 2.0
    return values[mid]


def _variance(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / (len(values) - 1)


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    p = max(0.0, min(1.0, p))
    idx = int(round((len(sorted_values) - 1) * p))
    return sorted_values[idx]


def _expected_shortfall(sorted_values: list[float], alpha: float) -> float:
    if not sorted_values:
        return 0.0
    cutoff = max(1, int(len(sorted_values) * (1.0 - alpha)))
    tail = sorted_values[:cutoff]
    return sum(tail) / len(tail)
