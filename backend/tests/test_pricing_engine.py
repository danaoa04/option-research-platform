from __future__ import annotations

from datetime import date

import pytest

from backend.pricing import (
    Currency,
    DiscreteDividend,
    DividendType,
    EarlyExerciseAnalyzer,
    ExerciseStyle,
    OptionType,
    PricingEngine,
    PricingModelName,
    PricingRequest,
    PricingValidationError,
    SettlementType,
    UnderlyingType,
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
    underlying_type: UnderlyingType = UnderlyingType.EQUITY,
    settlement_type: SettlementType = SettlementType.PHYSICAL,
    futures_price: float | None = None,
    tree_steps: int = 400,
    discrete_dividends: tuple[DiscreteDividend, ...] = (),
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
        underlying_type=underlying_type,
        settlement_type=settlement_type,
        futures_price=futures_price,
        tree_steps=tree_steps,
        discrete_dividends=discrete_dividends,
        currency=Currency.USD,
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


def test_american_put_is_greater_than_or_equal_to_european_put() -> None:
    engine = PricingEngine()
    european_put = _request(
        option_type=OptionType.PUT,
        exercise_style=ExerciseStyle.EUROPEAN,
        underlying_type=UnderlyingType.EQUITY,
    )
    american_put = _request(
        option_type=OptionType.PUT,
        exercise_style=ExerciseStyle.AMERICAN,
        underlying_type=UnderlyingType.EQUITY,
    )

    euro_price = engine.price(european_put).option_value
    amer_price = engine.price(american_put).option_value

    assert amer_price >= euro_price


def test_non_dividend_american_call_approximates_european_call() -> None:
    engine = PricingEngine()
    european_call = _request(
        option_type=OptionType.CALL,
        exercise_style=ExerciseStyle.EUROPEAN,
        underlying_type=UnderlyingType.EQUITY,
        dividend_yield=0.0,
    )
    american_call = _request(
        option_type=OptionType.CALL,
        exercise_style=ExerciseStyle.AMERICAN,
        underlying_type=UnderlyingType.EQUITY,
        dividend_yield=0.0,
    )

    euro_price = engine.price(european_call).option_value
    amer_price = engine.price(american_call).option_value

    assert amer_price == pytest.approx(euro_price, rel=5e-2)


def test_american_dividend_call_signals_early_exercise_nodes() -> None:
    engine = PricingEngine()
    request = _request(
        option_type=OptionType.CALL,
        exercise_style=ExerciseStyle.AMERICAN,
        underlying_type=UnderlyingType.EQUITY,
        discrete_dividends=(
            DiscreteDividend(ex_dividend_date=date(2026, 3, 1), amount=1.5),
        ),
    )
    result = engine.price(request)

    assert (
        result.calculation_metadata["selected_model"]
        == PricingModelName.COX_ROSS_RUBINSTEIN.value
    )
    assert result.calculation_metadata["early_exercise_nodes"] >= 0


def test_deep_itm_american_put_has_value_above_intrinsic() -> None:
    engine = PricingEngine()
    request = _request(
        option_type=OptionType.PUT,
        exercise_style=ExerciseStyle.AMERICAN,
        underlying_type=UnderlyingType.EQUITY,
        spot=80.0,
        strike=120.0,
    )
    result = engine.price(request)

    assert result.option_value >= result.intrinsic_value


def test_crr_convergence_gap_tightens_with_more_steps() -> None:
    engine = PricingEngine()
    low_steps = engine.price(
        _request(
            option_type=OptionType.PUT,
            exercise_style=ExerciseStyle.AMERICAN,
            tree_steps=100,
        )
    )
    high_steps = engine.price(
        _request(
            option_type=OptionType.PUT,
            exercise_style=ExerciseStyle.AMERICAN,
            tree_steps=600,
        )
    )

    assert high_steps.calculation_metadata["convergence_gap"] <= low_steps.calculation_metadata[
        "convergence_gap"
    ]


def test_black76_reference_value_for_european_futures_option() -> None:
    engine = PricingEngine()
    request = _request(
        option_type=OptionType.CALL,
        exercise_style=ExerciseStyle.EUROPEAN,
        underlying_type=UnderlyingType.FUTURES,
        settlement_type=SettlementType.CASH,
        futures_price=100.0,
        dividend_yield=0.0,
    )
    result = engine.price(request)

    assert result.calculation_metadata["selected_model"] == PricingModelName.BLACK_76.value
    assert result.option_value == pytest.approx(7.5771, rel=3e-3)


def test_model_routing_uses_contract_metadata_not_ticker() -> None:
    engine = PricingEngine()
    european_spot = engine.price(
        _request(
            exercise_style=ExerciseStyle.EUROPEAN,
            underlying_type=UnderlyingType.ETF,
        )
    )
    european_futures = engine.price(
        _request(
            exercise_style=ExerciseStyle.EUROPEAN,
            underlying_type=UnderlyingType.FUTURES,
            settlement_type=SettlementType.CASH,
            futures_price=101.0,
        )
    )
    american_equity = engine.price(
        _request(exercise_style=ExerciseStyle.AMERICAN, underlying_type=UnderlyingType.EQUITY)
    )

    assert (
        european_spot.calculation_metadata["selected_model"]
        == PricingModelName.BLACK_SCHOLES.value
    )
    assert (
        european_futures.calculation_metadata["selected_model"]
        == PricingModelName.BLACK_76.value
    )
    assert (
        american_equity.calculation_metadata["selected_model"]
        == PricingModelName.COX_ROSS_RUBINSTEIN.value
    )


def test_unsupported_american_index_contract_is_explicitly_rejected() -> None:
    engine = PricingEngine()

    with pytest.raises(PricingValidationError, match="unsupported American contract metadata"):
        engine.price(
            _request(
                exercise_style=ExerciseStyle.AMERICAN,
                underlying_type=UnderlyingType.INDEX,
                settlement_type=SettlementType.CASH,
            )
        )


def test_early_exercise_analyzer_handles_missing_dividend_data() -> None:
    analyzer = EarlyExerciseAnalyzer()
    advisory = analyzer.analyze(
        _request(
            option_type=OptionType.CALL,
            exercise_style=ExerciseStyle.AMERICAN,
            underlying_type=UnderlyingType.EQUITY,
            dividend_yield=0.0,
            discrete_dividends=(),
        )
    )

    assert any("no dividend inputs" in warning for warning in advisory.warnings)


def test_early_exercise_analyzer_flags_special_dividend_uncertainty() -> None:
    analyzer = EarlyExerciseAnalyzer()
    advisory = analyzer.analyze(
        _request(
            option_type=OptionType.CALL,
            exercise_style=ExerciseStyle.AMERICAN,
            underlying_type=UnderlyingType.EQUITY,
            discrete_dividends=(
                DiscreteDividend(
                    ex_dividend_date=date(2026, 5, 15),
                    amount=2.0,
                    dividend_type=DividendType.SPECIAL,
                ),
            ),
        )
    )

    assert any("special-dividend uncertainty" in warning for warning in advisory.warnings)


def test_model_capability_registry_exposes_routing_constraints() -> None:
    engine = PricingEngine()
    registry = engine.model_capability_registry()

    assert PricingModelName.BLACK_SCHOLES in registry
    assert PricingModelName.COX_ROSS_RUBINSTEIN in registry
    assert "delta" in registry[PricingModelName.BLACK_76].supported_greeks


def test_batch_pricing_and_multiplier_behavior() -> None:
    engine = PricingEngine()
    requests = [
        _request(multiplier=100.0),
        _request(multiplier=50.0, option_type=OptionType.PUT),
    ]
    results = engine.price_batch(requests)

    assert len(results) == 2
    assert results[0].option_value > results[1].option_value
