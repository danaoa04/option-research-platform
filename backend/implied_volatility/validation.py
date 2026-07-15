"""Validation helpers for model-aware implied-volatility requests."""

from __future__ import annotations

import math
from dataclasses import dataclass

from backend.pricing.models import OptionType, PricingModelName
from backend.pricing.utilities import discount_factor, intrinsic_value, year_fraction

from .exceptions import ImpliedVolatilityValidationError
from .models import (
    FailureReason,
    ImpliedVolatilityRequest,
    QuoteIssuePolicy,
    QuotePolicy,
    SolverConfig,
)


@dataclass(slots=True, frozen=True)
class ValidationDiagnostics:
    market_price: float
    intrinsic_lower_bound: float
    theoretical_upper_bound: float


def select_market_price(
    request: ImpliedVolatilityRequest,
    config: SolverConfig,
) -> tuple[float, list[str]]:
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
            if (
                request.quote_policy == QuotePolicy.STRICT
                or config.crossed_market_policy == QuoteIssuePolicy.REJECT
            ):
                raise ImpliedVolatilityValidationError(
                    "crossed market is not allowed under strict policy"
                )
            if config.crossed_market_policy == QuoteIssuePolicy.CLIP:
                lower = min(request.bid, request.ask)
                upper = max(request.bid, request.ask)
                selected = min(max(float(selected), lower), upper)

        spread = request.ask - request.bid
        if spread > max(1e-12, config.max_relative_spread * max(request.ask, request.bid, 1e-12)):
            warnings.append("wide bid/ask spread")
            if config.wide_spread_policy == QuoteIssuePolicy.REJECT:
                raise ImpliedVolatilityValidationError("wide bid/ask spread rejected by policy")

        if request.bid == 0.0:
            warnings.append("zero bid quote")
            if config.zero_bid_policy == QuoteIssuePolicy.REJECT:
                raise ImpliedVolatilityValidationError("zero bid rejected by policy")

    if request.ask is None and request.market_price_source.value == "ask":
        if config.missing_ask_policy == QuoteIssuePolicy.REJECT:
            raise ImpliedVolatilityValidationError("missing ask quote for ask source")
        warnings.append("missing ask quote")

    if request.quote_is_stale:
        warnings.append("stale quote flag enabled")
        if config.stale_quote_policy == QuoteIssuePolicy.REJECT:
            raise ImpliedVolatilityValidationError("stale quote rejected by policy")

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
    if config.batch_parallelism <= 0:
        raise ImpliedVolatilityValidationError("batch_parallelism must be positive")
    if config.max_relative_spread <= 0.0:
        raise ImpliedVolatilityValidationError("max_relative_spread must be positive")

    pricing_request = request.pricing_request
    if pricing_request.exercise_style is None:
        raise ImpliedVolatilityValidationError(FailureReason.MISSING_CONTRACT_METADATA.value)
    if pricing_request.settlement_type is None:
        raise ImpliedVolatilityValidationError(FailureReason.MISSING_CONTRACT_METADATA.value)
    if pricing_request.underlying_type is None:
        raise ImpliedVolatilityValidationError(FailureReason.MISSING_CONTRACT_METADATA.value)

    _validate_model_contract_compatibility(request, model_name)

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

    market_price, _ = select_market_price(request, config)
    if market_price <= 0.0:
        raise ImpliedVolatilityValidationError("market price must be positive")

    intrinsic = intrinsic_value(
        pricing_request.spot,
        pricing_request.strike,
        pricing_request.option_type,
    ) * pricing_request.multiplier

    theoretical_upper = _theoretical_upper_bound(request, model_name, t)

    bounded_market_price = market_price
    if market_price < intrinsic:
        if config.out_of_bounds_price_policy == QuoteIssuePolicy.CLIP:
            bounded_market_price = intrinsic
        else:
            raise ImpliedVolatilityValidationError(FailureReason.BELOW_INTRINSIC.value)
    if bounded_market_price > theoretical_upper:
        if config.out_of_bounds_price_policy == QuoteIssuePolicy.CLIP:
            bounded_market_price = theoretical_upper
        else:
            raise ImpliedVolatilityValidationError(FailureReason.ABOVE_THEORETICAL_BOUND.value)

    if bounded_market_price < intrinsic:
        raise ImpliedVolatilityValidationError(FailureReason.BELOW_INTRINSIC.value)
    if bounded_market_price > theoretical_upper:
        raise ImpliedVolatilityValidationError(FailureReason.ABOVE_THEORETICAL_BOUND.value)

    return ValidationDiagnostics(
        market_price=bounded_market_price,
        intrinsic_lower_bound=intrinsic,
        theoretical_upper_bound=theoretical_upper,
    )


def _validate_model_contract_compatibility(
    request: ImpliedVolatilityRequest,
    model_name: PricingModelName,
) -> None:
    pricing_request = request.pricing_request

    if model_name == PricingModelName.BLACK_SCHOLES:
        if pricing_request.exercise_style.value != "european":
            raise ImpliedVolatilityValidationError(FailureReason.UNSUPPORTED_PRICING_MODEL.value)
        if pricing_request.underlying_type.value == "futures":
            raise ImpliedVolatilityValidationError(FailureReason.UNSUPPORTED_PRICING_MODEL.value)

    if model_name == PricingModelName.BLACK_76:
        if pricing_request.exercise_style.value != "european":
            raise ImpliedVolatilityValidationError(FailureReason.UNSUPPORTED_PRICING_MODEL.value)
        if pricing_request.underlying_type.value != "futures":
            raise ImpliedVolatilityValidationError(FailureReason.UNSUPPORTED_PRICING_MODEL.value)

    if model_name in {
        PricingModelName.COX_ROSS_RUBINSTEIN,
        PricingModelName.BINOMIAL_TREE,
    }:
        if pricing_request.underlying_type.value not in {"equity", "etf"}:
            raise ImpliedVolatilityValidationError(FailureReason.UNSUPPORTED_PRICING_MODEL.value)


def _theoretical_upper_bound(
    request: ImpliedVolatilityRequest,
    model_name: PricingModelName,
    t: float,
) -> float:
    pricing_request = request.pricing_request
    multiplier = pricing_request.multiplier
    option_type = pricing_request.option_type
    discounted_strike = pricing_request.strike * discount_factor(pricing_request.risk_free_rate, t)

    if model_name == PricingModelName.BLACK_76:
        futures_level = (
            pricing_request.futures_price
            if pricing_request.futures_price is not None
            else pricing_request.spot
            * math.exp((pricing_request.risk_free_rate - pricing_request.dividend_yield) * t)
        )
        if option_type == OptionType.CALL:
            return discount_factor(pricing_request.risk_free_rate, t) * futures_level * multiplier
        return discounted_strike * multiplier

    if pricing_request.exercise_style.value == "american":
        if option_type == OptionType.CALL:
            return pricing_request.spot * multiplier
        return pricing_request.strike * multiplier

    discounted_spot = pricing_request.spot * discount_factor(pricing_request.dividend_yield, t)
    if option_type == OptionType.CALL:
        return discounted_spot * multiplier
    return discounted_strike * multiplier
