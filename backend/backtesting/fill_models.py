"""Deterministic research fill model engine with slippage and partial-fill support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from .quote_selection import QuoteSelectionResult

if TYPE_CHECKING:
    from .execution import ExecutionRequest


@dataclass(slots=True, frozen=True)
class FillModelRequest:
    request: ExecutionRequest
    quote: dict[str, Any] | None
    diagnostics: QuoteSelectionResult
    policy_name: str


@dataclass(slots=True, frozen=True)
class FillModelResult:
    requested_quantity: int
    filled_quantity: int
    remaining_quantity: int
    fill_price: float | None
    fill_timestamp: datetime | None
    fill_model: str
    slippage: float
    spread_capture: float | None
    quote_quality: float
    warnings: tuple[str, ...]
    failure_reason: str | None


@dataclass(slots=True)
class ResearchFillModelEngine:
    default_vol_sensitivity: float = 0.02
    default_liquidity_sensitivity: float = 0.05

    def fill(self, req: FillModelRequest) -> FillModelResult:
        policy = req.request.fill_model_policy
        quote = req.quote
        if quote is None:
            return FillModelResult(
                requested_quantity=req.request.quantity,
                filled_quantity=0,
                remaining_quantity=req.request.quantity,
                fill_price=None,
                fill_timestamp=None,
                fill_model=req.policy_name,
                slippage=0.0,
                spread_capture=None,
                quote_quality=0.0,
                warnings=("no_quote",),
                failure_reason="missing_quote",
            )

        mode = str(policy.get("mode", req.policy_name))
        selected_price = req.diagnostics.selected_price
        if selected_price is None:
            return FillModelResult(
                requested_quantity=req.request.quantity,
                filled_quantity=0,
                remaining_quantity=req.request.quantity,
                fill_price=None,
                fill_timestamp=quote.get("timestamp"),
                fill_model=mode,
                slippage=0.0,
                spread_capture=None,
                quote_quality=0.0,
                warnings=("price_unavailable",),
                failure_reason="price_unavailable",
            )

        spread = req.diagnostics.spread_width or 0.0
        vol = float(quote.get("iv", quote.get("implied_volatility", 0.0)) or 0.0)
        liq = float(quote.get("liquidity_score", 1.0) or 1.0)
        base_slippage = float(req.request.slippage_policy.get("fixed_per_contract", 0.0))
        pct_slip = float(req.request.slippage_policy.get("percent_of_price", 0.0))
        spread_slip = (
            float(req.request.slippage_policy.get("spread_width_multiplier", 0.0)) * spread
        )
        vol_slip = (
            float(
                req.request.slippage_policy.get(
                    "volatility_sensitivity",
                    self.default_vol_sensitivity,
                )
            )
            * vol
        )
        liq_slip = float(
            req.request.slippage_policy.get(
                "liquidity_sensitivity",
                self.default_liquidity_sensitivity,
            )
        ) * max(0.0, 1.0 - liq)

        slippage = base_slippage + pct_slip * selected_price + spread_slip + vol_slip + liq_slip
        signed = slippage if req.request.side.value == "buy" else -slippage
        raw_fill = max(0.0, selected_price + signed)

        requested_qty = max(0, req.request.quantity)
        fill_ratio = float(policy.get("fill_ratio", 1.0))
        min_fill = max(0, req.request.minimum_fill_quantity)
        filled = int(requested_qty * max(0.0, min(1.0, fill_ratio)))
        if filled and filled < min_fill:
            filled = 0
        if req.request.all_or_none_research and filled not in {0, requested_qty}:
            filled = 0

        reason: str | None = None
        warnings: list[str] = list(req.diagnostics.quality_flags)
        if mode == "no_fill":
            filled = 0
            reason = "policy_no_fill"
        if filled == 0 and reason is None:
            reason = "insufficient_liquidity"

        remaining = max(0, requested_qty - filled)
        spread_capture = None if spread <= 0 else (spread * 0.5 - abs(slippage))
        quality = max(0.0, 1.0 - min(1.0, (req.diagnostics.quote_age_seconds or 0.0) / 600.0))

        return FillModelResult(
            requested_quantity=requested_qty,
            filled_quantity=filled,
            remaining_quantity=remaining,
            fill_price=raw_fill if filled > 0 else None,
            fill_timestamp=quote.get("timestamp"),
            fill_model=mode,
            slippage=slippage,
            spread_capture=spread_capture,
            quote_quality=quality,
            warnings=tuple(warnings),
            failure_reason=reason,
        )
