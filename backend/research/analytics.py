"""Deterministic historical analytics for multi-expiry strategy studies."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models import HistoricalAnalyticsResult, StrategyStatePoint


@dataclass(slots=True)
class HistoricalAnalyticsEngine:
    risk_free_rate: float = 0.0

    def summarize(
        self,
        *,
        returns: list[float],
        states: list[StrategyStatePoint],
    ) -> HistoricalAnalyticsResult:
        if not returns:
            raise ValueError("returns must not be empty")

        winners = [value for value in returns if value > 0.0]
        losers = [value for value in returns if value < 0.0]

        expected_value = _mean(returns)
        std_dev = _stddev(returns)
        downside = _stddev([min(item, 0.0) for item in returns])

        sharpe = 0.0 if std_dev == 0.0 else (expected_value - self.risk_free_rate) / std_dev
        sortino = 0.0 if downside == 0.0 else (expected_value - self.risk_free_rate) / downside

        equity_curve = _equity_curve(returns)
        max_drawdown = _max_drawdown(equity_curve)

        theta_capture = sum(point.theta for point in states)
        vega_exposure = _mean([abs(point.vega) for point in states]) if states else 0.0
        gamma_exposure = _mean([abs(point.gamma) for point in states]) if states else 0.0

        return HistoricalAnalyticsResult(
            historical_pop=len(winners) / len(returns),
            average_winner=_mean(winners) if winners else 0.0,
            average_loser=_mean(losers) if losers else 0.0,
            expected_value=expected_value,
            median_return=_median(returns),
            standard_deviation=std_dev,
            sharpe=sharpe,
            sortino=sortino,
            max_drawdown=max_drawdown,
            win_streak=_max_streak(returns, positive=True),
            loss_streak=_max_streak(returns, positive=False),
            theta_capture=theta_capture,
            vega_exposure=vega_exposure,
            gamma_exposure=gamma_exposure,
        )


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    size = len(ordered)
    middle = size // 2
    if size % 2 == 0:
        return (ordered[middle - 1] + ordered[middle]) / 2.0
    return ordered[middle]


def _stddev(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    avg = _mean(values)
    variance = sum((item - avg) ** 2 for item in values) / (len(values) - 1)
    return math.sqrt(max(variance, 0.0))


def _equity_curve(returns: list[float]) -> list[float]:
    equity = [0.0]
    running = 0.0
    for item in returns:
        running += item
        equity.append(running)
    return equity


def _max_drawdown(curve: list[float]) -> float:
    peak = curve[0]
    max_drop = 0.0
    for value in curve:
        peak = max(peak, value)
        max_drop = min(max_drop, value - peak)
    return abs(max_drop)


def _max_streak(values: list[float], *, positive: bool) -> int:
    best = 0
    run = 0
    for item in values:
        is_hit = item > 0.0 if positive else item < 0.0
        if is_hit:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best
