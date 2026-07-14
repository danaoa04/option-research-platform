from __future__ import annotations

from datetime import date

import pytest

from backend.pricing import (
    ExerciseStyle,
    OptionType,
    PricingEngine,
    PricingModelName,
    PricingModelNotImplementedError,
    PricingRequest,
    PricingValidationError,
    UnsupportedOptionStyleError,
)


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
) -> PricingRequest:
    return PricingRequest(
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


def test_black_scholes_call_matches_reference_example() -> None:
    # Published reference values for S=100, K=100, r=5%, q=0, sigma=20%, T=1.
    engine = PricingEngine()
    result = engine.price(_request(option_type=OptionType.CALL))

    assert result.option_value == pytest.approx(10.4506, abs=1e-4)
    assert result.intrinsic_value == pytest.approx(0.0, abs=1e-10)
    assert result.extrinsic_value == pytest.approx(10.4506, abs=1e-4)
    assert result.time_to_expiry == pytest.approx(1.0, abs=1e-12)


def test_black_scholes_put_matches_reference_example() -> None:
    # Published reference values for S=100, K=100, r=5%, q=0, sigma=20%, T=1.
    engine = PricingEngine()
    result = engine.price(_request(option_type=OptionType.PUT))

    assert result.option_value == pytest.approx(5.5735, abs=1e-4)
    assert result.intrinsic_value == pytest.approx(0.0, abs=1e-10)
    assert result.extrinsic_value == pytest.approx(5.5735, abs=1e-4)


def test_rejects_invalid_pricing_inputs() -> None:
    engine = PricingEngine()

    with pytest.raises(PricingValidationError, match="negative volatility"):
        engine.price(_request(volatility=-0.01))

    with pytest.raises(PricingValidationError, match="negative expiry"):
        engine.price(_request(expiry=date(2025, 12, 31)))

    with pytest.raises(PricingValidationError, match="invalid strike"):
        engine.price(_request(strike=0.0))

    with pytest.raises(PricingValidationError, match="invalid spot"):
        engine.price(_request(spot=-1.0))


def test_rejects_unsupported_option_style_for_black_scholes() -> None:
    engine = PricingEngine()
    request = _request(exercise_style=ExerciseStyle.AMERICAN)

    with pytest.raises(UnsupportedOptionStyleError):
        engine.price(request, model_name=PricingModelName.BLACK_SCHOLES)


def test_unimplemented_models_raise_deterministic_error() -> None:
    engine = PricingEngine()
    request = _request()

    with pytest.raises(PricingModelNotImplementedError):
        engine.price(request, model_name=PricingModelName.BLACK_76)
