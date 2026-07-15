"""Tree-resolution escalation policy for American model diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from backend.pricing import PricingEngine, PricingRequest
from backend.pricing.models import PricingModelName

from .models import SolverConfig, TreeStepDiagnostic, TreeStepPolicyResult


@dataclass(slots=True)
class TreeResolutionPolicy:
    """Escalate American tree steps and evaluate convergence diagnostics."""

    pricing_engine: PricingEngine

    def evaluate(
        self,
        request: PricingRequest,
        model_name: PricingModelName,
        implied_volatility: float,
        config: SolverConfig,
    ) -> TreeStepPolicyResult:
        base_steps = max(config.tree_step_start, request.tree_steps)
        steps: list[int] = []
        for multiplier in config.tree_step_schedule:
            candidate = base_steps * max(multiplier, 1)
            if candidate <= config.tree_step_max:
                steps.append(candidate)
        if not steps:
            steps = [min(base_steps, config.tree_step_max)]

        diagnostics: list[TreeStepDiagnostic] = []
        prev: TreeStepDiagnostic | None = None

        for step_count in steps:
            price, delta, gamma = self._price_and_greeks(
                request=request,
                model_name=model_name,
                implied_volatility=implied_volatility,
                tree_steps=step_count,
            )
            row = TreeStepDiagnostic(tree_steps=step_count, price=price, delta=delta, gamma=gamma)
            if prev is not None:
                price_change = abs(price - prev.price)
                delta_change = abs(delta - prev.delta)
                gamma_change = abs(gamma - prev.gamma)
                iv_change_proxy = price_change / max(
                    abs(_vega_proxy(price, implied_volatility)),
                    1e-8,
                )
                row = TreeStepDiagnostic(
                    tree_steps=step_count,
                    price=price,
                    delta=delta,
                    gamma=gamma,
                    price_change=price_change,
                    delta_change=delta_change,
                    gamma_change=gamma_change,
                    iv_change_proxy=iv_change_proxy,
                )
            diagnostics.append(row)
            prev = row

        selected = diagnostics[-1]
        converged = False
        for row in diagnostics[1:]:
            if (
                (row.price_change or float("inf")) <= config.tree_price_convergence_threshold
                and (row.iv_change_proxy or float("inf")) <= config.tree_iv_convergence_threshold
                and max(row.delta_change or 0.0, row.gamma_change or 0.0)
                <= config.tree_greek_stability_threshold
            ):
                selected = row
                converged = True
                break

        warnings: list[str] = []
        if not converged:
            warnings.append("tree resolution did not converge within configured escalation bounds")

        return TreeStepPolicyResult(
            selected_tree_steps=selected.tree_steps,
            converged=converged,
            diagnostics=tuple(diagnostics),
            warnings=tuple(warnings),
        )

    def _price_and_greeks(
        self,
        *,
        request: PricingRequest,
        model_name: PricingModelName,
        implied_volatility: float,
        tree_steps: int,
    ) -> tuple[float, float, float]:
        center = _with_params(request, implied_volatility=implied_volatility, tree_steps=tree_steps)
        up = _with_params(
            request,
            implied_volatility=implied_volatility,
            tree_steps=tree_steps,
            spot_shift=0.5,
        )
        down = _with_params(
            request,
            implied_volatility=implied_volatility,
            tree_steps=tree_steps,
            spot_shift=-0.5,
        )

        center_price = self.pricing_engine.price(center, model_name=model_name).option_value
        up_price = self.pricing_engine.price(up, model_name=model_name).option_value
        down_price = self.pricing_engine.price(down, model_name=model_name).option_value

        delta = (up_price - down_price) / max(up.spot - down.spot, 1e-8)
        gamma = (up_price - 2.0 * center_price + down_price) / max((0.5) ** 2, 1e-8)
        return center_price, delta, gamma


def _with_params(
    request: PricingRequest,
    *,
    implied_volatility: float,
    tree_steps: int,
    spot_shift: float = 0.0,
) -> PricingRequest:
    return PricingRequest(
        spot=max(request.spot + spot_shift, 1e-8),
        strike=request.strike,
        expiry=request.expiry,
        volatility=implied_volatility,
        risk_free_rate=request.risk_free_rate,
        dividend_yield=request.dividend_yield,
        option_type=request.option_type,
        exercise_style=request.exercise_style,
        multiplier=request.multiplier,
        valuation_date=request.valuation_date,
        settlement_type=request.settlement_type,
        underlying_type=request.underlying_type,
        currency=request.currency,
        discrete_dividends=request.discrete_dividends,
        futures_price=request.futures_price,
        tree_steps=tree_steps,
        contract_symbol=request.contract_symbol,
    )


def _vega_proxy(price: float, implied_volatility: float) -> float:
    # Keep a deterministic proxy when model vega is not available for American trees.
    return max(abs(price), 1.0) * max(implied_volatility, 1e-4)
