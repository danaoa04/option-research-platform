"""Strategy-specific lifecycle policy library for deterministic research backtests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any

from .policies import (
    ConflictMode,
    ConflictResolutionResult,
    LifecyclePolicySignal,
    PolicyConflictResolver,
)


class PolicyFamily(StrEnum):
    ENTRY = "entry"
    EXIT = "exit"
    MANAGEMENT = "management"
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    ROLL = "roll"


@dataclass(slots=True, frozen=True)
class PolicyEvaluationDiagnostic:
    key: str
    observed: float | int | bool | str | None
    threshold: float | int | bool | str | None
    passed: bool
    reason_code: str


@dataclass(slots=True, frozen=True)
class PolicyEvaluationContext:
    strategy_identifier: str
    event_timestamp: datetime
    data_timestamp: datetime
    underlying_symbol: str
    dte: int | None = None
    pnl_pct: float | None = None
    absolute_delta: float | None = None
    iv_rank: float | None = None
    earnings_within_days: int | None = None
    in_dividend_window: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class PolicyEvaluationOutcome:
    policy_id: str
    policy_version: str
    family: PolicyFamily
    passed: bool
    reason_code: str
    observed_values: dict[str, float | int | bool | str | None]
    thresholds: dict[str, float | int | bool | str | None]
    diagnostics: tuple[PolicyEvaluationDiagnostic, ...]
    confidence: float
    data_timestamp: datetime
    required_data_present: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class StrategyPolicyDefinition:
    policy_id: str
    name: str
    family: PolicyFamily
    version: str
    priority: int
    parameters: dict[str, float | int | bool | str]
    required_data: tuple[str, ...]
    supported_strategies: tuple[str, ...]
    tags: tuple[str, ...] = ()
    deprecated: bool = False
    replacement_policy_id: str | None = None


@dataclass(slots=True, frozen=True)
class StrategyPolicyAlias:
    alias: str
    policy_id: str


@dataclass(slots=True, frozen=True)
class StrategyPolicySet:
    set_id: str
    set_version: str
    strategy_identifier: str
    conflict_mode: ConflictMode
    entry_policies: tuple[str, ...] = ()
    exit_policies: tuple[str, ...] = ()
    management_policies: tuple[str, ...] = ()
    earnings_policies: tuple[str, ...] = ()
    dividend_policies: tuple[str, ...] = ()
    roll_policies: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class PolicySetEvaluationResult:
    policy_set_id: str
    policy_set_version: str
    outcomes: tuple[PolicyEvaluationOutcome, ...]
    conflict_resolution: ConflictResolutionResult


class StrategyPolicyLibraryError(RuntimeError):
    """Raised when policy registry invariants are violated."""


class StrategyPolicyRegistry:
    def __init__(self) -> None:
        self._policies: dict[str, StrategyPolicyDefinition] = {}
        self._aliases: dict[str, str] = {}
        self._policy_sets: dict[tuple[str, str], StrategyPolicySet] = {}

    def register_policy(self, policy: StrategyPolicyDefinition) -> None:
        existing = self._policies.get(policy.policy_id)
        if existing is not None and existing.version != policy.version:
            raise StrategyPolicyLibraryError(
                f"policy '{policy.policy_id}' already registered with version '{existing.version}'"
            )
        self._policies[policy.policy_id] = policy

    def register_alias(self, alias: StrategyPolicyAlias) -> None:
        current = self._aliases.get(alias.alias)
        if current is not None and current != alias.policy_id:
            raise StrategyPolicyLibraryError(
                f"policy alias collision for '{alias.alias}' ({current} != {alias.policy_id})"
            )
        if alias.policy_id not in self._policies:
            raise StrategyPolicyLibraryError(f"unknown policy '{alias.policy_id}' for alias")
        self._aliases[alias.alias] = alias.policy_id

    def register_policy_set(self, policy_set: StrategyPolicySet) -> None:
        key = (policy_set.set_id, policy_set.set_version)
        if key in self._policy_sets:
            raise StrategyPolicyLibraryError(
                "policy set "
                f"'{policy_set.set_id}' version '{policy_set.set_version}' "
                "already exists"
            )
        for policy_name in self._policy_names_for_set(policy_set):
            self.resolve_policy(policy_name)
        self._policy_sets[key] = policy_set

    def discover_policies(
        self,
        *,
        family: PolicyFamily | None = None,
        include_deprecated: bool = False,
    ) -> tuple[StrategyPolicyDefinition, ...]:
        rows = sorted(self._policies.values(), key=lambda item: item.policy_id)
        if family is not None:
            rows = [item for item in rows if item.family is family]
        if not include_deprecated:
            rows = [item for item in rows if not item.deprecated]
        return tuple(rows)

    def discover_policy_sets(
        self,
        *,
        strategy_identifier: str | None = None,
    ) -> tuple[StrategyPolicySet, ...]:
        rows = sorted(
            self._policy_sets.values(),
            key=lambda item: (item.strategy_identifier, item.set_id),
        )
        if strategy_identifier is not None:
            rows = [item for item in rows if item.strategy_identifier == strategy_identifier]
        return tuple(rows)

    def resolve_policy(self, name: str) -> StrategyPolicyDefinition:
        key = self._aliases.get(name, name)
        policy = self._policies.get(key)
        if policy is None:
            raise StrategyPolicyLibraryError(f"unknown policy '{name}'")
        return policy

    def resolve_policy_set(self, *, set_id: str, set_version: str) -> StrategyPolicySet:
        key = (set_id, set_version)
        policy_set = self._policy_sets.get(key)
        if policy_set is None:
            raise StrategyPolicyLibraryError(
                f"unknown policy set '{set_id}' version '{set_version}'"
            )
        return policy_set

    def evaluate_policy(
        self,
        *,
        policy_name: str,
        context: PolicyEvaluationContext,
    ) -> PolicyEvaluationOutcome:
        policy = self.resolve_policy(policy_name)
        evaluator = _POLICY_EVALUATORS.get(policy.policy_id)
        if evaluator is None:
            raise StrategyPolicyLibraryError(f"no evaluator registered for '{policy.policy_id}'")
        return evaluator(policy=policy, context=context)

    def evaluate_policy_set(
        self,
        *,
        set_id: str,
        set_version: str,
        context: PolicyEvaluationContext,
    ) -> PolicySetEvaluationResult:
        policy_set = self.resolve_policy_set(set_id=set_id, set_version=set_version)
        policy_names = self._policy_names_for_set(policy_set)
        outcomes = tuple(
            self.evaluate_policy(policy_name=policy_name, context=context)
            for policy_name in policy_names
        )

        signals = tuple(
            LifecyclePolicySignal(
                policy_name=item.policy_id,
                signal="pass" if item.passed else "fail",
                disposition=_disposition_for_family(item.family),
                priority=self.resolve_policy(item.policy_id).priority,
                details={
                    "reason_code": item.reason_code,
                    "required_data_present": item.required_data_present,
                    "confidence": item.confidence,
                },
            )
            for item in outcomes
        )

        return PolicySetEvaluationResult(
            policy_set_id=policy_set.set_id,
            policy_set_version=policy_set.set_version,
            outcomes=outcomes,
            conflict_resolution=PolicyConflictResolver().resolve(
                signals=signals,
                mode=policy_set.conflict_mode,
            ),
        )

    @staticmethod
    def _policy_names_for_set(policy_set: StrategyPolicySet) -> tuple[str, ...]:
        return (
            *policy_set.entry_policies,
            *policy_set.exit_policies,
            *policy_set.management_policies,
            *policy_set.earnings_policies,
            *policy_set.dividend_policies,
            *policy_set.roll_policies,
        )


def _disposition_for_family(family: PolicyFamily) -> Any:
    if family in {PolicyFamily.EXIT, PolicyFamily.ROLL, PolicyFamily.EARNINGS}:
        from .policies import PolicyDisposition

        return PolicyDisposition.MANDATORY
    from .policies import PolicyDisposition

    return PolicyDisposition.ADVISORY


def _build_outcome(
    *,
    policy: StrategyPolicyDefinition,
    context: PolicyEvaluationContext,
    passed: bool,
    reason_code: str,
    observed: dict[str, float | int | bool | str | None],
    thresholds: dict[str, float | int | bool | str | None],
    required_data_present: bool,
) -> PolicyEvaluationOutcome:
    diagnostics = tuple(
        PolicyEvaluationDiagnostic(
            key=key,
            observed=observed.get(key),
            threshold=thresholds.get(key),
            passed=passed,
            reason_code=reason_code,
        )
        for key in sorted(set(observed) | set(thresholds))
    )
    return PolicyEvaluationOutcome(
        policy_id=policy.policy_id,
        policy_version=policy.version,
        family=policy.family,
        passed=passed,
        reason_code=reason_code,
        observed_values=observed,
        thresholds=thresholds,
        diagnostics=diagnostics,
        confidence=1.0 if required_data_present else 0.0,
        data_timestamp=context.data_timestamp,
        required_data_present=required_data_present,
        metadata={"strategy_identifier": context.strategy_identifier},
    )


def _evaluate_iv_rank_floor(
    *,
    policy: StrategyPolicyDefinition,
    context: PolicyEvaluationContext,
) -> PolicyEvaluationOutcome:
    minimum = float(policy.parameters.get("minimum", 0.0))
    observed = context.iv_rank
    required_data_present = observed is not None
    observed_value = float(observed) if observed is not None else None
    passed = observed_value is not None and observed_value >= minimum
    reason = "iv_rank_above_floor" if passed else "iv_rank_below_floor"
    return _build_outcome(
        policy=policy,
        context=context,
        passed=passed,
        reason_code=reason,
        observed={"iv_rank": observed_value},
        thresholds={"minimum": minimum},
        required_data_present=required_data_present,
    )


def _evaluate_profit_target(
    *,
    policy: StrategyPolicyDefinition,
    context: PolicyEvaluationContext,
) -> PolicyEvaluationOutcome:
    target = float(policy.parameters.get("target", 0.0))
    observed = context.pnl_pct
    required_data_present = observed is not None
    observed_value = float(observed) if observed is not None else None
    passed = observed_value is not None and observed_value >= target
    reason = "profit_target_hit" if passed else "profit_target_not_hit"
    return _build_outcome(
        policy=policy,
        context=context,
        passed=passed,
        reason_code=reason,
        observed={"pnl_pct": observed_value},
        thresholds={"target": target},
        required_data_present=required_data_present,
    )


def _evaluate_stop_loss(
    *,
    policy: StrategyPolicyDefinition,
    context: PolicyEvaluationContext,
) -> PolicyEvaluationOutcome:
    threshold = float(policy.parameters.get("threshold", -1.0))
    observed = context.pnl_pct
    required_data_present = observed is not None
    observed_value = float(observed) if observed is not None else None
    passed = observed_value is not None and observed_value <= threshold
    reason = "stop_loss_triggered" if passed else "stop_loss_not_triggered"
    return _build_outcome(
        policy=policy,
        context=context,
        passed=passed,
        reason_code=reason,
        observed={"pnl_pct": observed_value},
        thresholds={"threshold": threshold},
        required_data_present=required_data_present,
    )


def _evaluate_roll_dte_window(
    *,
    policy: StrategyPolicyDefinition,
    context: PolicyEvaluationContext,
) -> PolicyEvaluationOutcome:
    max_dte = int(policy.parameters.get("max_dte", 7))
    observed = context.dte
    required_data_present = observed is not None
    observed_value = int(observed) if observed is not None else None
    passed = observed_value is not None and observed_value <= max_dte
    reason = "roll_window_open" if passed else "roll_window_closed"
    return _build_outcome(
        policy=policy,
        context=context,
        passed=passed,
        reason_code=reason,
        observed={"dte": observed_value},
        thresholds={"max_dte": max_dte},
        required_data_present=required_data_present,
    )


def _evaluate_earnings_avoidance(
    *,
    policy: StrategyPolicyDefinition,
    context: PolicyEvaluationContext,
) -> PolicyEvaluationOutcome:
    min_days = int(policy.parameters.get("min_days", 2))
    observed = context.earnings_within_days
    required_data_present = observed is not None
    observed_value = int(observed) if observed is not None else None
    passed = observed_value is not None and observed_value > min_days
    reason = "earnings_window_clear" if passed else "earnings_window_blocked"
    return _build_outcome(
        policy=policy,
        context=context,
        passed=passed,
        reason_code=reason,
        observed={"earnings_within_days": observed_value},
        thresholds={"min_days": min_days},
        required_data_present=required_data_present,
    )


def _evaluate_dividend_avoidance(
    *,
    policy: StrategyPolicyDefinition,
    context: PolicyEvaluationContext,
) -> PolicyEvaluationOutcome:
    block_dividend_window = bool(policy.parameters.get("block_window", True))
    observed = context.in_dividend_window
    passed = (not observed) if block_dividend_window else True
    reason = "dividend_window_clear" if passed else "dividend_window_blocked"
    return _build_outcome(
        policy=policy,
        context=context,
        passed=passed,
        reason_code=reason,
        observed={"in_dividend_window": observed},
        thresholds={"block_window": block_dividend_window},
        required_data_present=True,
    )


def _evaluate_delta_roll(
    *,
    policy: StrategyPolicyDefinition,
    context: PolicyEvaluationContext,
) -> PolicyEvaluationOutcome:
    limit = float(policy.parameters.get("absolute_delta_limit", 0.35))
    observed = context.absolute_delta
    required_data_present = observed is not None
    observed_value = float(observed) if observed is not None else None
    passed = observed_value is not None and observed_value >= limit
    reason = "delta_roll_triggered" if passed else "delta_roll_not_triggered"
    return _build_outcome(
        policy=policy,
        context=context,
        passed=passed,
        reason_code=reason,
        observed={"absolute_delta": observed_value},
        thresholds={"absolute_delta_limit": limit},
        required_data_present=required_data_present,
    )


_POLICY_EVALUATORS = {
    "entry.iv_rank_floor": _evaluate_iv_rank_floor,
    "exit.profit_target": _evaluate_profit_target,
    "exit.stop_loss": _evaluate_stop_loss,
    "management.roll_dte_window": _evaluate_roll_dte_window,
    "earnings.avoid_near_event": _evaluate_earnings_avoidance,
    "dividend.avoid_ex_div_window": _evaluate_dividend_avoidance,
    "roll.delta_breach": _evaluate_delta_roll,
}


def default_strategy_policy_registry() -> StrategyPolicyRegistry:
    registry = StrategyPolicyRegistry()

    for policy in (
        StrategyPolicyDefinition(
            policy_id="entry.iv_rank_floor",
            name="Entry IV Rank Floor",
            family=PolicyFamily.ENTRY,
            version="8B-v1",
            priority=40,
            parameters={"minimum": 0.2},
            required_data=("iv_rank",),
            supported_strategies=(
                "covered.pmcc",
                "wheel.cash_secured_put",
                "vertical.bull_put_spread",
            ),
            tags=("entry", "volatility"),
        ),
        StrategyPolicyDefinition(
            policy_id="exit.profit_target",
            name="Exit Profit Target",
            family=PolicyFamily.EXIT,
            version="8B-v1",
            priority=10,
            parameters={"target": 0.4},
            required_data=("pnl_pct",),
            supported_strategies=(
                "covered.pmcc",
                "wheel.cash_secured_put",
                "vertical.bull_call_spread",
            ),
            tags=("exit",),
        ),
        StrategyPolicyDefinition(
            policy_id="exit.stop_loss",
            name="Exit Stop Loss",
            family=PolicyFamily.EXIT,
            version="8B-v1",
            priority=5,
            parameters={"threshold": -0.25},
            required_data=("pnl_pct",),
            supported_strategies=(
                "covered.pmcc",
                "wheel.cash_secured_put",
                "vertical.bull_call_spread",
            ),
            tags=("risk", "exit"),
        ),
        StrategyPolicyDefinition(
            policy_id="management.roll_dte_window",
            name="Management Roll DTE Window",
            family=PolicyFamily.MANAGEMENT,
            version="8B-v1",
            priority=30,
            parameters={"max_dte": 14},
            required_data=("dte",),
            supported_strategies=(
                "covered.pmcc",
                "calendar.call_calendar",
                "diagonal.call_diagonal",
            ),
            tags=("management", "roll"),
        ),
        StrategyPolicyDefinition(
            policy_id="earnings.avoid_near_event",
            name="Earnings Avoidance Window",
            family=PolicyFamily.EARNINGS,
            version="8B-v1",
            priority=1,
            parameters={"min_days": 2},
            required_data=("earnings_within_days",),
            supported_strategies=(
                "covered.pmcc",
                "wheel.cash_secured_put",
                "straddle.long_straddle",
            ),
            tags=("earnings",),
        ),
        StrategyPolicyDefinition(
            policy_id="dividend.avoid_ex_div_window",
            name="Dividend Avoidance Window",
            family=PolicyFamily.DIVIDEND,
            version="8B-v1",
            priority=15,
            parameters={"block_window": True},
            required_data=("dividend_calendar",),
            supported_strategies=("covered.pmcc",),
            tags=("dividend",),
        ),
        StrategyPolicyDefinition(
            policy_id="roll.delta_breach",
            name="Roll on Delta Breach",
            family=PolicyFamily.ROLL,
            version="8B-v1",
            priority=3,
            parameters={"absolute_delta_limit": 0.35},
            required_data=("absolute_delta",),
            supported_strategies=("covered.pmcc", "vertical.bull_put_spread", "iron.iron_condor"),
            tags=("roll", "risk"),
        ),
    ):
        registry.register_policy(policy)

    for alias in (
        StrategyPolicyAlias(alias="profit_target", policy_id="exit.profit_target"),
        StrategyPolicyAlias(alias="stop_loss", policy_id="exit.stop_loss"),
        StrategyPolicyAlias(alias="earnings_block", policy_id="earnings.avoid_near_event"),
        StrategyPolicyAlias(alias="delta_roll", policy_id="roll.delta_breach"),
    ):
        registry.register_alias(alias)

    registry.register_policy_set(
        StrategyPolicySet(
            set_id="pmcc_core",
            set_version="8B-v1",
            strategy_identifier="covered.pmcc",
            conflict_mode=ConflictMode.PRIORITY_ORDERING,
            entry_policies=("entry.iv_rank_floor",),
            exit_policies=("exit.profit_target", "exit.stop_loss"),
            management_policies=("management.roll_dte_window",),
            earnings_policies=("earnings.avoid_near_event",),
            dividend_policies=("dividend.avoid_ex_div_window",),
            roll_policies=("roll.delta_breach",),
            metadata={"sprint": "8B", "compatibility": "8A-preserving"},
        )
    )

    registry.register_policy_set(
        StrategyPolicySet(
            set_id="wheel_core",
            set_version="8B-v1",
            strategy_identifier="wheel.cash_secured_put",
            conflict_mode=ConflictMode.PRIORITY_ORDERING,
            entry_policies=("entry.iv_rank_floor",),
            exit_policies=("exit.profit_target", "exit.stop_loss"),
            earnings_policies=("earnings.avoid_near_event",),
            metadata={"sprint": "8B", "compatibility": "8A-preserving"},
        )
    )

    return registry


def deterministic_strategy_policy_checksum(
    *,
    policies: tuple[StrategyPolicyDefinition, ...],
    policy_sets: tuple[StrategyPolicySet, ...],
) -> str:
    payload = {
        "policies": [
            {
                "policy_id": item.policy_id,
                "family": item.family.value,
                "version": item.version,
                "priority": item.priority,
                "parameters": dict(sorted(item.parameters.items(), key=lambda row: row[0])),
            }
            for item in sorted(policies, key=lambda row: row.policy_id)
        ],
        "policy_sets": [
            {
                "set_id": item.set_id,
                "set_version": item.set_version,
                "strategy_identifier": item.strategy_identifier,
                "conflict_mode": item.conflict_mode.value,
                "entry_policies": item.entry_policies,
                "exit_policies": item.exit_policies,
                "management_policies": item.management_policies,
                "earnings_policies": item.earnings_policies,
                "dividend_policies": item.dividend_policies,
                "roll_policies": item.roll_policies,
            }
            for item in sorted(policy_sets, key=lambda row: (row.set_id, row.set_version))
        ],
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()


def policy_set_api_payload(policy_set: StrategyPolicySet) -> dict[str, Any]:
    return {
        "set_id": policy_set.set_id,
        "set_version": policy_set.set_version,
        "strategy_identifier": policy_set.strategy_identifier,
        "conflict_mode": policy_set.conflict_mode.value,
        "entry_policies": list(policy_set.entry_policies),
        "exit_policies": list(policy_set.exit_policies),
        "management_policies": list(policy_set.management_policies),
        "earnings_policies": list(policy_set.earnings_policies),
        "dividend_policies": list(policy_set.dividend_policies),
        "roll_policies": list(policy_set.roll_policies),
        "metadata": dict(policy_set.metadata),
    }


def now_utc() -> datetime:
    return datetime.now(tz=UTC)
