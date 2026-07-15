"""Backtest analytics services and typed result models for Sprint 6C."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from statistics import mean
from typing import Any

from .guards import NoLookAheadGuard


@dataclass(slots=True, frozen=True)
class StrategyAnalyticsPoint:
    timestamp: datetime
    strategy_instance_id: str
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    return_value: float
    capital_usage: float
    cash_usage: float
    intrinsic_value: float
    extrinsic_value: float
    greeks: dict[str, float]
    implied_volatility: float | None
    realized_volatility: float | None
    iv_rank: float | None
    iv_percentile: float | None
    front_iv: float | None
    back_iv: float | None
    term_structure_slope: float | None
    term_structure_regime: str | None
    liquidity: float | None
    quote_quality: float | None
    lifecycle_state: str
    drawdown: float
    exposure: dict[str, float] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class PortfolioAnalyticsPoint:
    timestamp: datetime
    equity: float
    cash: float
    reserved_capital: float
    capital_utilization: float
    realized_pnl: float
    unrealized_pnl: float
    greeks: dict[str, float]
    sector_exposure: dict[str, float] = field(default_factory=dict)
    symbol_exposure: dict[str, float] = field(default_factory=dict)
    expiration_exposure: dict[str, float] = field(default_factory=dict)
    strategy_family_exposure: dict[str, float] = field(default_factory=dict)
    volatility_regime_exposure: dict[str, float] = field(default_factory=dict)
    term_structure_exposure: dict[str, float] = field(default_factory=dict)
    expected_shortfall: float = 0.0
    drawdown: float = 0.0
    concentration: float = 0.0
    liquidity_risk: float = 0.0
    risk_limit_status: str = "ok"


@dataclass(slots=True, frozen=True)
class PnLAttribution:
    timestamp: datetime
    strategy_instance_id: str
    underlying_move: float
    delta: float
    gamma: float
    theta: float
    vega: float
    volatility_surface: float
    term_structure: float
    skew: float
    rates: float
    dividend: float
    execution_cost: float
    slippage: float
    commissions: float
    corporate_actions: float
    residual: float
    approximation: bool = True


@dataclass(slots=True, frozen=True)
class GreeksAttribution:
    timestamp: datetime
    strategy_instance_id: str
    greek_changes: dict[str, float]
    attributable_to: dict[str, float]


@dataclass(slots=True, frozen=True)
class DrawdownPoint:
    timestamp: datetime
    equity: float
    running_peak: float
    drawdown: float


@dataclass(slots=True, frozen=True)
class ComparisonResult:
    key: str
    left_run_id: str
    right_run_id: str
    table_rows: tuple[dict[str, Any], ...]
    chart_payload: dict[str, Any]


@dataclass(slots=True, frozen=True)
class PerformanceAnalytics:
    total_return: float
    cagr: float
    annualized_volatility: float
    sharpe: float
    sortino: float
    calmar: float
    maximum_drawdown: float
    expected_shortfall: float
    downside_deviation: float
    profit_factor: float
    win_rate: float
    average_winner: float
    average_loser: float
    payoff_ratio: float
    expectancy: float
    capital_utilization: float


@dataclass(slots=True)
class BacktestAnalyticsService:
    guard: NoLookAheadGuard

    def strategy_equity_curve(
        self,
        *,
        points: tuple[StrategyAnalyticsPoint, ...],
        strategy_instance_id: str,
    ) -> tuple[tuple[datetime, float], ...]:
        rows = [
            item for item in points if item.strategy_instance_id == strategy_instance_id
        ]
        return tuple(
            (item.timestamp, item.total_pnl)
            for item in sorted(rows, key=lambda row: row.timestamp)
        )

    def portfolio_equity_curve(
        self,
        *,
        points: tuple[PortfolioAnalyticsPoint, ...],
    ) -> tuple[tuple[datetime, float], ...]:
        return tuple(
            (item.timestamp, item.equity)
            for item in sorted(points, key=lambda row: row.timestamp)
        )

    def lifecycle_state_history(
        self,
        *,
        points: tuple[StrategyAnalyticsPoint, ...],
        strategy_instance_id: str,
    ) -> tuple[dict[str, Any], ...]:
        rows = [
            item for item in points if item.strategy_instance_id == strategy_instance_id
        ]
        return tuple(
            {
                "timestamp": item.timestamp,
                "lifecycle_state": item.lifecycle_state,
                "warnings": item.warnings,
                "failures": item.failures,
            }
            for item in sorted(rows, key=lambda row: row.timestamp)
        )

    def greeks_history(
        self,
        *,
        points: tuple[StrategyAnalyticsPoint, ...],
        strategy_instance_id: str,
    ) -> tuple[dict[str, Any], ...]:
        rows = [
            item for item in points if item.strategy_instance_id == strategy_instance_id
        ]
        return tuple(
            {
                "timestamp": item.timestamp,
                "greeks": dict(item.greeks),
            }
            for item in sorted(rows, key=lambda row: row.timestamp)
        )

    def iv_history(
        self,
        *,
        points: tuple[StrategyAnalyticsPoint, ...],
        strategy_instance_id: str,
    ) -> tuple[dict[str, Any], ...]:
        rows = [
            item for item in points if item.strategy_instance_id == strategy_instance_id
        ]
        return tuple(
            {
                "timestamp": item.timestamp,
                "implied_volatility": item.implied_volatility,
                "realized_volatility": item.realized_volatility,
                "iv_rank": item.iv_rank,
                "iv_percentile": item.iv_percentile,
                "front_iv": item.front_iv,
                "back_iv": item.back_iv,
            }
            for item in sorted(rows, key=lambda row: row.timestamp)
        )

    def term_structure_history(
        self,
        *,
        points: tuple[StrategyAnalyticsPoint, ...],
        strategy_instance_id: str,
    ) -> tuple[dict[str, Any], ...]:
        rows = [
            item for item in points if item.strategy_instance_id == strategy_instance_id
        ]
        return tuple(
            {
                "timestamp": item.timestamp,
                "term_structure_slope": item.term_structure_slope,
                "regime": item.term_structure_regime,
            }
            for item in sorted(rows, key=lambda row: row.timestamp)
        )

    def drawdown_history(
        self,
        *,
        equity_curve: tuple[tuple[datetime, float], ...],
    ) -> tuple[DrawdownPoint, ...]:
        running_peak = float("-inf")
        output: list[DrawdownPoint] = []
        for timestamp, equity in equity_curve:
            running_peak = max(running_peak, equity)
            drawdown = 0.0 if running_peak <= 0 else (running_peak - equity) / running_peak
            output.append(
                DrawdownPoint(
                    timestamp=timestamp,
                    equity=equity,
                    running_peak=running_peak,
                    drawdown=drawdown,
                )
            )
        return tuple(output)

    def compare_strategy_runs(
        self,
        *,
        left_run_id: str,
        right_run_id: str,
        left_curve: tuple[tuple[datetime, float], ...],
        right_curve: tuple[tuple[datetime, float], ...],
        key: str = "equity_curve",
    ) -> ComparisonResult:
        right_by_ts = {ts: value for ts, value in right_curve}
        rows: list[dict[str, Any]] = []
        for timestamp, left_value in left_curve:
            if timestamp not in right_by_ts:
                continue
            right_value = right_by_ts[timestamp]
            rows.append(
                {
                    "timestamp": timestamp,
                    "left": left_value,
                    "right": right_value,
                    "delta": left_value - right_value,
                }
            )
        return ComparisonResult(
            key=key,
            left_run_id=left_run_id,
            right_run_id=right_run_id,
            table_rows=tuple(rows),
            chart_payload={
                "series": {
                    "left": [{"x": row["timestamp"], "y": row["left"]} for row in rows],
                    "right": [{"x": row["timestamp"], "y": row["right"]} for row in rows],
                }
            },
        )

    def performance_analytics(
        self,
        *,
        equity_curve: tuple[tuple[datetime, float], ...],
        returns: tuple[float, ...],
        capital_utilization: float,
    ) -> PerformanceAnalytics:
        if not equity_curve:
            return PerformanceAnalytics(
                total_return=0.0,
                cagr=0.0,
                annualized_volatility=0.0,
                sharpe=0.0,
                sortino=0.0,
                calmar=0.0,
                maximum_drawdown=0.0,
                expected_shortfall=0.0,
                downside_deviation=0.0,
                profit_factor=0.0,
                win_rate=0.0,
                average_winner=0.0,
                average_loser=0.0,
                payoff_ratio=0.0,
                expectancy=0.0,
                capital_utilization=capital_utilization,
            )

        first_equity = equity_curve[0][1]
        last_equity = equity_curve[-1][1]
        total_return = 0.0 if first_equity == 0 else (last_equity - first_equity) / first_equity
        drawdowns = [item.drawdown for item in self.drawdown_history(equity_curve=equity_curve)]
        max_drawdown = max(drawdowns) if drawdowns else 0.0
        winners = [item for item in returns if item > 0]
        losers = [item for item in returns if item < 0]
        avg_winner = mean(winners) if winners else 0.0
        avg_loser = mean(losers) if losers else 0.0
        downside = [item for item in returns if item < 0]
        downside_deviation = (mean([item * item for item in downside]) ** 0.5) if downside else 0.0
        volatility = (mean([item * item for item in returns]) ** 0.5) if returns else 0.0
        sharpe = 0.0 if volatility == 0 else (mean(returns) / volatility)
        sortino = 0.0 if downside_deviation == 0 else (mean(returns) / downside_deviation)
        calmar = 0.0 if max_drawdown == 0 else total_return / max_drawdown
        profit_factor = (
            0.0
            if not losers
            else abs(sum(winners) / min(-1e-9, sum(losers)))
        )
        win_rate = (len(winners) / len(returns)) if returns else 0.0
        payoff_ratio = 0.0 if avg_loser == 0 else abs(avg_winner / avg_loser)
        expectancy = mean(returns) if returns else 0.0
        expected_shortfall = mean(sorted(returns)[: max(1, len(returns) // 20)]) if returns else 0.0

        return PerformanceAnalytics(
            total_return=total_return,
            cagr=total_return,
            annualized_volatility=volatility,
            sharpe=sharpe,
            sortino=sortino,
            calmar=calmar,
            maximum_drawdown=max_drawdown,
            expected_shortfall=expected_shortfall,
            downside_deviation=downside_deviation,
            profit_factor=profit_factor,
            win_rate=win_rate,
            average_winner=avg_winner,
            average_loser=avg_loser,
            payoff_ratio=payoff_ratio,
            expectancy=expectancy,
            capital_utilization=capital_utilization,
        )

    def as_of(
        self,
        *,
        as_of: datetime,
        rows: tuple[dict[str, Any], ...],
        timestamp_key: str,
    ) -> dict[str, Any] | None:
        as_of_ts = _ensure_aware(as_of)
        selected: dict[str, Any] | None = None
        selected_ts: datetime | None = None
        for row in rows:
            row_ts = _ensure_aware(row.get(timestamp_key))
            if row_ts > as_of_ts:
                continue
            if selected_ts is None or row_ts >= selected_ts:
                selected = row
                selected_ts = row_ts
        if selected_ts is not None:
            self.guard.assert_visible(as_of=as_of_ts, record_timestamp=selected_ts)
        return selected


def _ensure_aware(value: datetime | None) -> datetime:
    if value is None:
        return datetime(1970, 1, 1, tzinfo=UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
