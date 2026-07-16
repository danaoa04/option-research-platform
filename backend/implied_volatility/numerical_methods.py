"""Numerical methods for implied-volatility root-finding."""

from __future__ import annotations

import math
from collections.abc import Callable

from .models import (
    FailureReason,
    ImpliedVolatilityResult,
    SolverConfig,
    SolverMethod,
    SolverOutcome,
)


def _evaluate_objective(
    objective: Callable[[float], float],
    volatility: float,
) -> tuple[float | None, FailureReason]:
    try:
        value = objective(volatility)
    except Exception:
        return None, FailureReason.NUMERICAL_INSTABILITY
    if not math.isfinite(value):
        return None, FailureReason.NUMERICAL_INSTABILITY
    return value, FailureReason.NONE


def solve_newton_raphson(
    objective: Callable[[float], float],
    config: SolverConfig,
) -> ImpliedVolatilityResult:
    max_iterations = (
        config.newton_max_iterations
        if config.newton_max_iterations is not None
        else config.max_iterations
    )
    vol = min(max(config.initial_guess, config.vol_lower_bound), config.vol_upper_bound)
    residual, reason = _evaluate_objective(objective, vol)
    if residual is None:
        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.NEWTON_RAPHSON,
            iterations=0,
            converged=False,
            residual=float("inf"),
            final_pricing_error=None,
            outcome=SolverOutcome.NON_CONVERGENCE,
            failure_reason=reason,
            lower_bound=config.vol_lower_bound,
            upper_bound=config.vol_upper_bound,
            calculation_metadata={"solver": "newton_raphson"},
            warnings=["newton_raphson encountered unstable objective"],
        )

    stalled_count = 0
    for iteration in range(1, max_iterations + 1):
        assert residual is not None
        if abs(residual) <= config.price_tolerance:
            return ImpliedVolatilityResult(
                implied_volatility=vol,
                method=SolverMethod.NEWTON_RAPHSON,
                iterations=iteration,
                converged=True,
                residual=residual,
                final_pricing_error=residual,
                outcome=SolverOutcome.SUCCESS,
                failure_reason=FailureReason.NONE,
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
                calculation_metadata={"solver": "newton_raphson"},
            )

        forward = min(vol + config.finite_difference_bump, config.vol_upper_bound)
        backward = max(vol - config.finite_difference_bump, config.vol_lower_bound)
        f_forward, reason_forward = _evaluate_objective(objective, forward)
        f_backward, reason_backward = _evaluate_objective(objective, backward)
        if f_forward is None or f_backward is None:
            return ImpliedVolatilityResult(
                implied_volatility=None,
                method=SolverMethod.NEWTON_RAPHSON,
                iterations=iteration,
                converged=False,
                residual=residual,
                final_pricing_error=residual,
                outcome=SolverOutcome.NON_CONVERGENCE,
                failure_reason=(
                    reason_forward if reason_forward != FailureReason.NONE else reason_backward
                ),
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
                calculation_metadata={"solver": "newton_raphson"},
                warnings=["newton_raphson derivative evaluation unstable"],
            )

        deriv = (f_forward - f_backward) / max(forward - backward, 1e-12)
        if abs(deriv) < config.min_vega:
            return ImpliedVolatilityResult(
                implied_volatility=None,
                method=SolverMethod.NEWTON_RAPHSON,
                iterations=iteration,
                converged=False,
                residual=residual,
                final_pricing_error=residual,
                outcome=SolverOutcome.NON_CONVERGENCE,
                failure_reason=FailureReason.LOW_VEGA,
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
                calculation_metadata={"solver": "newton_raphson"},
                warnings=["newton_raphson vega too small"],
            )

        step = residual / deriv
        candidate = vol - step
        if candidate <= config.vol_lower_bound or candidate >= config.vol_upper_bound:
            return ImpliedVolatilityResult(
                implied_volatility=None,
                method=SolverMethod.NEWTON_RAPHSON,
                iterations=iteration,
                converged=False,
                residual=residual,
                final_pricing_error=residual,
                outcome=SolverOutcome.NON_CONVERGENCE,
                failure_reason=FailureReason.OUT_OF_BOUNDS_UPDATE,
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
                calculation_metadata={"solver": "newton_raphson"},
                warnings=["newton_raphson update exited volatility bounds"],
            )

        prev_residual = residual
        vol = candidate
        residual, reason = _evaluate_objective(objective, vol)
        if residual is None:
            return ImpliedVolatilityResult(
                implied_volatility=None,
                method=SolverMethod.NEWTON_RAPHSON,
                iterations=iteration,
                converged=False,
                residual=float("inf"),
                final_pricing_error=None,
                outcome=SolverOutcome.NON_CONVERGENCE,
                failure_reason=reason,
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
                calculation_metadata={"solver": "newton_raphson"},
                warnings=["newton_raphson objective became unstable"],
            )

        if abs(prev_residual - residual) <= config.price_tolerance:
            stalled_count += 1
        else:
            stalled_count = 0

        if stalled_count >= config.max_stalled_iterations:
            return ImpliedVolatilityResult(
                implied_volatility=None,
                method=SolverMethod.NEWTON_RAPHSON,
                iterations=iteration,
                converged=False,
                residual=residual,
                final_pricing_error=residual,
                outcome=SolverOutcome.NON_CONVERGENCE,
                failure_reason=FailureReason.STALLED,
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
                calculation_metadata={"solver": "newton_raphson"},
                warnings=["newton_raphson stalled"],
            )

        if abs(step) <= config.volatility_tolerance:
            return ImpliedVolatilityResult(
                implied_volatility=vol,
                method=SolverMethod.NEWTON_RAPHSON,
                iterations=iteration,
                converged=True,
                residual=residual,
                final_pricing_error=residual,
                outcome=SolverOutcome.APPROXIMATE,
                failure_reason=FailureReason.NONE,
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
                calculation_metadata={"solver": "newton_raphson", "approximate": True},
                warnings=["newton_raphson reached volatility tolerance before price tolerance"],
            )

    assert residual is not None
    return ImpliedVolatilityResult(
        implied_volatility=None,
        method=SolverMethod.NEWTON_RAPHSON,
        iterations=max_iterations,
        converged=False,
        residual=residual,
        final_pricing_error=residual,
        outcome=SolverOutcome.NON_CONVERGENCE,
        failure_reason=FailureReason.STALLED,
        lower_bound=config.vol_lower_bound,
        upper_bound=config.vol_upper_bound,
        calculation_metadata={"solver": "newton_raphson"},
        warnings=["newton_raphson did not converge"],
    )


def solve_bisection(
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
    f_low, reason_low = _evaluate_objective(objective, low)
    f_high, reason_high = _evaluate_objective(objective, high)
    if f_low is None or f_high is None:
        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.BISECTION,
            iterations=0,
            converged=False,
            residual=float("inf"),
            final_pricing_error=None,
            outcome=SolverOutcome.NON_CONVERGENCE,
            failure_reason=(reason_low if reason_low != FailureReason.NONE else reason_high),
            lower_bound=low,
            upper_bound=high,
            calculation_metadata={"solver": "bisection"},
            warnings=["bisection encountered unstable objective"],
        )

    if f_low == 0.0:
        return ImpliedVolatilityResult(
            implied_volatility=low,
            method=SolverMethod.BISECTION,
            iterations=0,
            converged=True,
            residual=0.0,
            final_pricing_error=0.0,
            outcome=SolverOutcome.SUCCESS,
            failure_reason=FailureReason.NONE,
            lower_bound=low,
            upper_bound=high,
            calculation_metadata={"solver": "bisection"},
        )

    if f_low * f_high > 0.0:
        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.BISECTION,
            iterations=0,
            converged=False,
            residual=min(abs(f_low), abs(f_high)),
            final_pricing_error=min(abs(f_low), abs(f_high)),
            outcome=SolverOutcome.NON_CONVERGENCE,
            failure_reason=FailureReason.NO_BRACKETED_SOLUTION,
            lower_bound=low,
            upper_bound=high,
            calculation_metadata={"solver": "bisection"},
            warnings=["bisection root not bracketed"],
        )

    mid = low
    f_mid = f_low
    for iteration in range(1, max_iterations + 1):
        mid = 0.5 * (low + high)
        maybe_mid, reason_mid = _evaluate_objective(objective, mid)
        if maybe_mid is None:
            return ImpliedVolatilityResult(
                implied_volatility=None,
                method=SolverMethod.BISECTION,
                iterations=iteration,
                converged=False,
                residual=float("inf"),
                final_pricing_error=None,
                outcome=SolverOutcome.NON_CONVERGENCE,
                failure_reason=reason_mid,
                lower_bound=low,
                upper_bound=high,
                calculation_metadata={"solver": "bisection"},
                warnings=["bisection objective became unstable"],
            )
        f_mid = maybe_mid

        if abs(f_mid) <= config.price_tolerance or abs(high - low) <= config.volatility_tolerance:
            return ImpliedVolatilityResult(
                implied_volatility=mid,
                method=SolverMethod.BISECTION,
                iterations=iteration,
                converged=True,
                residual=f_mid,
                final_pricing_error=f_mid,
                outcome=(
                    SolverOutcome.SUCCESS
                    if abs(f_mid) <= config.price_tolerance
                    else SolverOutcome.APPROXIMATE
                ),
                failure_reason=FailureReason.NONE,
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
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
        final_pricing_error=f_mid,
        outcome=SolverOutcome.NON_CONVERGENCE,
        failure_reason=FailureReason.STALLED,
        lower_bound=config.vol_lower_bound,
        upper_bound=config.vol_upper_bound,
        calculation_metadata={"solver": "bisection"},
        warnings=["bisection did not converge"],
    )


def solve_brent_hybrid(
    objective: Callable[[float], float],
    config: SolverConfig,
) -> ImpliedVolatilityResult:
    """Brent-style safeguarded inverse-quadratic/bisection hybrid."""
    max_iterations = (
        config.brent_max_iterations
        if config.brent_max_iterations is not None
        else config.max_iterations
    )
    a = config.vol_lower_bound
    b = config.vol_upper_bound
    fa, reason_a = _evaluate_objective(objective, a)
    fb, reason_b = _evaluate_objective(objective, b)
    if fa is None or fb is None:
        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.BRENT,
            iterations=0,
            converged=False,
            residual=float("inf"),
            final_pricing_error=None,
            outcome=SolverOutcome.NON_CONVERGENCE,
            failure_reason=(reason_a if reason_a != FailureReason.NONE else reason_b),
            lower_bound=a,
            upper_bound=b,
            calculation_metadata={"solver": "brent_hybrid"},
            warnings=["brent hybrid encountered unstable objective"],
        )

    if fa * fb > 0.0:
        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.BRENT,
            iterations=0,
            converged=False,
            residual=min(abs(fa), abs(fb)),
            final_pricing_error=min(abs(fa), abs(fb)),
            outcome=SolverOutcome.NON_CONVERGENCE,
            failure_reason=FailureReason.NO_BRACKETED_SOLUTION,
            lower_bound=a,
            upper_bound=b,
            calculation_metadata={"solver": "brent_hybrid"},
            warnings=["brent hybrid root not bracketed"],
        )

    if abs(fa) < abs(fb):
        a, b = b, a
        fa, fb = fb, fa

    c = a
    fc = fa
    d = b - a
    e = d

    for iteration in range(1, max_iterations + 1):
        if abs(fb) <= config.price_tolerance:
            return ImpliedVolatilityResult(
                implied_volatility=b,
                method=SolverMethod.BRENT,
                iterations=iteration,
                converged=True,
                residual=fb,
                final_pricing_error=fb,
                outcome=SolverOutcome.SUCCESS,
                failure_reason=FailureReason.NONE,
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
                calculation_metadata={"solver": "brent_hybrid"},
            )

        if fa * fb > 0.0:
            a = c
            fa = fc
            d = b - a
            e = d

        if abs(fa) < abs(fb):
            c = b
            b = a
            a = c
            fc = fb
            fb = fa
            fa = fc

        tol = 0.5 * config.volatility_tolerance
        midpoint = 0.5 * (a - b)
        if abs(midpoint) <= tol:
            return ImpliedVolatilityResult(
                implied_volatility=b,
                method=SolverMethod.BRENT,
                iterations=iteration,
                converged=True,
                residual=fb,
                final_pricing_error=fb,
                outcome=SolverOutcome.APPROXIMATE,
                failure_reason=FailureReason.NONE,
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
                calculation_metadata={"solver": "brent_hybrid", "approximate": True},
                warnings=["brent hybrid satisfied volatility tolerance"],
            )

        if abs(e) >= tol and abs(fc) > abs(fb):
            s = fb / fc
            if a == c:
                p = 2.0 * midpoint * s
                q = 1.0 - s
            else:
                q = fc / fa
                r = fb / fa
                p = s * (2.0 * midpoint * q * (q - r) - (b - c) * (r - 1.0))
                q = (q - 1.0) * (r - 1.0) * (s - 1.0)
            if p > 0.0:
                q = -q
            else:
                p = -p

            if 2.0 * p < min(3.0 * midpoint * q - abs(tol * q), abs(e * q)):
                e = d
                d = p / q
            else:
                d = midpoint
                e = midpoint
        else:
            d = midpoint
            e = midpoint

        c = b
        fc = fb
        if abs(d) > tol:
            b = b + d
        else:
            b = b + math.copysign(tol, midpoint)

        maybe_fb, reason_b = _evaluate_objective(objective, b)
        if maybe_fb is None:
            return ImpliedVolatilityResult(
                implied_volatility=None,
                method=SolverMethod.BRENT,
                iterations=iteration,
                converged=False,
                residual=float("inf"),
                final_pricing_error=None,
                outcome=SolverOutcome.NON_CONVERGENCE,
                failure_reason=reason_b,
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
                calculation_metadata={"solver": "brent_hybrid"},
                warnings=["brent hybrid objective became unstable"],
            )
        fb = maybe_fb

    return ImpliedVolatilityResult(
        implied_volatility=None,
        method=SolverMethod.BRENT,
        iterations=max_iterations,
        converged=False,
        residual=fb,
        final_pricing_error=fb,
        outcome=SolverOutcome.NON_CONVERGENCE,
        failure_reason=FailureReason.STALLED,
        lower_bound=config.vol_lower_bound,
        upper_bound=config.vol_upper_bound,
        calculation_metadata={"solver": "brent_hybrid"},
        warnings=["brent hybrid did not converge"],
    )
