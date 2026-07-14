"""Strongly typed data models for provider-neutral option pricing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


class ExerciseStyle(StrEnum):
    EUROPEAN = "european"
    AMERICAN = "american"


class PricingModelName(StrEnum):
    BLACK_SCHOLES = "black_scholes"
    BLACK_76 = "black_76"
    BINOMIAL_TREE = "binomial_tree"
    COX_ROSS_RUBINSTEIN = "cox_ross_rubinstein"
    BARONE_ADESI_WHALEY = "barone_adesi_whaley"
    BJERKSUND_STENSLAND = "bjerksund_stensland"


@dataclass(slots=True, frozen=True)
class PricingRequest:
    spot: float
    strike: float
    expiry: date
    volatility: float
    risk_free_rate: float
    dividend_yield: float
    option_type: OptionType
    exercise_style: ExerciseStyle
    multiplier: float
    valuation_date: date


@dataclass(slots=True, frozen=True)
class PricingResult:
    option_value: float
    intrinsic_value: float
    extrinsic_value: float
    time_to_expiry: float
    calculation_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
