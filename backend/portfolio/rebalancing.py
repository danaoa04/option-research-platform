"""Research-level rebalance policies and reason codes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import PortfolioAllocation, RebalanceChange, RebalancePlan, RebalanceTrigger


@dataclass(slots=True)
class RebalanceEngine:
    drift_threshold: float = 0.05

    def plan(
        self,
        *,
        as_of: date,
        previous: tuple[PortfolioAllocation, ...],
        target: tuple[PortfolioAllocation, ...],
        trigger: RebalanceTrigger,
    ) -> RebalancePlan:
        previous_map = {item.candidate_id: item.weight for item in previous}
        target_map = {item.candidate_id: item.weight for item in target}
        candidate_ids = sorted(set(previous_map) | set(target_map))
        changes: list[RebalanceChange] = []

        for candidate_id in candidate_ids:
            previous_weight = previous_map.get(candidate_id, 0.0)
            target_weight = target_map.get(candidate_id, 0.0)
            delta_weight = target_weight - previous_weight
            reason_codes: list[RebalanceTrigger] = [trigger]
            if abs(delta_weight) >= self.drift_threshold:
                reason_codes.append(RebalanceTrigger.THRESHOLD_DRIFT)
            if previous_weight > 0.0 and target_weight == 0.0:
                reason_codes.append(RebalanceTrigger.LIFECYCLE_COMPLETION)
            changes.append(
                RebalanceChange(
                    candidate_id=candidate_id,
                    previous_weight=previous_weight,
                    target_weight=target_weight,
                    delta_weight=delta_weight,
                    reason_codes=tuple(dict.fromkeys(reason_codes)),
                )
            )

        warnings: tuple[str, ...] = ()
        if not changes:
            warnings = ("no rebalance changes",)
        return RebalancePlan(
            as_of=as_of,
            trigger=trigger,
            changes=tuple(changes),
            warnings=warnings,
        )
