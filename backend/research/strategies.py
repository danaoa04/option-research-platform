"""Strategy framework utilities for multi-expiration research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import DEFAULT_DTE_BUCKETS, MultiExpiryStrategy, StrategyLeg, StrategyType


@dataclass(slots=True)
class StrategyFactory:
    """Build typed multi-leg strategy definitions for research workflows."""

    def build(
        self,
        *,
        strategy_type: StrategyType,
        symbol: str,
        legs: list[StrategyLeg],
        entry_date: date,
        exit_date: date,
        metadata: dict[str, object] | None = None,
    ) -> MultiExpiryStrategy:
        if not legs:
            raise ValueError("strategy requires at least one leg")
        if exit_date <= entry_date:
            raise ValueError("exit_date must be after entry_date")

        expiries = {leg.expiration for leg in legs}
        if len(expiries) < 2 and strategy_type != StrategyType.MULTI_EXPIRY_CUSTOM:
            raise ValueError("strategy requires multiple expirations")

        return MultiExpiryStrategy(
            strategy_type=strategy_type,
            symbol=symbol,
            legs=tuple(legs),
            entry_date=entry_date,
            exit_date=exit_date,
            metadata=dict(metadata or {}),
        )


def normalize_dte_targets(targets: tuple[int, ...] | None = None) -> tuple[int, ...]:
    values = targets or DEFAULT_DTE_BUCKETS
    clean = sorted({item for item in values if item > 0})
    if not clean:
        raise ValueError("at least one DTE target is required")
    return tuple(clean)
