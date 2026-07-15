"""Broker-neutral itemized fee and commission model for research execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .execution import ExecutionRequest


@dataclass(slots=True, frozen=True)
class FeeItem:
    fee_type: str
    amount: float
    currency: str = "USD"


@dataclass(slots=True, frozen=True)
class FeeModelRequest:
    request: ExecutionRequest
    filled_quantity: int
    fill_price: float | None


@dataclass(slots=True)
class ItemizedFeeModel:
    def calculate(self, request: FeeModelRequest) -> tuple[FeeItem, ...]:
        qty = max(0, request.filled_quantity)
        policy = request.request.commission_policy
        exchange_policy = request.request.exchange_fee_policy

        per_contract = float(policy.get("per_contract", 0.0)) * qty
        per_order = float(policy.get("per_order", 0.0))
        stock_commission = float(policy.get("stock_commission", 0.0))
        minimum_ticket = float(policy.get("minimum_ticket", 0.0))
        cap_max = policy.get("maximum_fee_cap")
        cap_min = policy.get("minimum_fee_cap")

        exchange_fee = float(exchange_policy.get("exchange_fee", 0.0)) * qty
        regulatory_fee = float(exchange_policy.get("regulatory_fee", 0.0)) * qty
        clearing_fee = float(exchange_policy.get("clearing_fee", 0.0)) * qty

        exercise_fee = float(policy.get("exercise_fee", 0.0))
        assignment_fee = float(policy.get("assignment_fee", 0.0))

        base = per_contract + per_order + stock_commission
        if qty > 0:
            base = max(base, minimum_ticket)
        if cap_min is not None:
            base = max(base, float(cap_min))
        if cap_max is not None:
            base = min(base, float(cap_max))

        return (
            FeeItem("commission", round(base, 8)),
            FeeItem("exchange_fee", round(exchange_fee, 8)),
            FeeItem("regulatory_fee", round(regulatory_fee, 8)),
            FeeItem("clearing_fee", round(clearing_fee, 8)),
            FeeItem("exercise_fee", round(exercise_fee, 8)),
            FeeItem("assignment_fee", round(assignment_fee, 8)),
        )
