"""Validation helpers for implied-volatility requests."""

from __future__ import annotations

from backend.pricing.models import OptionType
from backend.pricing.utilities import intrinsic_value

from .exceptions import ImpliedVolatilityValidationError
from .models import ImpliedVolatilityRequest, SolverConfig


def validate_request(request: ImpliedVolatilityRequest, config: SolverConfig) -> None:
    """Validate solver request and configuration."""
    if request.market_price <= 0.0:
        raise ImpliedVolatilityValidationError("market price must be positive")

    if config.vol_lower_bound <= 0.0:
        raise ImpliedVolatilityValidationError("vol_lower_bound must be positive")
    if config.vol_upper_bound <= config.vol_lower_bound:
        raise ImpliedVolatilityValidationError(
            "vol_upper_bound must be greater than vol_lower_bound"
        )

    pricing_request = request.pricing_request
    intrinsic = intrinsic_value(
        pricing_request.spot,
        pricing_request.strike,
        pricing_request.option_type,
    ) * pricing_request.multiplier
    if request.market_price < intrinsic:
        raise ImpliedVolatilityValidationError(
            "market price cannot be below intrinsic value"
        )

    if pricing_request.option_type == OptionType.CALL:
        max_price = pricing_request.spot * pricing_request.multiplier
    else:
        max_price = pricing_request.strike * pricing_request.multiplier
    if request.market_price > max_price:
        raise ImpliedVolatilityValidationError(
            "market price exceeds simple no-arbitrage upper bound"
        )
