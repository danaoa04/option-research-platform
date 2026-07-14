from __future__ import annotations

from datetime import date

import pytest

from backend.greeks import (
    GreeksEngine,
    GreeksNotImplementedError,
    GreeksRequest,
    GreeksValidationError,
    PositionLeg,
)
from backend.pricing.models import ExerciseStyle, OptionType, PricingModelName


def _request(
    *,
    option_type: OptionType = OptionType.CALL,
    exercise_style: ExerciseStyle = ExerciseStyle.EUROPEAN,
    spot: float = 100.0,
    strike: float = 100.0,
    volatility: float = 0.2,
    risk_free_rate: float = 0.05,
    dividend_yield: float = 0.0,
    valuation_date: date = date(2026, 1, 1),
    expiry: date = date(2027, 1, 1),
    multiplier: float = 1.0,
) -> GreeksRequest:
    return GreeksRequest(
        spot=spot,
        strike=strike,
        expiry=expiry,
        volatility=volatility,
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
        option_type=option_type,
        exercise_style=exercise_style,
        multiplier=multiplier,
        valuation_date=valuation_date,
    )


def test_black_scholes_greeks_basic_signs_and_magnitude() -> None:
    engine = GreeksEngine()
    call = engine.calculate(_request(option_type=OptionType.CALL))
    put = engine.calculate(_request(option_type=OptionType.PUT))

    assert 0.0 < call.delta < 1.0
    assert -1.0 < put.delta < 0.0
    assert call.gamma > 0.0
    assert put.gamma > 0.0
    assert call.vega > 0.0
    assert put.vega > 0.0


def test_finite_difference_verification_matches_primary_analytics() -> None:
    engine = GreeksEngine()
    verification = engine.finite_difference_verify(_request())

    assert verification.delta.absolute_error < 1e-3
    assert verification.gamma.absolute_error < 1e-4
    assert verification.vega.absolute_error < 1e-2
    assert verification.rho.absolute_error < 2e-2
    assert verification.theta.absolute_error < 2e-3
    assert verification.vanna.absolute_error < 5e-2
    assert verification.vomma.absolute_error < 2e-1


def test_batch_calculation_returns_one_result_per_request() -> None:
    engine = GreeksEngine()
    requests = [
        _request(option_type=OptionType.CALL, strike=95.0),
        _request(option_type=OptionType.PUT, strike=105.0),
        _request(option_type=OptionType.CALL, volatility=0.3),
    ]

    results = engine.calculate_batch(requests)

    assert len(results) == 3
    assert all(result.time_to_expiry > 0.0 for result in results)


def test_portfolio_multi_leg_aggregation() -> None:
    engine = GreeksEngine()
    short_front = PositionLeg(
        request=_request(option_type=OptionType.CALL, strike=100.0, multiplier=100.0),
        quantity=-1.0,
    )
    long_back = PositionLeg(
        request=_request(option_type=OptionType.CALL, strike=105.0, multiplier=100.0),
        quantity=1.0,
    )

    portfolio = engine.calculate_portfolio([short_front, long_back])

    assert len(portfolio.per_leg) == 2
    recomputed_delta = portfolio.per_leg[0].delta + portfolio.per_leg[1].delta
    recomputed_gamma = portfolio.per_leg[0].gamma + portfolio.per_leg[1].gamma
    assert portfolio.total.delta == pytest.approx(recomputed_delta)
    assert portfolio.total.gamma == pytest.approx(recomputed_gamma)


def test_rejects_invalid_greeks_inputs() -> None:
    engine = GreeksEngine()

    with pytest.raises(GreeksValidationError, match="negative volatility"):
        engine.calculate(_request(volatility=-0.01))

    with pytest.raises(GreeksValidationError, match="negative expiry"):
        engine.calculate(_request(expiry=date(2025, 12, 31)))

    with pytest.raises(GreeksValidationError, match="invalid strike"):
        engine.calculate(_request(strike=0.0))

    with pytest.raises(GreeksValidationError, match="invalid spot"):
        engine.calculate(_request(spot=0.0))


def test_only_black_scholes_model_is_currently_supported() -> None:
    engine = GreeksEngine()

    with pytest.raises(GreeksNotImplementedError):
        engine.calculate(_request(), model_name=PricingModelName.BLACK_76)
