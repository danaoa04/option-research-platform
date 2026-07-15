"""Research borrow availability and hard-to-borrow accrual support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .accounts import BorrowPolicy


@dataclass(slots=True, frozen=True)
class BorrowQuote:
    symbol: str
    effective_timestamp: datetime
    available: bool | None
    annualized_rate: float | None
    hard_to_borrow: bool
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class BorrowAccrual:
    accrual_id: str
    symbol: str
    accrual_timestamp: datetime
    share_quantity: int
    annualized_rate: float
    accrued_amount: float
    hard_to_borrow: bool
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class BorrowAssessment:
    symbol: str
    available: bool
    annualized_rate: float
    hard_to_borrow: bool
    locate_required: bool
    buy_in_risk: float
    recall_risk: float
    warnings: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BorrowEngine:
    def assess(
        self,
        *,
        symbol: str,
        policy: BorrowPolicy,
        quote: BorrowQuote | None,
    ) -> BorrowAssessment:
        warnings: list[str] = []
        if quote is None:
            if not policy.allow_conservative_fallback or policy.fallback_borrow_rate is None:
                return BorrowAssessment(
                    symbol=symbol,
                    available=False,
                    annualized_rate=0.0,
                    hard_to_borrow=True,
                    locate_required=policy.locate_required_placeholder,
                    buy_in_risk=policy.buy_in_risk_multiplier,
                    recall_risk=policy.recall_risk_multiplier,
                    warnings=("missing_borrow_data",),
                    metadata={},
                )
            warnings.append("missing_borrow_data")
            warnings.append("conservative_fallback_applied")
            return BorrowAssessment(
                symbol=symbol,
                available=False,
                annualized_rate=policy.fallback_borrow_rate,
                hard_to_borrow=True,
                locate_required=policy.locate_required_placeholder,
                buy_in_risk=policy.buy_in_risk_multiplier,
                recall_risk=policy.recall_risk_multiplier,
                warnings=tuple(warnings),
                metadata={"source": "fallback"},
            )

        if quote.available is False:
            warnings.append("borrow_unavailable")
        if quote.hard_to_borrow:
            warnings.append("hard_to_borrow")
        if quote.available is None or quote.annualized_rate is None:
            warnings.append("missing_borrow_data")
        if quote.annualized_rate is None:
            warnings.append("borrow_rate_missing")
        rate = quote.annualized_rate
        if rate is None:
            rate = policy.fallback_borrow_rate or 0.0
        return BorrowAssessment(
            symbol=symbol,
            available=bool(quote.available),
            annualized_rate=rate,
            hard_to_borrow=quote.hard_to_borrow,
            locate_required=policy.locate_required_placeholder,
            buy_in_risk=policy.buy_in_risk_multiplier * (2.0 if quote.hard_to_borrow else 1.0),
            recall_risk=policy.recall_risk_multiplier * (2.0 if quote.hard_to_borrow else 1.0),
            warnings=tuple(warnings),
            metadata={"source": quote.source},
        )

    def accrue(
        self,
        *,
        accrual_id: str,
        assessment: BorrowAssessment,
        share_quantity: int,
        market_price: float,
        start_timestamp: datetime,
        end_timestamp: datetime,
    ) -> BorrowAccrual:
        start_ts = _aware(start_timestamp)
        end_ts = _aware(end_timestamp)
        elapsed_days = max(0.0, (end_ts - start_ts).total_seconds() / 86400.0)
        basis = abs(share_quantity) * max(0.0, market_price)
        accrued = basis * assessment.annualized_rate * (elapsed_days / 365.0)
        return BorrowAccrual(
            accrual_id=accrual_id,
            symbol=assessment.symbol,
            accrual_timestamp=end_ts,
            share_quantity=share_quantity,
            annualized_rate=assessment.annualized_rate,
            accrued_amount=round(-accrued, 8),
            hard_to_borrow=assessment.hard_to_borrow,
            warnings=assessment.warnings,
            metadata={"elapsed_days": elapsed_days, **assessment.metadata},
        )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
