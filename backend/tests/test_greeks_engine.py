from __future__ import annotations

import math
from datetime import date

import pytest

from backend.greeks import (
    FiniteDifferenceConfig,
    GreeksEngine,
    GreeksRequest,
    GreeksValidationError,
    GreekWarningCode,
    PositionLeg,
    benchmark_batch_runtime,
)
from backend.pricing.exceptions import UnsupportedOptionStyleError
from backend.pricing.models import (
    DiscreteDividend,
    ExerciseStyle,
    OptionType,
    PricingModelName,
    SettlementType,
    UnderlyingType,
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
    underlying_type: UnderlyingType = UnderlyingType.EQUITY,
    settlement_type: SettlementType = SettlementType.PHYSICAL,
    futures_price: float | None = None,
    tree_steps: int = 400,
    discrete_dividends: tuple[DiscreteDividend, ...] = (),
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
        underlying_type=underlying_type,
        settlement_type=settlement_type,
        futures_price=futures_price,
        tree_steps=tree_steps,
        discrete_dividends=discrete_dividends,
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
    assert verification.delta.stable
    assert verification.gamma.stable
    assert verification.vega.stable


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


def test_american_numerical_model_rejects_european_style_override() -> None:
    engine = GreeksEngine()

    with pytest.raises(UnsupportedOptionStyleError):
        engine.calculate(_request(), model_name=PricingModelName.COX_ROSS_RUBINSTEIN)


def test_black76_first_order_greeks_for_futures_option() -> None:
    engine = GreeksEngine()
    result = engine.calculate(
        _request(
            option_type=OptionType.CALL,
            exercise_style=ExerciseStyle.EUROPEAN,
            underlying_type=UnderlyingType.FUTURES,
            settlement_type=SettlementType.CASH,
            futures_price=100.0,
        ),
        model_name=PricingModelName.BLACK_76,
    )

    assert math.isfinite(result.delta)
    assert math.isfinite(result.gamma)
    assert math.isfinite(result.theta)
    assert math.isfinite(result.vega)
    assert math.isfinite(result.rho)
    assert "vanna" in result.unsupported_greeks


def test_american_greeks_are_numerical_first_order_only() -> None:
    engine = GreeksEngine()
    request = _request(
        option_type=OptionType.PUT,
        exercise_style=ExerciseStyle.AMERICAN,
        underlying_type=UnderlyingType.EQUITY,
    )
    result = engine.calculate(request)

    assert math.isfinite(result.delta)
    assert math.isfinite(result.gamma)
    assert math.isfinite(result.theta)
    assert math.isfinite(result.vega)
    assert math.isfinite(result.rho)
    assert math.isnan(result.vanna)
    assert "vanna" in result.unsupported_greeks


def test_american_numerical_greeks_handle_multipliers_and_signs() -> None:
    engine = GreeksEngine()
    base = engine.calculate(
        _request(
            exercise_style=ExerciseStyle.AMERICAN,
            option_type=OptionType.PUT,
            multiplier=100.0,
        )
    )
    portfolio = engine.calculate_portfolio(
        [
            PositionLeg(
                request=_request(
                    exercise_style=ExerciseStyle.AMERICAN,
                    option_type=OptionType.PUT,
                    multiplier=100.0,
                ),
                quantity=-2.0,
                model_name=PricingModelName.COX_ROSS_RUBINSTEIN,
            )
        ]
    )

    assert portfolio.total.delta == pytest.approx(-2.0 * base.delta)
    assert portfolio.total.gamma == pytest.approx(-2.0 * base.gamma)


def test_american_greeks_with_dividend_schedule_are_deterministic() -> None:
    engine = GreeksEngine()
    request = _request(
        option_type=OptionType.CALL,
        exercise_style=ExerciseStyle.AMERICAN,
        discrete_dividends=(
            DiscreteDividend(ex_dividend_date=date(2026, 3, 15), amount=1.25),
        ),
    )

    first = engine.calculate(request)
    second = engine.calculate(request)
    assert first.delta == pytest.approx(second.delta)
    assert first.gamma == pytest.approx(second.gamma)
    assert first.theta == pytest.approx(second.theta)
    assert first.vega == pytest.approx(second.vega)
    assert first.rho == pytest.approx(second.rho)
    assert first.supported_greeks == second.supported_greeks
    assert first.unsupported_greeks == second.unsupported_greeks


def test_reference_values_match_published_black_scholes_benchmarks() -> None:
    engine = GreeksEngine()
    result = engine.calculate(_request(option_type=OptionType.CALL))

    assert result.delta == pytest.approx(0.6368, rel=2e-3)
    assert result.gamma == pytest.approx(0.0188, rel=3e-3)
    assert result.vega == pytest.approx(37.5240, rel=2e-3)
    assert result.rho == pytest.approx(53.2325, rel=2e-3)
    assert result.theta == pytest.approx(-0.0176, rel=3e-2)


def test_put_call_delta_relationship_with_dividend_yield() -> None:
    engine = GreeksEngine()
    call_request = _request(option_type=OptionType.CALL, dividend_yield=0.02)
    put_request = _request(option_type=OptionType.PUT, dividend_yield=0.02)
    call = engine.calculate(call_request)
    put = engine.calculate(put_request)

    time_to_expiry = call.time_to_expiry
    expected = pytest.approx(
        call_request.multiplier * math.exp(-call_request.dividend_yield * time_to_expiry),
        rel=1e-6,
    )
    assert (call.delta - put.delta) == expected


def test_short_positions_and_multiplier_are_applied_consistently() -> None:
    engine = GreeksEngine()
    base = engine.calculate(_request(multiplier=100.0))
    short_leg = engine.calculate_portfolio(
        [
            PositionLeg(
                request=_request(multiplier=100.0),
                quantity=-2.0,
            )
        ]
    )

    assert short_leg.total.delta == pytest.approx(-2.0 * base.delta)
    assert short_leg.total.gamma == pytest.approx(-2.0 * base.gamma)
    assert short_leg.total.vega == pytest.approx(-2.0 * base.vega)


def test_expired_and_zero_volatility_behaviors() -> None:
    engine = GreeksEngine()

    with pytest.raises(GreeksValidationError, match="negative expiry"):
        engine.calculate(_request(expiry=date(2025, 12, 31)))

    zero_vol = engine.calculate(_request(volatility=0.0))
    assert zero_vol.delta == 0.0
    assert any(w.code == GreekWarningCode.DEGENERATE_INPUT for w in zero_vol.warnings)


def test_near_zero_time_to_expiry_emits_stability_warning() -> None:
    engine = GreeksEngine()
    near_expiry = _request(expiry=date(2026, 1, 2), valuation_date=date(2026, 1, 1))
    result = engine.calculate(near_expiry)

    assert any(w.code == GreekWarningCode.NUMERICAL_INSTABILITY for w in result.warnings)


def test_finite_difference_config_validation_and_warning_contract() -> None:
    engine = GreeksEngine()

    with pytest.raises(GreeksValidationError, match="bumps must be positive"):
        engine.finite_difference_verify(_request(), FiniteDifferenceConfig(spot_bump=0.0))

    verification = engine.finite_difference_verify(_request())
    warning_codes = {w.code for w in verification.warnings}
    assert GreekWarningCode.UNSUPPORTED_VERIFICATION in warning_codes


def test_batch_calculation_is_deterministic_for_same_inputs() -> None:
    engine = GreeksEngine()
    requests = [
        _request(option_type=OptionType.CALL, strike=95.0),
        _request(option_type=OptionType.PUT, strike=105.0),
        _request(option_type=OptionType.CALL, volatility=0.3),
    ]

    first = engine.calculate_batch(requests)
    second = engine.calculate_batch(requests)
    assert first == second


def test_greeks_batch_benchmark_hook_runs() -> None:
    requests = [_request(strike=90.0), _request(strike=100.0), _request(strike=110.0)]
    result = benchmark_batch_runtime(requests, iterations=5)

    assert result.name == "greeks_batch_runtime"
    assert result.request_count == 3
    assert result.elapsed_seconds >= 0.0
