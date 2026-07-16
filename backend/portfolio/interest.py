"""Deterministic interest accrual for positive cash and margin debits."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .accounts import AccountConfiguration, DayCountConvention, InterestPolicy, InterestRateMode


@dataclass(slots=True, frozen=True)
class InterestRatePoint:
    effective_timestamp: datetime
    annual_rate: float
    source_curve: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class InterestAccrual:
    accrual_id: str
    accrual_timestamp: datetime
    balance_basis: float
    annual_rate: float
    accrued_amount: float
    is_debit: bool
    source_curve: str
    assumptions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InterestAccrualEngine:
    def accrue(
        self,
        *,
        accrual_id: str,
        policy: InterestPolicy,
        configuration: AccountConfiguration,
        balance: float,
        start_timestamp: datetime,
        end_timestamp: datetime,
        benchmark_rates: tuple[InterestRatePoint, ...] = (),
    ) -> InterestAccrual:
        start_ts = _aware(start_timestamp)
        end_ts = _aware(end_timestamp)
        elapsed_days = max(0.0, (end_ts - start_ts).total_seconds() / 86400.0)
        divisor = 365.0 if policy.day_count_convention is DayCountConvention.CALENDAR else 252.0
        annual_rate, source_curve = self._rate(policy, balance, benchmark_rates)
        debit = balance < 0
        basis = abs(balance)
        raw = basis * annual_rate * (elapsed_days / divisor)
        accrued = (
            raw
            if not policy.daily_compounding
            else basis * ((1.0 + annual_rate / divisor) ** elapsed_days - 1.0)
        )
        signed = -accrued if debit else accrued
        return InterestAccrual(
            accrual_id=accrual_id,
            accrual_timestamp=end_ts,
            balance_basis=round(balance, 8),
            annual_rate=round(annual_rate, 10),
            accrued_amount=round(signed, 8),
            is_debit=debit,
            source_curve=source_curve,
            assumptions={
                "account_id": configuration.account_id,
                "day_count_convention": policy.day_count_convention.value,
                "elapsed_days": elapsed_days,
                "daily_compounding": policy.daily_compounding,
            },
        )

    def _rate(
        self,
        policy: InterestPolicy,
        balance: float,
        benchmark_rates: tuple[InterestRatePoint, ...],
    ) -> tuple[float, str]:
        if policy.mode is InterestRateMode.FIXED:
            return (
                policy.margin_debit_rate if balance < 0 else policy.positive_cash_rate,
                "fixed_policy",
            )
        if policy.mode is InterestRateMode.TIERED and policy.tiered_rates:
            basis = abs(balance)
            selected = policy.tiered_rates[-1][1]
            for threshold, rate in sorted(policy.tiered_rates, key=lambda item: item[0]):
                if basis <= threshold:
                    selected = rate
                    break
            return (selected, "tiered_policy")
        latest = max(benchmark_rates, key=lambda item: item.effective_timestamp, default=None)
        if latest is None:
            return (
                policy.margin_debit_rate if balance < 0 else policy.positive_cash_rate,
                policy.benchmark_name or "benchmark_missing_fallback",
            )
        base = latest.annual_rate + policy.benchmark_spread
        if balance < 0 and policy.margin_debit_rate > 0:
            base = max(base, policy.margin_debit_rate)
        if balance >= 0 and policy.positive_cash_rate > 0:
            base = max(base, policy.positive_cash_rate)
        return (base, latest.source_curve)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
