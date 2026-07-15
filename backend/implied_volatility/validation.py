"""Validation helpers for model-aware implied-volatility requests."""

from __future__ import annotations

from dataclasses import dataclass

from backend.pricing.models import OptionType, PricingModelName
from backend.pricing.utilities import intrinsic_value, year_fraction

from .exceptions import ImpliedVolatilityValidationError
from .models import (
    FailureReason,
    ImpliedVolatilityRequest,
    QuotePolicy,
    SolverConfig,
)


@dataclass(slots=True, frozen=True)
class ValidationDiagnostics:
    market_price: float
    intrinsic_lower_bound: float
    theoretical_upper_bound: float


def select_market_price(request: ImpliedVolatilityRequest) -> tuple[float, list[str]]:
    """Resolve configured quote source and policy into one market price."""
    warnings: list[str] = []
    source = request.market_price_source

    if source.value == "bid":
        selected = request.bid
    elif source.value == "ask":
        selected = request.ask
    elif source.value == "last":
        selected = request.last
    elif source.value == "mark":
        selected = request.mark_price if request.mark_price is not None else request.market_price
    else:
        if request.bid is not None and request.ask is not None:
            selected = 0.5 * (request.bid + request.ask)
        else:
            selected = request.market_price

    if selected is None:
        selected = request.market_price

    if request.bid is not None and request.ask is not None:
        if request.bid > request.ask:
            warnings.append("crossed market detected")
            if request.quote_policy == QuotePolicy.STRICT:
                raise ImpliedVolatilityValidationError(
                    "crossed market is not allowed under strict policy"
                )

        spread = request.ask - request.bid
        if spread > max(1e-12, 0.2 * max(request.ask, request.bid, 1e-12)):
            warnings.append("wide bid/ask spread")

        if request.bid == 0.0:
            warnings.append("zero bid quote")

    if request.ask is None and request.market_price_source.value == "ask":
        raise ImpliedVolatilityValidationError("missing ask quote for ask source")

    if request.quote_is_stale:
        warnings.append("stale quote flag enabled")

    return selected, warnings


def validate_request(
    request: ImpliedVolatilityRequest,
    config: SolverConfig,
    model_name: PricingModelName,
) -> ValidationDiagnostics:
    """Validate request/config and return key arbitrage bounds diagnostics."""
    if config.vol_lower_bound <= 0.0:
        raise ImpliedVolatilityValidationError("vol_lower_bound must be positive")
    if config.vol_upper_bound <= config.vol_lower_bound:
        raise ImpliedVolatilityValidationError(
            "vol_upper_bound must be greater than vol_lower_bound"
        )
    if config.price_tolerance <= 0.0:
        raise ImpliedVolatilityValidationError("price_tolerance must be positive")
    if config.volatility_tolerance <= 0.0:
        raise ImpliedVolatilityValidationError("volatility_tolerance must be positive")

    pricing_request = request.pricing_request
    t = year_fraction(pricing_request.valuation_date, pricing_request.expiry)
    if t < 0.0:
        raise ImpliedVolatilityValidationError(FailureReason.INVALID_INPUT.value)
    if t == 0.0:
        raise ImpliedVolatilityValidationError(FailureReason.EXPIRED_OPTION.value)

    if pricing_request.spot <= 0.0 or pricing_request.strike <= 0.0:
        raise ImpliedVolatilityValidationError(FailureReason.INVALID_INPUT.value)

    for dividend in pricing_request.discrete_dividends:
        if dividend.amount <= 0.0:
            raise ImpliedVolatilityValidationError(FailureReason.INVALID_DIVIDEND_DATA.value)
        if dividend.ex_dividend_date < pricing_request.valuation_date:
            raise ImpliedVolatilityValidationError(FailureReason.INVALID_DIVIDEND_DATA.value)

    if pricing_request.multiplier <= 0.0:
        raise ImpliedVolatilityValidationError(FailureReason.INVALID_INPUT.value)

    market_price, _ = select_market_price(request)
    if market_price <= 0.0:
        raise ImpliedVolatilityValidationError("market price must be positive")

    intrinsic = intrinsic_value(
        pricing_request.spot,
        pricing_request.strike,
        pricing_request.option_type,
    ) * pricing_request.multiplier

    if model_name == PricingModelName.BLACK_76:
        base = pricing_request.futures_price
        if base is None:
            base = pricing_request.spot
    else:
        base = pricing_request.spot

    if pricing_request.option_type == OptionType.CALL:
        theoretical_upper = base * pricing_request.multiplier
    else:
        theoretical_upper = pricing_request.strike * pricing_request.multiplier

    if market_price < intrinsic:
        raise ImpliedVolatilityValidationError(FailureReason.BELOW_INTRINSIC.value)
    if market_price > theoretical_upper:
        raise ImpliedVolatilityValidationError(FailureReason.ABOVE_THEORETICAL_BOUND.value)

    return ValidationDiagnostics(
        market_price=market_price,
        intrinsic_lower_bound=intrinsic,
        theoretical_upper_bound=theoretical_upper,
    )
