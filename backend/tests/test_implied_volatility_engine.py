from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta

import pytest

from backend.implied_volatility import (
    ImpliedVolatilityEngine,
    ImpliedVolatilityRequest,
    ImpliedVolatilityValidationError,
    InMemoryHistoricalIVStorage,
    SmileInterpolator,
    SolverConfig,
    SolverMethod,
    TermStructureInterpolator,
    VolatilityCubeFramework,
    VolatilityObservation,
    VolatilitySurfaceInterpolator,
    VolatilitySurfacePoint,
)
from backend.implied_volatility.interfaces import BrentSolverInterface
from backend.pricing import ExerciseStyle, OptionType, PricingEngine, PricingRequest


def _pricing_request(
    *,
    spot: float = 100.0,
    strike: float = 100.0,
    volatility: float = 0.2,
) -> PricingRequest:
    return PricingRequest(
        spot=spot,
        strike=strike,
        expiry=date(2027, 1, 1),
        volatility=volatility,
        risk_free_rate=0.05,
        dividend_yield=0.0,
        option_type=OptionType.CALL,
        exercise_style=ExerciseStyle.EUROPEAN,
        multiplier=1.0,
        valuation_date=date(2026, 1, 1),
    )


def test_iv_solver_newton_raphson_converges_to_known_volatility() -> None:
    pricing_engine = PricingEngine()
    true_request = _pricing_request(volatility=0.2)
    market_price = pricing_engine.price(true_request).option_value

    engine = ImpliedVolatilityEngine()
    result = engine.solve(
        ImpliedVolatilityRequest(market_price=market_price, pricing_request=true_request),
    )

    assert result.converged is True
    assert result.method == SolverMethod.NEWTON_RAPHSON
    assert result.implied_volatility == pytest.approx(0.2, abs=1e-6)


def test_iv_solver_falls_back_to_bisection_when_newton_is_limited() -> None:
    pricing_engine = PricingEngine()
    true_request = _pricing_request(volatility=0.25)
    market_price = pricing_engine.price(true_request).option_value

    engine = ImpliedVolatilityEngine()
    config = SolverConfig(
        max_iterations=100,
        newton_max_iterations=1,
        bisection_max_iterations=100,
        initial_guess=0.01,
    )
    result = engine.solve(
        ImpliedVolatilityRequest(market_price=market_price, pricing_request=true_request),
        config=config,
    )

    assert result.converged is True
    assert result.method == SolverMethod.BISECTION
    assert result.implied_volatility == pytest.approx(0.25, abs=1e-5)


def test_iv_solver_failure_handling_returns_non_converged_result() -> None:
    request = _pricing_request(spot=100.0, strike=100.0, volatility=0.2)
    engine = ImpliedVolatilityEngine()
    market_price = PricingEngine().price(request).option_value

    result = engine.solve(
        ImpliedVolatilityRequest(market_price=market_price, pricing_request=request),
        config=SolverConfig(
            vol_lower_bound=1e-6,
            vol_upper_bound=0.05,
            raise_on_failure=False,
            use_brent_interface_on_failure=False,
        ),
    )

    assert result.converged is False
    assert result.implied_volatility is None
    assert result.method == SolverMethod.NONE


def test_validation_rejects_market_price_below_intrinsic() -> None:
    request = _pricing_request(spot=120.0, strike=100.0, volatility=0.2)
    engine = ImpliedVolatilityEngine()

    with pytest.raises(ImpliedVolatilityValidationError):
        engine.solve(
            ImpliedVolatilityRequest(market_price=5.0, pricing_request=request),
            config=SolverConfig(),
        )


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


def test_brent_solver_interface_is_used_when_configured() -> None:
    request = _pricing_request(volatility=0.2)
    market_price = PricingEngine().price(request).option_value

    engine = ImpliedVolatilityEngine(brent_solver=_FakeBrentSolver())
    config = SolverConfig(max_iterations=0, use_brent_interface_on_failure=True)
    result = engine.solve(
        ImpliedVolatilityRequest(market_price=market_price, pricing_request=request),
        config=config,
    )

    assert result.converged is True
    assert result.method == SolverMethod.BRENT
    assert result.implied_volatility == pytest.approx(0.33, abs=1e-12)


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
