"""Position and portfolio valuation services for historical backtesting."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from .exceptions import ValuationError
from .models import (
    MarkPricePolicy,
    PortfolioSnapshot,
    PositionLegState,
    PositionState,
    QuoteSnapshot,
)


@dataclass(slots=True, frozen=True)
class LegValuation:
    leg_id: str
    contract_identifier: str
    mark_price: float
    market_source: str
    diagnostics: dict[str, float | str]


@dataclass(slots=True)
class ValuationService:
    mark_policy: MarkPricePolicy
    stale_quote_seconds: float = 300.0

    def value_leg(
        self,
        *,
        as_of: datetime,
        leg: PositionLegState,
        quote: QuoteSnapshot | None,
        theoretical_fallback: Callable[[PositionLegState, datetime], float] | None = None,
    ) -> LegValuation:
        as_of_ts = _ensure_aware(as_of)
        if quote is not None:
            quote_ts = _ensure_aware(quote.timestamp)
            stale = max(0.0, (as_of_ts - quote_ts).total_seconds())
            if stale <= self.stale_quote_seconds:
                market_price = _from_policy(self.mark_policy, quote)
                if market_price is not None:
                    return LegValuation(
                        leg_id=leg.leg_id,
                        contract_identifier=leg.contract_identifier,
                        mark_price=market_price,
                        market_source="historical_quote",
                        diagnostics={"stale_age_seconds": stale, "policy": self.mark_policy.value},
                    )

        if (
            self.mark_policy is MarkPricePolicy.THEORETICAL_FALLBACK
            and theoretical_fallback is not None
        ):
            value = theoretical_fallback(leg, as_of_ts)
            return LegValuation(
                leg_id=leg.leg_id,
                contract_identifier=leg.contract_identifier,
                mark_price=value,
                market_source="theoretical_fallback",
                diagnostics={"policy": self.mark_policy.value},
            )

        raise ValuationError(
            "cannot value leg with configured policy and available historical quote context"
        )

    def value_portfolio(
        self,
        *,
        as_of: datetime,
        open_positions: tuple[PositionState, ...],
        marks: dict[str, float],
        cash_balance: float,
        reserved_capital: float,
        realized_pnl: float,
        accrued_fees: float,
        dividends: float,
        portfolio_greeks: dict[str, float],
        exposure: dict[str, float],
    ) -> PortfolioSnapshot:
        unrealized = 0.0
        for position in open_positions:
            for leg in position.legs:
                mark = marks.get(leg.contract_identifier, leg.current_price or 0.0)
                entry = leg.entry_price or 0.0
                unrealized += (mark - entry) * leg.quantity

        denominator = max(1e-9, cash_balance + reserved_capital)
        capital_utilization = reserved_capital / denominator
        return PortfolioSnapshot(
            timestamp=_ensure_aware(as_of),
            cash_balance=cash_balance,
            reserved_capital=reserved_capital,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized,
            accrued_fees=accrued_fees,
            dividends=dividends,
            portfolio_greeks=portfolio_greeks,
            portfolio_exposure=exposure,
            capital_utilization=capital_utilization,
        )


def _from_policy(policy: MarkPricePolicy, quote: QuoteSnapshot) -> float | None:
    if policy is MarkPricePolicy.BID:
        return quote.bid
    if policy is MarkPricePolicy.ASK:
        return quote.ask
    if policy is MarkPricePolicy.LAST:
        return quote.last
    if quote.bid is not None and quote.ask is not None:
        return (quote.bid + quote.ask) / 2.0
    return None


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
