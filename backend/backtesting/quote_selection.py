"""Deterministic historical quote selection policies for execution research."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any


class QuotePriceSelection(StrEnum):
    BID = "bid"
    ASK = "ask"
    MIDPOINT = "midpoint"
    LAST = "last"
    THROUGH_SPREAD = "through_spread"


@dataclass(slots=True, frozen=True)
class QuoteSelectionPolicy:
    mode: str
    price_selection: QuotePriceSelection
    through_spread_pct: float = 0.5
    theoretical_fallback_enabled: bool = False


@dataclass(slots=True, frozen=True)
class QuoteSelectionResult:
    selected_quote: dict[str, Any] | None
    selected_price: float | None
    quote_age_seconds: float | None
    spread_width: float | None
    quality_flags: tuple[str, ...]
    stale_data: bool
    crossed_market: bool
    source_manifest: str | None
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QuoteSelector:
    stale_quote_seconds: float = 120.0

    def select(
        self,
        *,
        request_timestamp: datetime,
        quotes: tuple[dict[str, Any], ...],
        policy: QuoteSelectionPolicy,
        delay_seconds: float,
    ) -> QuoteSelectionResult:
        ts = _aware(request_timestamp)
        delayed_ts = ts + timedelta(seconds=max(0.0, delay_seconds))
        ordered = sorted(quotes, key=lambda row: _aware(_ts(row)))

        selected: dict[str, Any] | None = None
        if policy.mode == "exact":
            selected = next((row for row in ordered if _aware(_ts(row)) == ts), None)
        elif policy.mode == "next_after_delay":
            selected = next((row for row in ordered if _aware(_ts(row)) >= delayed_ts), None)
        else:
            # Default nearest-prior semantics preserve no-look-ahead.
            for row in ordered:
                row_ts = _aware(_ts(row))
                if row_ts <= ts:
                    selected = row
                else:
                    break

        if selected is None and policy.theoretical_fallback_enabled:
            selected = {
                "timestamp": delayed_ts,
                "bid": None,
                "ask": None,
                "last": None,
                "theoretical": 0.0,
                "manifest": "theoretical_fallback",
                "quality_flags": ["theoretical_fallback"],
            }

        if selected is None:
            return QuoteSelectionResult(
                selected_quote=None,
                selected_price=None,
                quote_age_seconds=None,
                spread_width=None,
                quality_flags=("missing_quote",),
                stale_data=True,
                crossed_market=False,
                source_manifest=None,
                diagnostics={"policy_mode": policy.mode},
            )

        bid = _as_float(selected.get("bid"))
        ask = _as_float(selected.get("ask"))
        last = _as_float(selected.get("last"))
        spread = None if bid is None or ask is None else max(0.0, ask - bid)
        crossed = bool(bid is not None and ask is not None and bid > ask)
        age = max(0.0, (ts - _aware(_ts(selected))).total_seconds())
        stale = age > self.stale_quote_seconds
        selected_price = _price(policy=policy, bid=bid, ask=ask, last=last, row=selected)
        qflags = tuple(str(item) for item in selected.get("quality_flags", []))
        flags = list(qflags)
        if stale:
            flags.append("stale_quote")
        if crossed:
            flags.append("crossed_market")

        return QuoteSelectionResult(
            selected_quote=selected,
            selected_price=selected_price,
            quote_age_seconds=age,
            spread_width=spread,
            quality_flags=tuple(flags),
            stale_data=stale,
            crossed_market=crossed,
            source_manifest=selected.get("manifest"),
            diagnostics={
                "policy_mode": policy.mode,
                "delay_seconds": max(0.0, delay_seconds),
                "selected_timestamp": _aware(_ts(selected)).isoformat(),
            },
        )


def _price(
    *,
    policy: QuoteSelectionPolicy,
    bid: float | None,
    ask: float | None,
    last: float | None,
    row: dict[str, Any],
) -> float | None:
    if policy.price_selection is QuotePriceSelection.BID:
        return bid
    if policy.price_selection is QuotePriceSelection.ASK:
        return ask
    if policy.price_selection is QuotePriceSelection.LAST:
        return last
    if policy.price_selection is QuotePriceSelection.MIDPOINT:
        if bid is None or ask is None:
            return None
        return (bid + ask) / 2.0
    if policy.price_selection is QuotePriceSelection.THROUGH_SPREAD:
        if bid is None or ask is None:
            return None
        return bid + max(0.0, min(1.0, policy.through_spread_pct)) * (ask - bid)
    return _as_float(row.get("theoretical"))


def _ts(row: dict[str, Any]) -> datetime:
    value = row.get("timestamp")
    if isinstance(value, datetime):
        return value
    return datetime(1970, 1, 1, tzinfo=UTC)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
