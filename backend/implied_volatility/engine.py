"""Implied-volatility solver engine with multiple root-finding paths."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from backend.pricing import PricingEngine, PricingRequest

from .exceptions import ImpliedVolatilityConvergenceError
from .interfaces import BrentSolverInterface
from .models import (
    ImpliedVolatilityRequest,
    ImpliedVolatilityResult,
    SolverConfig,
    SolverMethod,
)
from .validation import validate_request


@dataclass(slots=True)
class ImpliedVolatilityEngine:
    """Solve implied volatility from market price with robust fallback behavior."""

    pricing_engine: PricingEngine = field(default_factory=PricingEngine)
    brent_solver: BrentSolverInterface | None = None

    def solve(
        self,
        request: ImpliedVolatilityRequest,
        config: SolverConfig | None = None,
    ) -> ImpliedVolatilityResult:
        cfg = config or SolverConfig()
        validate_request(request, cfg)

        target_price = request.market_price

        def objective(volatility: float) -> float:
            updated = _with_volatility(request.pricing_request, volatility)
            model_price = self.pricing_engine.price(updated, request.model_name).option_value
            return model_price - target_price

        newton = self._newton_raphson(objective, cfg)
        if newton.converged:
            return newton

        bisection = self._bisection(objective, cfg)
        if bisection.converged:
            return bisection

        if cfg.use_brent_interface_on_failure and self.brent_solver is not None:
            brent = self._brent_interface(objective, cfg)
            if brent.converged:
                return brent

        message = "implied-volatility solver did not converge"
        if cfg.raise_on_failure:
            raise ImpliedVolatilityConvergenceError(message)

        warnings = [message, "newton and bisection failed within configured bounds"]
        if cfg.use_brent_interface_on_failure and self.brent_solver is None:
            warnings.append("brent solver interface requested but not configured")

        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.NONE,
            iterations=cfg.max_iterations,
            converged=False,
            residual=float("inf"),
            calculation_metadata={"model": request.model_name.value},
            warnings=warnings,
        )

    def _newton_raphson(
        self,
        objective: Callable[[float], float],
        config: SolverConfig,
    ) -> ImpliedVolatilityResult:
        max_iterations = (
            config.newton_max_iterations
            if config.newton_max_iterations is not None
            else config.max_iterations
        )
        vol = min(max(config.initial_guess, config.vol_lower_bound), config.vol_upper_bound)
        residual = objective(vol)

        for iteration in range(1, max_iterations + 1):
            if abs(residual) <= config.tolerance:
                return ImpliedVolatilityResult(
                    implied_volatility=vol,
                    method=SolverMethod.NEWTON_RAPHSON,
                    iterations=iteration,
                    converged=True,
                    residual=residual,
                    calculation_metadata={"solver": "newton_raphson"},
                )

            bumped = min(vol + config.finite_difference_bump, config.vol_upper_bound)
            deriv = (objective(bumped) - residual) / max(bumped - vol, 1e-12)
            if abs(deriv) < 1e-12:
                break

            step = residual / deriv
            candidate = vol - step
            if candidate <= config.vol_lower_bound or candidate >= config.vol_upper_bound:
                break

            vol = candidate
            residual = objective(vol)

        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.NEWTON_RAPHSON,
            iterations=max_iterations,
            converged=False,
            residual=residual,
            calculation_metadata={"solver": "newton_raphson"},
            warnings=["newton_raphson did not converge"],
        )

    def _bisection(
        self,
        objective: Callable[[float], float],
        config: SolverConfig,
    ) -> ImpliedVolatilityResult:
        max_iterations = (
            config.bisection_max_iterations
            if config.bisection_max_iterations is not None
            else config.max_iterations
        )
        low = config.vol_lower_bound
        high = config.vol_upper_bound
        f_low = objective(low)
        f_high = objective(high)

        if f_low == 0.0:
            return ImpliedVolatilityResult(
                implied_volatility=low,
                method=SolverMethod.BISECTION,
                iterations=0,
                converged=True,
                residual=0.0,
                calculation_metadata={"solver": "bisection"},
            )

        if f_low * f_high > 0.0:
            return ImpliedVolatilityResult(
                implied_volatility=None,
                method=SolverMethod.BISECTION,
                iterations=0,
                converged=False,
                residual=min(abs(f_low), abs(f_high)),
                calculation_metadata={"solver": "bisection"},
                warnings=["bisection root not bracketed"],
            )

        mid = low
        f_mid = f_low
        for iteration in range(1, max_iterations + 1):
            mid = 0.5 * (low + high)
            f_mid = objective(mid)

            if abs(f_mid) <= config.tolerance or abs(high - low) <= config.tolerance:
                return ImpliedVolatilityResult(
                    implied_volatility=mid,
                    method=SolverMethod.BISECTION,
                    iterations=iteration,
                    converged=True,
                    residual=f_mid,
                    calculation_metadata={"solver": "bisection"},
                )

            if f_low * f_mid < 0.0:
                high = mid
                f_high = f_mid
            else:
                low = mid
                f_low = f_mid

        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.BISECTION,
            iterations=max_iterations,
            converged=False,
            residual=f_mid,
            calculation_metadata={"solver": "bisection"},
            warnings=["bisection did not converge"],
        )

    def _brent_interface(
        self,
        objective: Callable[[float], float],
        config: SolverConfig,
    ) -> ImpliedVolatilityResult:
        if self.brent_solver is None:
            return ImpliedVolatilityResult(
                implied_volatility=None,
                method=SolverMethod.BRENT,
                iterations=0,
                converged=False,
                residual=float("inf"),
                calculation_metadata={"solver": "brent"},
                warnings=["brent solver interface is not configured"],
            )

        root, iterations, converged, residual = self.brent_solver.solve(
            func=objective,
            low=config.vol_lower_bound,
            high=config.vol_upper_bound,
            tolerance=config.tolerance,
            max_iterations=config.max_iterations,
        )

        return ImpliedVolatilityResult(
            implied_volatility=root if converged else None,
            method=SolverMethod.BRENT,
            iterations=iterations,
            converged=converged,
            residual=residual,
            calculation_metadata={"solver": "brent_interface"},
            warnings=[] if converged else ["brent solver did not converge"],
        )


def _with_volatility(request: PricingRequest, volatility: float) -> PricingRequest:
    return PricingRequest(
        spot=request.spot,
        strike=request.strike,
        expiry=request.expiry,
        volatility=volatility,
        risk_free_rate=request.risk_free_rate,
        dividend_yield=request.dividend_yield,
        option_type=request.option_type,
        exercise_style=request.exercise_style,
        multiplier=request.multiplier,
        valuation_date=request.valuation_date,
    )
