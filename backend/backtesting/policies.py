"""Lifecycle policy evaluation and deterministic conflict resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PolicyDisposition(StrEnum):
    MANDATORY = "mandatory"
    ADVISORY = "advisory"


class ConflictMode(StrEnum):
    FIRST_MATCH = "first_match"
    PRIORITY_ORDERING = "priority_ordering"
    ALL_MATCH_DIAGNOSTICS = "all_match_diagnostics"


@dataclass(slots=True, frozen=True)
class LifecyclePolicySignal:
    policy_name: str
    signal: str
    disposition: PolicyDisposition
    priority: int
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ConflictResolutionResult:
    winning_signal: LifecyclePolicySignal | None
    matched_signals: tuple[LifecyclePolicySignal, ...]
    diagnostics: tuple[str, ...]


class PolicyConflictResolver:
    def resolve(
        self,
        *,
        signals: tuple[LifecyclePolicySignal, ...],
        mode: ConflictMode,
    ) -> ConflictResolutionResult:
        if not signals:
            return ConflictResolutionResult(
                winning_signal=None,
                matched_signals=(),
                diagnostics=("no_signals",),
            )

        mandatory = [item for item in signals if item.disposition is PolicyDisposition.MANDATORY]
        advisory = [item for item in signals if item.disposition is PolicyDisposition.ADVISORY]
        chosen: LifecyclePolicySignal | None

        if mode is ConflictMode.FIRST_MATCH:
            chosen = signals[0]
        elif mode is ConflictMode.PRIORITY_ORDERING:
            pool = mandatory if mandatory else advisory
            chosen = sorted(pool, key=lambda item: item.priority)[0]
        else:
            pool = mandatory if mandatory else advisory
            chosen = sorted(pool, key=lambda item: item.priority)[0]

        diagnostics = [
            f"matched={item.policy_name}:{item.signal}:{item.disposition.value}"
            for item in sorted(signals, key=lambda row: (row.priority, row.policy_name))
        ]
        return ConflictResolutionResult(
            winning_signal=chosen,
            matched_signals=tuple(signals),
            diagnostics=tuple(diagnostics),
        )
