"""Baseline deterministic research fill model for offline backtesting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .exceptions import FillModelError
from .models import (
    FillDiagnostics,
    FillPricePolicy,
    FillResult,
    OrderIntent,
    OrderSide,
    QuoteSnapshot,
)


@dataclass(slots=True, frozen=True)
class FillModelConfig:
    stale_quote_seconds: float = 120.0
    fixed_slippage: float = 0.0
    percent_through_spread: float = 0.5
    delay_to_next_quote: bool = False
    reject_crossed_market: bool = True
    reject_missing_quote: bool = True


@dataclass(slots=True)
class BaselineResearchFillModel:
    config: FillModelConfig

    def fill(
        self,
        *,
        intent: OrderIntent,
        quote: QuoteSnapshot | None,
        next_quote: QuoteSnapshot | None = None,
    ) -> FillResult:
        if quote is None:
            if self.config.reject_missing_quote:
                return self._reject(intent, "missing_quote")
            raise FillModelError(
                "fill model requires quote when missing quote rejection is disabled"
            )

        as_of = _ensure_aware(intent.requested_timestamp)
        quote_ts = _ensure_aware(quote.timestamp)
        stale_age = max(0.0, (as_of - quote_ts).total_seconds())
        if stale_age > self.config.stale_quote_seconds:
            return self._reject(intent, "stale_quote", stale_age_seconds=stale_age)

        if self.config.reject_crossed_market and _is_crossed(quote):
            return self._reject(intent, "crossed_market", stale_age_seconds=stale_age)

        source_quote = (
            next_quote if self.config.delay_to_next_quote and next_quote is not None else quote
        )
        price = self._price_from_policy(intent=intent, quote=source_quote)
        if price is None:
            return self._reject(intent, "price_unavailable", stale_age_seconds=stale_age)

        signed_slippage = (
            self.config.fixed_slippage
            if intent.side is OrderSide.BUY
            else -self.config.fixed_slippage
        )
        fill_price = max(0.0, price + signed_slippage)

        return FillResult(
            intent_id=intent.intent_id,
            filled=True,
            fill_timestamp=_ensure_aware(source_quote.timestamp),
            fill_price=fill_price,
            diagnostics=FillDiagnostics(
                status="filled",
                reason_code="filled",
                stale_age_seconds=stale_age,
                spread_width=_spread(source_quote),
                used_policy=intent.price_policy,
                metadata={
                    "fixed_slippage": self.config.fixed_slippage,
                    "delay_to_next_quote": self.config.delay_to_next_quote,
                },
            ),
        )

    def _price_from_policy(self, *, intent: OrderIntent, quote: QuoteSnapshot) -> float | None:
        if intent.price_policy is FillPricePolicy.BID:
            return quote.bid
        if intent.price_policy is FillPricePolicy.ASK:
            return quote.ask
        if intent.price_policy is FillPricePolicy.LAST:
            return quote.last
        if intent.price_policy is FillPricePolicy.MIDPOINT:
            if quote.bid is None or quote.ask is None:
                return None
            return (quote.bid + quote.ask) / 2.0

        if intent.price_policy is FillPricePolicy.THROUGH_SPREAD:
            if quote.bid is None or quote.ask is None:
                return None
            spread = quote.ask - quote.bid
            if intent.side is OrderSide.BUY:
                return quote.bid + spread * self.config.percent_through_spread
            return quote.ask - spread * self.config.percent_through_spread

        return None

    def _reject(
        self,
        intent: OrderIntent,
        reason_code: str,
        *,
        stale_age_seconds: float | None = None,
    ) -> FillResult:
        return FillResult(
            intent_id=intent.intent_id,
            filled=False,
            fill_timestamp=None,
            fill_price=None,
            diagnostics=FillDiagnostics(
                status="rejected",
                reason_code=reason_code,
                stale_age_seconds=stale_age_seconds,
                spread_width=None,
                used_policy=intent.price_policy,
                metadata={},
            ),
        )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _is_crossed(quote: QuoteSnapshot) -> bool:
    if quote.bid is None or quote.ask is None:
        return False
    return quote.bid > quote.ask


def _spread(quote: QuoteSnapshot) -> float | None:
    if quote.bid is None or quote.ask is None:
        return None
    return max(0.0, quote.ask - quote.bid)
