from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta

import pytest

from backend.implied_volatility import (
    FailureReason,
    ImpliedVolatilityEngine,
    ImpliedVolatilityRequest,
    InMemoryHistoricalIVStorage,
    MarketPriceSource,
    QuotePolicy,
    SmileInterpolator,
    SolverConfig,
    SolverMethod,
    SolverOutcome,
    TermStructureInterpolator,
    VolatilityCubeFramework,
    VolatilityObservation,
    VolatilitySurfaceInterpolator,
    VolatilitySurfacePoint,
)
from backend.implied_volatility.interfaces import BrentSolverInterface
from backend.pricing import ExerciseStyle, OptionType, PricingEngine, PricingRequest
from backend.pricing.models import PricingModelName, SettlementType, UnderlyingType


def _pricing_request(
    *,
    spot: float = 100.0,
    strike: float = 100.0,
    volatility: float = 0.2,
    option_type: OptionType = OptionType.CALL,
    exercise_style: ExerciseStyle = ExerciseStyle.EUROPEAN,
    underlying_type: UnderlyingType = UnderlyingType.EQUITY,
    settlement_type: SettlementType = SettlementType.PHYSICAL,
    futures_price: float | None = None,
    tree_steps: int = 400,
) -> PricingRequest:
    return PricingRequest(
        spot=spot,
        strike=strike,
        expiry=date(2027, 1, 1),
        volatility=volatility,
        risk_free_rate=0.05,
        dividend_yield=0.0,
        option_type=option_type,
        exercise_style=exercise_style,
        multiplier=1.0,
        valuation_date=date(2026, 1, 1),
        underlying_type=underlying_type,
        settlement_type=settlement_type,
        futures_price=futures_price,
        tree_steps=tree_steps,
    )


def test_black_scholes_iv_example_converges() -> None:
    pricing_engine = PricingEngine()
    true_request = _pricing_request(volatility=0.2)
    market_price = pricing_engine.price(true_request).option_value

    engine = ImpliedVolatilityEngine()
    result = engine.solve(
        ImpliedVolatilityRequest(
            market_price=market_price,
            pricing_request=true_request,
            model_name=PricingModelName.BLACK_SCHOLES,
        ),
    )

    assert result.converged is True
    assert result.outcome in {SolverOutcome.SUCCESS, SolverOutcome.APPROXIMATE}
    assert result.method in {
        SolverMethod.NEWTON_RAPHSON,
        SolverMethod.BISECTION,
        SolverMethod.BRENT,
    }
    assert result.implied_volatility == pytest.approx(0.2, abs=1e-6)


def test_black_76_iv_example_converges() -> None:
    pricing_engine = PricingEngine()
    true_request = _pricing_request(
        volatility=0.3,
        underlying_type=UnderlyingType.FUTURES,
        settlement_type=SettlementType.CASH,
        futures_price=100.0,
    )
    market_price = pricing_engine.price(true_request).option_value

    engine = ImpliedVolatilityEngine()
    result = engine.solve(
        ImpliedVolatilityRequest(market_price=market_price, pricing_request=true_request),
    )

    assert result.converged is True
    assert result.pricing_model_used == PricingModelName.BLACK_76
    assert result.implied_volatility == pytest.approx(0.3, abs=1e-5)


def test_american_option_iv_recovery_with_crr_generated_price() -> None:
    pricing_engine = PricingEngine()
    true_request = _pricing_request(
        volatility=0.28,
        option_type=OptionType.PUT,
        exercise_style=ExerciseStyle.AMERICAN,
        underlying_type=UnderlyingType.EQUITY,
        tree_steps=500,
    )
    market_price = pricing_engine.price(true_request).option_value

    engine = ImpliedVolatilityEngine()
    result = engine.solve(
        ImpliedVolatilityRequest(market_price=market_price, pricing_request=true_request)
    )

    assert result.converged is True
    assert result.pricing_model_used == PricingModelName.COX_ROSS_RUBINSTEIN
    assert result.implied_volatility == pytest.approx(0.28, abs=3e-3)
    assert "tree_resolution_sensitivity" in result.calculation_metadata


def test_calls_and_puts_supported() -> None:
    pricing_engine = PricingEngine()
    call_req = _pricing_request(option_type=OptionType.CALL, volatility=0.18)
    put_req = _pricing_request(option_type=OptionType.PUT, volatility=0.24)
    call_price = pricing_engine.price(call_req).option_value
    put_price = pricing_engine.price(put_req).option_value

    engine = ImpliedVolatilityEngine()
    call_iv = engine.solve(
        ImpliedVolatilityRequest(
            market_price=call_price,
            pricing_request=call_req,
        )
    )
    put_iv = engine.solve(
        ImpliedVolatilityRequest(
            market_price=put_price,
            pricing_request=put_req,
        )
    )

    assert call_iv.converged
    assert put_iv.converged
    assert call_iv.implied_volatility == pytest.approx(0.18, abs=1e-5)
    assert put_iv.implied_volatility == pytest.approx(0.24, abs=1e-5)


def test_newton_falls_back_when_limited() -> None:
    pricing_engine = PricingEngine()
    req = _pricing_request(volatility=0.25)
    market_price = pricing_engine.price(req).option_value

    engine = ImpliedVolatilityEngine()
    cfg = SolverConfig(
        newton_max_iterations=1,
        initial_guess=0.01,
        fallback_sequence=(SolverMethod.NEWTON_RAPHSON, SolverMethod.BISECTION),
    )
    result = engine.solve(
        ImpliedVolatilityRequest(market_price=market_price, pricing_request=req),
        cfg,
    )

    assert result.converged is True
    assert result.method == SolverMethod.BISECTION


def test_brent_interface_used_when_in_fallback_sequence() -> None:
    class _FakeBrentSolver(BrentSolverInterface):
        def solve(
            self,
            func: Callable[[float], float],
            low: float,
            high: float,
            tolerance: float,
            max_iterations: int,
        ) -> tuple[float, int, bool, float]:
            root = 0.33
            return root, 2, True, func(root)

    pricing_engine = PricingEngine()
    req = _pricing_request(volatility=0.2)
    market_price = pricing_engine.price(req).option_value

    engine = ImpliedVolatilityEngine(brent_solver=_FakeBrentSolver())
    cfg = SolverConfig(
        newton_max_iterations=0,
        bisection_max_iterations=0,
        fallback_sequence=(SolverMethod.BRENT,),
    )
    result = engine.solve(
        ImpliedVolatilityRequest(market_price=market_price, pricing_request=req),
        cfg,
    )

    assert result.converged is True
    assert result.method == SolverMethod.BRENT
    assert result.implied_volatility == pytest.approx(0.33, abs=1e-12)


def test_low_vega_failure_reason_is_exposed() -> None:
    pricing_engine = PricingEngine()
    req = _pricing_request(volatility=0.2)
    market_price = pricing_engine.price(req).option_value

    engine = ImpliedVolatilityEngine()
    cfg = SolverConfig(
        min_vega=1e6,
        initial_guess=0.01,
        fallback_sequence=(SolverMethod.NEWTON_RAPHSON,),
        raise_on_failure=False,
    )
    result = engine.solve(
        ImpliedVolatilityRequest(market_price=market_price, pricing_request=req),
        cfg,
    )

    assert result.converged is False
    assert result.failure_reason == FailureReason.LOW_VEGA


def test_invalid_market_price_below_intrinsic_returns_structured_failure() -> None:
    req = _pricing_request(spot=120.0, strike=100.0, volatility=0.2)
    engine = ImpliedVolatilityEngine()
    result = engine.solve(ImpliedVolatilityRequest(market_price=5.0, pricing_request=req))

    assert result.converged is False
    assert result.outcome == SolverOutcome.INVALID_MARKET_PRICE
    assert result.failure_reason == FailureReason.BELOW_INTRINSIC


def test_no_bracketed_solution_is_reported() -> None:
    pricing_engine = PricingEngine()
    req = _pricing_request(volatility=0.8)
    market_price = pricing_engine.price(req).option_value

    engine = ImpliedVolatilityEngine()
    cfg = SolverConfig(vol_upper_bound=0.1)
    result = engine.solve(
        ImpliedVolatilityRequest(market_price=market_price, pricing_request=req),
        cfg,
    )

    assert result.converged is False
    assert result.failure_reason == FailureReason.NO_BRACKETED_SOLUTION


def test_batch_and_scalar_consistency_and_ordering() -> None:
    pricing_engine = PricingEngine()
    requests = [
        _pricing_request(volatility=0.15, option_type=OptionType.CALL),
        _pricing_request(volatility=0.2, option_type=OptionType.PUT),
        _pricing_request(
            volatility=0.3,
            underlying_type=UnderlyingType.FUTURES,
            settlement_type=SettlementType.CASH,
            futures_price=100.0,
        ),
    ]
    iv_requests = [
        ImpliedVolatilityRequest(
            market_price=pricing_engine.price(req).option_value,
            pricing_request=req,
        )
        for req in requests
    ]

    engine = ImpliedVolatilityEngine()
    scalar = [engine.solve(req) for req in iv_requests]
    batch = engine.solve_batch(iv_requests).results

    assert [r.pricing_model_used for r in batch] == [r.pricing_model_used for r in scalar]
    assert [r.outcome for r in batch] == [r.outcome for r in scalar]


def test_mixed_batch_returns_per_contract_errors_without_abort() -> None:
    pricing_engine = PricingEngine()
    valid = _pricing_request(volatility=0.2)
    valid_price = pricing_engine.price(valid).option_value
    invalid = _pricing_request(spot=120.0, strike=100.0)

    engine = ImpliedVolatilityEngine()
    batch = engine.solve_batch(
        [
            ImpliedVolatilityRequest(market_price=valid_price, pricing_request=valid),
            ImpliedVolatilityRequest(market_price=1.0, pricing_request=invalid),
        ]
    )

    assert len(batch.results) == 2
    assert batch.results[0].converged is True
    assert batch.results[1].converged is False
    assert batch.results[1].outcome == SolverOutcome.INVALID_MARKET_PRICE


def test_router_driven_model_selection_and_no_silent_black_scholes_fallback() -> None:
    pricing_engine = PricingEngine()
    american_req = _pricing_request(
        option_type=OptionType.PUT,
        exercise_style=ExerciseStyle.AMERICAN,
        underlying_type=UnderlyingType.EQUITY,
        volatility=0.22,
    )
    market_price = pricing_engine.price(american_req).option_value

    engine = ImpliedVolatilityEngine()
    result = engine.solve(
        ImpliedVolatilityRequest(
            market_price=market_price,
            pricing_request=american_req,
        )
    )

    assert result.pricing_model_used == PricingModelName.COX_ROSS_RUBINSTEIN
    assert result.pricing_model_used != PricingModelName.BLACK_SCHOLES


def test_quote_source_policy_records_source_and_flags_stale_quotes() -> None:
    req = _pricing_request(volatility=0.2)
    market = PricingEngine().price(req).option_value

    engine = ImpliedVolatilityEngine()
    result = engine.solve(
        ImpliedVolatilityRequest(
            market_price=market,
            mark_price=market,
            bid=max(market - 0.2, 1e-6),
            ask=market + 0.2,
            quote_is_stale=True,
            market_price_source=MarketPriceSource.MARK,
            quote_policy=QuotePolicy.CLIP_TO_BOUNDS,
            pricing_request=req,
        )
    )

    assert result.converged is True
    assert result.calculation_metadata["price_source"] == MarketPriceSource.MARK.value
    assert any("stale quote" in warning for warning in result.warnings)


def test_smile_term_surface_and_cube_interpolation() -> None:
    smile = SmileInterpolator(strikes=[90.0, 100.0, 110.0], ivs=[0.30, 0.25, 0.22])
    assert smile.evaluate(105.0) == pytest.approx(0.235, abs=1e-12)

    term = TermStructureInterpolator(tenors=[30, 60], ivs=[0.24, 0.20])
    assert term.evaluate(45) == pytest.approx(0.22, abs=1e-12)

    surface = VolatilitySurfaceInterpolator(
        surface_points=[
            VolatilitySurfacePoint(
                symbol="SPY",
                valuation_date=date(2026, 1, 1),
                strike=100.0,
                tenor_days=30,
                implied_volatility=0.25,
            ),
            VolatilitySurfacePoint(
                symbol="SPY",
                valuation_date=date(2026, 1, 1),
                strike=110.0,
                tenor_days=30,
                implied_volatility=0.23,
            ),
            VolatilitySurfacePoint(
                symbol="SPY",
                valuation_date=date(2026, 1, 1),
                strike=100.0,
                tenor_days=60,
                implied_volatility=0.22,
            ),
            VolatilitySurfacePoint(
                symbol="SPY",
                valuation_date=date(2026, 1, 1),
                strike=110.0,
                tenor_days=60,
                implied_volatility=0.21,
            ),
        ]
    )
    assert surface.evaluate(strike=105.0, tenor_days=45) == pytest.approx(0.2275, abs=1e-12)

    cube = VolatilityCubeFramework()
    cube.add_point(
        symbol="SPY",
        valuation_date=date(2026, 1, 1),
        tenor_days=30,
        strike=100.0,
        implied_volatility=0.25,
    )
    cube.add_point(
        symbol="SPY",
        valuation_date=date(2026, 1, 1),
        tenor_days=30,
        strike=110.0,
        implied_volatility=0.23,
    )
    cube.add_point(
        symbol="SPY",
        valuation_date=date(2026, 1, 1),
        tenor_days=60,
        strike=100.0,
        implied_volatility=0.22,
    )
    cube.add_point(
        symbol="SPY",
        valuation_date=date(2026, 1, 1),
        tenor_days=60,
        strike=110.0,
        implied_volatility=0.21,
    )
    assert cube.evaluate(
        symbol="SPY",
        valuation_date=date(2026, 1, 1),
        strike=105.0,
        tenor_days=45,
    ) == pytest.approx(0.2275, abs=1e-12)


def test_historical_iv_storage_hooks() -> None:
    store = InMemoryHistoricalIVStorage()
    now = datetime(2026, 1, 1, 10, 0)
    store.store(
        VolatilityObservation(
            symbol="SPY",
            timestamp=now,
            strike=100.0,
            tenor_days=30,
            implied_volatility=0.25,
        )
    )
    store.store(
        VolatilityObservation(
            symbol="SPY",
            timestamp=now + timedelta(minutes=5),
            strike=105.0,
            tenor_days=30,
            implied_volatility=0.24,
        )
    )

    rows = store.query(
        symbol="SPY",
        start_ts=now - timedelta(minutes=1),
        end_ts=now + timedelta(minutes=10),
    )

    assert len(rows) == 2
