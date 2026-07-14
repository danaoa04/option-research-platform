"""Typed models for implied-volatility solving and interpolation workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from backend.pricing.models import PricingModelName, PricingRequest


class SolverMethod(StrEnum):
    NEWTON_RAPHSON = "newton_raphson"
    BISECTION = "bisection"
    BRENT = "brent"
    NONE = "none"


@dataclass(slots=True, frozen=True)
class ImpliedVolatilityRequest:
    market_price: float
    pricing_request: PricingRequest
    model_name: PricingModelName = PricingModelName.BLACK_SCHOLES


@dataclass(slots=True, frozen=True)
class SolverConfig:
    tolerance: float = 1e-8
    max_iterations: int = 100
    newton_max_iterations: int | None = None
    bisection_max_iterations: int | None = None
    initial_guess: float = 0.2
    vol_lower_bound: float = 1e-6
    vol_upper_bound: float = 5.0
    finite_difference_bump: float = 1e-4
    use_brent_interface_on_failure: bool = True
    raise_on_failure: bool = False


@dataclass(slots=True, frozen=True)
class ImpliedVolatilityResult:
    implied_volatility: float | None
    method: SolverMethod
    iterations: int
    converged: bool
    residual: float
    calculation_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class VolatilityObservation:
    symbol: str
    timestamp: datetime
    strike: float
    tenor_days: int
    implied_volatility: float


@dataclass(slots=True, frozen=True)
class VolatilitySurfacePoint:
    symbol: str
    valuation_date: date
    strike: float
    tenor_days: int
    implied_volatility: float
