"""Strategy rolling, adjustment, conversion, and management comparison foundations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any


class RollPolicyStatus(StrEnum):
    MANDATORY = "mandatory"
    ADVISORY = "advisory"


class RollLifecycleState(StrEnum):
    WAITING_FOR_ENTRY = "waiting_for_entry"
    OPEN = "open"
    MANAGED = "managed"
    ROLL_PENDING = "roll_pending"
    PARTIAL_ROLL = "partial_roll"
    CLOSED = "closed"


class RollType(StrEnum):
    ROLL_OUT = "roll_out"
    ROLL_IN = "roll_in"
    ROLL_UP = "roll_up"
    ROLL_DOWN = "roll_down"
    ROLL_UP_AND_OUT = "roll_up_and_out"
    ROLL_DOWN_AND_OUT = "roll_down_and_out"
    ROLL_FOR_CREDIT = "roll_for_credit"
    ROLL_FOR_DEBIT_WITHIN_CAP = "roll_for_debit_within_cap"
    CLOSE_AND_REOPEN = "close_and_reopen"
    SINGLE_LEG_ROLL = "single_leg_roll"
    SHORT_LEG_ONLY_ROLL = "short_leg_only_roll"
    LONG_LEG_ONLY_ROLL = "long_leg_only_roll"
    ENTIRE_POSITION_ROLL = "entire_position_roll"
    TESTED_SIDE_ROLL = "tested_side_roll"
    UNTESTED_SIDE_ROLL = "untested_side_roll"
    BODY_ROLL = "body_roll"
    WING_ROLL = "wing_roll"
    RATIO_ADJUSTMENT = "ratio_adjustment"
    QUANTITY_REDUCTION = "quantity_reduction"
    QUANTITY_INCREASE = "quantity_increase"
    EXPIRATION_LADDERING = "expiration_laddering"


class ManagementAction(StrEnum):
    HOLD = "hold"
    CLOSE = "close"
    ROLL = "roll"
    ADJUST = "adjust"
    CONVERT = "convert"
    REDUCE = "reduce"
    HEDGE = "hedge"
    ACCEPT_ASSIGNMENT = "accept_assignment"
    EXERCISE = "exercise"
    DO_NOTHING = "do_nothing"


@dataclass(slots=True, frozen=True)
class RollPolicyDefinition:
    canonical_identifier: str
    aliases: tuple[str, ...]
    version: str
    supported_strategy_families: tuple[str, ...]
    supported_lifecycle_states: tuple[RollLifecycleState, ...]
    supported_exercise_styles: tuple[str, ...]
    supported_settlement_types: tuple[str, ...]
    required_market_data: tuple[str, ...]
    required_volatility_data: tuple[str, ...]
    parameter_schema: dict[str, Any]
    default_priority: int
    status: RollPolicyStatus
    plugin_namespace: str | None = None
    deprecated: bool = False
    replacement_identifier: str | None = None
    known_limitations: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class RollPolicyRegistrySnapshot:
    policies: tuple[RollPolicyDefinition, ...]
    created_at: datetime
    checksum: str


class StrategyManagementError(RuntimeError):
    """Raised when management planning invariants are violated."""


class RollPolicyRegistry:
    def __init__(self) -> None:
        self._policies: dict[str, RollPolicyDefinition] = {}
        self._aliases: dict[str, str] = {}

    def register_policy(self, definition: RollPolicyDefinition) -> None:
        existing = self._policies.get(definition.canonical_identifier)
        if existing is not None and existing.version != definition.version:
            raise StrategyManagementError(
                f"roll policy version collision for '{definition.canonical_identifier}'"
            )
        self._policies[definition.canonical_identifier] = definition
        for alias in definition.aliases:
            current = self._aliases.get(alias)
            if current is not None and current != definition.canonical_identifier:
                raise StrategyManagementError(f"roll policy alias collision '{alias}' ({current})")
            self._aliases[alias] = definition.canonical_identifier

    def register_plugin_policies(
        self,
        *,
        plugin_namespace: str,
        policies: tuple[RollPolicyDefinition, ...],
    ) -> None:
        for definition in policies:
            if definition.plugin_namespace != plugin_namespace:
                raise StrategyManagementError(
                    "plugin namespace mismatch for roll policy registration"
                )
            self.register_policy(definition)

    def resolve(self, name: str) -> RollPolicyDefinition:
        key = self._aliases.get(name, name)
        definition = self._policies.get(key)
        if definition is None:
            raise StrategyManagementError(f"unknown roll policy '{name}'")
        return definition

    def discover(
        self,
        *,
        include_deprecated: bool = False,
    ) -> tuple[RollPolicyDefinition, ...]:
        rows = sorted(
            self._policies.values(),
            key=lambda item: (item.default_priority, item.canonical_identifier),
        )
        if include_deprecated:
            return tuple(rows)
        return tuple(item for item in rows if not item.deprecated)

    def snapshot(self) -> RollPolicyRegistrySnapshot:
        policies = self.discover(include_deprecated=True)
        checksum = deterministic_roll_policy_checksum(policies=policies)
        return RollPolicyRegistrySnapshot(
            policies=policies,
            created_at=datetime.now(tz=UTC),
            checksum=checksum,
        )


@dataclass(slots=True, frozen=True)
class RollLegSelection:
    leg_label: str
    contract_id: str
    quantity: int
    expiration: datetime
    strike: float | None
    delta: float | None
    premium: float | None
    bid: float | None
    ask: float | None
    liquidity_score: float | None
    quote_quality: float | None


@dataclass(slots=True, frozen=True)
class RollRequest:
    strategy_identifier: str
    strategy_instance_id: str
    position_identifier: str
    selected_source_legs: tuple[RollLegSelection, ...]
    preserved_legs: tuple[RollLegSelection, ...]
    close_quantity: int
    target_quantity: int
    target_expiration_policy: str
    target_strike_policy: str
    target_delta: float | None
    target_dte: int | None
    target_premium: float | None
    credit_or_debit_requirement: str | None
    maximum_debit: float | None
    minimum_credit: float | None
    maximum_cumulative_roll_debit: float | None
    minimum_expected_improvement: float
    liquidity_threshold: float
    quote_quality_threshold: float
    margin_policy: dict[str, Any]
    execution_policy: dict[str, Any]
    requested_timestamp: datetime
    trigger: str
    reason_code: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RollTargetCandidate:
    candidate_id: str
    target_legs: tuple[RollLegSelection, ...]
    roll_type: RollType
    target_expiration: datetime | None
    target_strike: float | None
    target_delta: float | None
    target_dte: int | None
    estimated_closing_cost: float | None
    estimated_opening_proceeds: float | None
    estimated_net_credit_or_debit: float | None
    fees: float
    liquidity_score: float
    quality_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class EligibilityRejection:
    code: str
    message: str
    observed: float | int | bool | str | None
    threshold: float | int | bool | str | None


@dataclass(slots=True, frozen=True)
class RollEligibilityEvaluation:
    eligible: bool
    rejections: tuple[EligibilityRejection, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ImprovementComponent:
    name: str
    weight: float
    observed_before: float | None
    observed_after: float | None
    contribution: float
    explanation: str


@dataclass(slots=True, frozen=True)
class ExpectedImprovementAssessment:
    total_score: float
    components: tuple[ImprovementComponent, ...]
    model_based: bool = True
    guarantee: str = "not_guaranteed"


@dataclass(slots=True, frozen=True)
class RollPlan:
    plan_id: str
    request: RollRequest
    selected_candidate: RollTargetCandidate
    source_legs_to_close: tuple[RollLegSelection, ...]
    target_legs_to_open: tuple[RollLegSelection, ...]
    preserved_legs: tuple[RollLegSelection, ...]
    proposed_quantities: dict[str, int]
    estimated_closing_cost: float | None
    estimated_opening_proceeds: float | None
    estimated_net_credit_or_debit: float | None
    fees: float
    estimated_post_roll_basis: float | None
    target_dte: int | None
    target_strike: float | None
    target_delta: float | None
    pre_roll_greeks: dict[str, float]
    post_roll_greeks: dict[str, float]
    pre_roll_margin: float | None
    post_roll_margin: float | None
    pre_roll_capital_usage: float | None
    post_roll_capital_usage: float | None
    expected_improvement: ExpectedImprovementAssessment
    liquidity_diagnostics: dict[str, Any]
    data_quality_diagnostics: dict[str, Any]
    assignment_risk_diagnostics: dict[str, Any]
    dividend_risk_diagnostics: dict[str, Any]
    warnings: tuple[str, ...]
    eligibility: RollEligibilityEvaluation
    reproducibility_metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RollExecutionIntent:
    intent_id: str
    plan_id: str
    execution_style: str
    all_or_none_research: bool
    sequential_legging: bool
    requested_net_price: float | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class PartialRollState:
    state_id: str
    plan_id: str
    one_source_leg_closed_target_failed: bool
    partial_close: bool
    partial_target_fill: bool
    preserved_legs: tuple[str, ...]
    residual_quantities: dict[str, int]
    temporary_naked_exposure: bool
    timeout_seconds: float
    risk_escalated: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RollReconciliation:
    reconciliation_id: str
    plan_id: str
    status: str
    retry_scheduled: bool
    cancel_scheduled: bool
    fallback_close_scheduled: bool
    state_transition: str
    recorded_temporary_exposure: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class BasisTrackingResult:
    original_basis: float
    cumulative_credits: float
    cumulative_debits: float
    fees: float
    closing_pnl: float
    target_leg_basis: float
    preserved_leg_basis: float
    new_strategy_cycle_basis: float
    realized_pnl: float
    unrealized_pnl: float
    cost_basis_transfer: float
    cumulative_short_premium_income: float
    cumulative_roll_cost: float
    post_assignment_or_exercise_basis: float | None


@dataclass(slots=True, frozen=True)
class ConversionPlan:
    conversion_id: str
    source_strategy: str
    target_strategy: str
    legs_closed: tuple[RollLegSelection, ...]
    legs_preserved: tuple[RollLegSelection, ...]
    legs_opened: tuple[RollLegSelection, ...]
    structural_rationale: str
    risk_before: dict[str, Any]
    risk_after: dict[str, Any]
    payoff_before: dict[str, Any]
    payoff_after: dict[str, Any]
    margin_before: float | None
    margin_after: float | None
    basis_before: float | None
    basis_after: float | None
    execution_estimate: dict[str, Any]
    conversion_cost: float | None
    compatible: bool
    warnings: tuple[str, ...]
    reproducibility_metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ManagementPathAlternative:
    action: ManagementAction
    immediate_cost: float | None
    projected_pnl_distribution: dict[str, float]
    expected_value: float | None
    probability_of_profit: float | None
    greeks: dict[str, float]
    margin: float | None
    buying_power: float | None
    tail_risk: float | None
    assignment_risk: float | None
    dividend_risk: float | None
    liquidity: float | None
    expected_holding_period_days: float | None
    complexity: float
    data_quality: float
    confidence: float
    warnings: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class ManagementComparison:
    comparison_id: str
    strategy_instance_id: str
    alternatives: tuple[ManagementPathAlternative, ...]
    selected_action: ManagementAction
    model_based: bool = True
    guarantee: str = "not_guaranteed"


@dataclass(slots=True, frozen=True)
class RollAnalyticsSummary:
    roll_count: int
    roll_frequency: float
    average_credit: float
    average_debit: float
    cumulative_roll_credit: float
    cumulative_roll_debit: float
    fees: float
    average_dte_extension: float
    average_strike_move: float
    average_delta_change: float
    theta_change: float
    vega_change: float
    gamma_change: float
    margin_change: float
    buying_power_change: float
    win_rate_after_roll: float


@dataclass(slots=True, frozen=True)
class ConversionAnalyticsSummary:
    conversion_count: int
    conversion_cost: float
    basis_change: float
    risk_reduction: float
    margin_change: float
    expected_value_change: float
    probability_of_profit_change: float
    tail_risk_change: float
    success_rate: float
    failure_rate: float
    reversal_rate: float
    average_time_to_close_days: float


def deterministic_roll_policy_checksum(
    *,
    policies: tuple[RollPolicyDefinition, ...],
) -> str:
    payload = [
        {
            "id": item.canonical_identifier,
            "version": item.version,
            "status": item.status.value,
            "priority": item.default_priority,
        }
        for item in sorted(policies, key=lambda row: row.canonical_identifier)
    ]
    return sha256(repr(payload).encode("utf-8")).hexdigest()


class RollTargetSelector:
    def next_weekly(self, expirations: tuple[datetime, ...], as_of: datetime) -> datetime | None:
        future = [item for item in expirations if item > as_of]
        if not future:
            return None
        ordered = sorted(future)
        return ordered[0]

    def next_monthly(self, expirations: tuple[datetime, ...], as_of: datetime) -> datetime | None:
        future = [item for item in expirations if item > as_of]
        if not future:
            return None
        ordered = sorted(future)
        for item in ordered:
            if 15 <= item.day <= 21:
                return item
        return ordered[0]

    def nearest_target_dte(
        self,
        expirations: tuple[datetime, ...],
        as_of: datetime,
        target_dte: int,
    ) -> datetime | None:
        future = [item for item in expirations if item > as_of]
        if not future:
            return None
        return min(
            future,
            key=lambda item: abs((item.date() - as_of.date()).days - target_dte),
        )

    def same_strike(
        self,
        strikes: tuple[float, ...],
        source_strike: float,
    ) -> float | None:
        if source_strike in strikes:
            return source_strike
        return None

    def nearest_strike(
        self,
        strikes: tuple[float, ...],
        target_strike: float,
    ) -> float | None:
        if not strikes:
            return None
        return min(strikes, key=lambda item: abs(item - target_strike))

    def target_delta(
        self,
        deltas: tuple[float, ...],
        target_delta: float,
    ) -> float | None:
        if not deltas:
            return None
        return min(deltas, key=lambda item: abs(item - target_delta))


class RollEligibilityGuard:
    def evaluate(
        self,
        *,
        request: RollRequest,
        candidate: RollTargetCandidate,
        roll_count: int,
        cumulative_debit: float,
        max_roll_count: int,
        cooldown_passed: bool,
        min_time_since_prior_roll_passed: bool,
        target_contract_available: bool,
        target_quote_available: bool,
        acceptable_quote_age: bool,
        acceptable_spread: bool,
        acceptable_fill_confidence: bool,
        margin_compatible: bool,
        buying_power_available: bool,
        no_conflicting_corporate_action: bool,
        no_unsupported_contract_adjustment: bool,
        assignment_risk_compatible: bool,
        dividend_risk_compatible: bool,
        event_risk_allowed: bool,
        no_look_ahead_compliant: bool,
    ) -> RollEligibilityEvaluation:
        rejections: list[EligibilityRejection] = []

        if candidate.target_expiration is None:
            rejections.append(
                EligibilityRejection(
                    code="invalid_target_expiration",
                    message="target expiration is missing",
                    observed=None,
                    threshold=None,
                )
            )
        if candidate.target_strike is None and request.target_strike_policy != "target_delta":
            rejections.append(
                EligibilityRejection(
                    code="invalid_target_strike",
                    message="target strike is missing",
                    observed=None,
                    threshold=None,
                )
            )
        if not target_contract_available:
            rejections.append(
                EligibilityRejection(
                    code="target_contract_unavailable",
                    message="target contract is unavailable",
                    observed=False,
                    threshold=True,
                )
            )
        if not target_quote_available:
            rejections.append(
                EligibilityRejection(
                    code="target_quote_unavailable",
                    message="target quote is unavailable",
                    observed=False,
                    threshold=True,
                )
            )
        if not acceptable_quote_age:
            rejections.append(
                EligibilityRejection(
                    code="quote_age_unacceptable",
                    message="quote is stale",
                    observed=False,
                    threshold=True,
                )
            )
        if candidate.liquidity_score < request.liquidity_threshold:
            rejections.append(
                EligibilityRejection(
                    code="minimum_liquidity_not_met",
                    message="liquidity below threshold",
                    observed=candidate.liquidity_score,
                    threshold=request.liquidity_threshold,
                )
            )
        if candidate.quality_score < request.quote_quality_threshold:
            rejections.append(
                EligibilityRejection(
                    code="quote_quality_not_met",
                    message="quote quality below threshold",
                    observed=candidate.quality_score,
                    threshold=request.quote_quality_threshold,
                )
            )
        if not acceptable_spread:
            rejections.append(
                EligibilityRejection(
                    code="spread_width_unacceptable",
                    message="spread width unacceptable",
                    observed=False,
                    threshold=True,
                )
            )
        if not acceptable_fill_confidence:
            rejections.append(
                EligibilityRejection(
                    code="fill_confidence_unacceptable",
                    message="fill confidence unacceptable",
                    observed=False,
                    threshold=True,
                )
            )
        if roll_count >= max_roll_count:
            rejections.append(
                EligibilityRejection(
                    code="maximum_roll_count_reached",
                    message="maximum roll count reached",
                    observed=roll_count,
                    threshold=max_roll_count,
                )
            )
        if (
            request.maximum_cumulative_roll_debit is not None
            and cumulative_debit > request.maximum_cumulative_roll_debit
        ):
            rejections.append(
                EligibilityRejection(
                    code="maximum_cumulative_debit_exceeded",
                    message="cumulative debit cap exceeded",
                    observed=cumulative_debit,
                    threshold=request.maximum_cumulative_roll_debit,
                )
            )
        if request.minimum_credit is not None:
            estimate = candidate.estimated_net_credit_or_debit
            if estimate is None or estimate < request.minimum_credit:
                rejections.append(
                    EligibilityRejection(
                        code="minimum_credit_not_met",
                        message="credit requirement not met",
                        observed=estimate,
                        threshold=request.minimum_credit,
                    )
                )
        if request.maximum_debit is not None:
            estimate = candidate.estimated_net_credit_or_debit
            if estimate is not None and estimate < 0 and abs(estimate) > request.maximum_debit:
                rejections.append(
                    EligibilityRejection(
                        code="maximum_debit_exceeded",
                        message="debit cap exceeded",
                        observed=abs(estimate),
                        threshold=request.maximum_debit,
                    )
                )
        if not margin_compatible:
            rejections.append(
                EligibilityRejection(
                    code="margin_incompatible",
                    message="margin policy incompatible",
                    observed=False,
                    threshold=True,
                )
            )
        if not buying_power_available:
            rejections.append(
                EligibilityRejection(
                    code="buying_power_unavailable",
                    message="buying power unavailable",
                    observed=False,
                    threshold=True,
                )
            )
        if not no_conflicting_corporate_action:
            rejections.append(
                EligibilityRejection(
                    code="conflicting_corporate_action",
                    message="corporate action conflict",
                    observed=False,
                    threshold=True,
                )
            )
        if not no_unsupported_contract_adjustment:
            rejections.append(
                EligibilityRejection(
                    code="unsupported_contract_adjustment",
                    message="unsupported contract adjustment",
                    observed=False,
                    threshold=True,
                )
            )
        if not assignment_risk_compatible:
            rejections.append(
                EligibilityRejection(
                    code="assignment_risk_incompatible",
                    message="assignment risk incompatible",
                    observed=False,
                    threshold=True,
                )
            )
        if not dividend_risk_compatible:
            rejections.append(
                EligibilityRejection(
                    code="dividend_risk_incompatible",
                    message="dividend risk incompatible",
                    observed=False,
                    threshold=True,
                )
            )
        if not event_risk_allowed:
            rejections.append(
                EligibilityRejection(
                    code="event_risk_restricted",
                    message="event risk restrictions active",
                    observed=False,
                    threshold=True,
                )
            )
        if not no_look_ahead_compliant:
            rejections.append(
                EligibilityRejection(
                    code="no_look_ahead_violation",
                    message="candidate violates no-look-ahead",
                    observed=False,
                    threshold=True,
                )
            )
        if not cooldown_passed:
            rejections.append(
                EligibilityRejection(
                    code="policy_cooldown_active",
                    message="policy cooldown active",
                    observed=False,
                    threshold=True,
                )
            )
        if not min_time_since_prior_roll_passed:
            rejections.append(
                EligibilityRejection(
                    code="minimum_time_since_prior_roll_not_met",
                    message="insufficient time since prior roll",
                    observed=False,
                    threshold=True,
                )
            )

        return RollEligibilityEvaluation(
            eligible=not rejections,
            rejections=tuple(rejections),
            diagnostics={
                "roll_count": roll_count,
                "cumulative_debit": cumulative_debit,
                "candidate_id": candidate.candidate_id,
            },
        )


class ExpectedImprovementModel:
    def evaluate(
        self,
        *,
        before: dict[str, float],
        after: dict[str, float],
        weights: dict[str, float],
    ) -> ExpectedImprovementAssessment:
        keys = sorted(set(before) | set(after) | set(weights))
        components: list[ImprovementComponent] = []
        total = 0.0
        for key in keys:
            prior = before.get(key)
            nxt = after.get(key)
            weight = float(weights.get(key, 1.0))
            if prior is None or nxt is None:
                contribution = 0.0
            else:
                contribution = (nxt - prior) * weight
            total += contribution
            components.append(
                ImprovementComponent(
                    name=key,
                    weight=weight,
                    observed_before=prior,
                    observed_after=nxt,
                    contribution=contribution,
                    explanation=f"component={key}; contribution={contribution:.6f}",
                )
            )
        return ExpectedImprovementAssessment(
            total_score=total,
            components=tuple(components),
        )


class StrategyManagementPlanner:
    def __init__(self) -> None:
        self.eligibility_guard = RollEligibilityGuard()
        self.improvement_model = ExpectedImprovementModel()

    def build_roll_plan(
        self,
        *,
        plan_id: str,
        request: RollRequest,
        candidate: RollTargetCandidate,
        eligibility: RollEligibilityEvaluation,
        pre_roll_greeks: dict[str, float],
        post_roll_greeks: dict[str, float],
        pre_roll_margin: float | None,
        post_roll_margin: float | None,
        pre_roll_capital_usage: float | None,
        post_roll_capital_usage: float | None,
        assignment_risk_diagnostics: dict[str, Any],
        dividend_risk_diagnostics: dict[str, Any],
    ) -> RollPlan:
        if request.close_quantity <= 0:
            raise StrategyManagementError("close quantity must be positive")
        if request.target_quantity <= 0:
            raise StrategyManagementError("target quantity must be positive")
        warnings: tuple[str, ...]
        if candidate.estimated_closing_cost is None or candidate.estimated_opening_proceeds is None:
            warnings = (
                "missing_quote_data_no_fabricated_credit_debit",
                "estimated_credit_debit_unavailable",
            )
        else:
            warnings = ()

        expected_improvement = self.improvement_model.evaluate(
            before={
                "delta_normalization": pre_roll_greeks.get("delta", 0.0),
                "gamma_reduction": pre_roll_greeks.get("gamma", 0.0),
                "theta_improvement": pre_roll_greeks.get("theta", 0.0),
                "vega_adjustment": pre_roll_greeks.get("vega", 0.0),
                "margin_relief": float(pre_roll_margin or 0.0),
                "buying_power_relief": float(pre_roll_capital_usage or 0.0),
            },
            after={
                "delta_normalization": post_roll_greeks.get("delta", 0.0),
                "gamma_reduction": -post_roll_greeks.get("gamma", 0.0),
                "theta_improvement": post_roll_greeks.get("theta", 0.0),
                "vega_adjustment": -post_roll_greeks.get("vega", 0.0),
                "margin_relief": -(float(post_roll_margin or 0.0)),
                "buying_power_relief": -(float(post_roll_capital_usage or 0.0)),
            },
            weights={
                "delta_normalization": 1.0,
                "gamma_reduction": 1.0,
                "theta_improvement": 1.0,
                "vega_adjustment": 1.0,
                "margin_relief": 0.1,
                "buying_power_relief": 0.1,
            },
        )

        return RollPlan(
            plan_id=plan_id,
            request=request,
            selected_candidate=candidate,
            source_legs_to_close=request.selected_source_legs,
            target_legs_to_open=candidate.target_legs,
            preserved_legs=request.preserved_legs,
            proposed_quantities={
                "close_quantity": request.close_quantity,
                "target_quantity": request.target_quantity,
            },
            estimated_closing_cost=candidate.estimated_closing_cost,
            estimated_opening_proceeds=candidate.estimated_opening_proceeds,
            estimated_net_credit_or_debit=candidate.estimated_net_credit_or_debit,
            fees=candidate.fees,
            estimated_post_roll_basis=None,
            target_dte=candidate.target_dte,
            target_strike=candidate.target_strike,
            target_delta=candidate.target_delta,
            pre_roll_greeks=dict(pre_roll_greeks),
            post_roll_greeks=dict(post_roll_greeks),
            pre_roll_margin=pre_roll_margin,
            post_roll_margin=post_roll_margin,
            pre_roll_capital_usage=pre_roll_capital_usage,
            post_roll_capital_usage=post_roll_capital_usage,
            expected_improvement=expected_improvement,
            liquidity_diagnostics={
                "liquidity_score": candidate.liquidity_score,
                "liquidity_threshold": request.liquidity_threshold,
            },
            data_quality_diagnostics={
                "quote_quality_score": candidate.quality_score,
                "quote_quality_threshold": request.quote_quality_threshold,
            },
            assignment_risk_diagnostics=dict(assignment_risk_diagnostics),
            dividend_risk_diagnostics=dict(dividend_risk_diagnostics),
            warnings=warnings,
            eligibility=eligibility,
            reproducibility_metadata={
                "requested_timestamp": request.requested_timestamp.isoformat(),
                "trigger": request.trigger,
                "reason_code": request.reason_code,
            },
        )

    def reconcile_partial_roll(
        self,
        *,
        state: PartialRollState,
        retry_allowed: bool,
        elapsed_seconds: float,
    ) -> RollReconciliation:
        timeout_reached = elapsed_seconds >= state.timeout_seconds
        fallback_close = bool(timeout_reached and state.temporary_naked_exposure)
        cancel = bool(timeout_reached and not retry_allowed)
        retry = bool(not timeout_reached and retry_allowed)
        status = "resolved"
        if state.partial_target_fill or state.partial_close:
            status = "partial"
        if state.temporary_naked_exposure:
            status = "exposure"
        return RollReconciliation(
            reconciliation_id=f"recon:{state.state_id}",
            plan_id=state.plan_id,
            status=status,
            retry_scheduled=retry,
            cancel_scheduled=cancel,
            fallback_close_scheduled=fallback_close,
            state_transition=(
                "risk_escalation"
                if state.risk_escalated or fallback_close
                else "management_continue"
            ),
            recorded_temporary_exposure=state.temporary_naked_exposure,
            diagnostics={
                "elapsed_seconds": elapsed_seconds,
                "timeout_seconds": state.timeout_seconds,
                "residual_quantities": dict(state.residual_quantities),
            },
        )

    def compare_management_paths(
        self,
        *,
        comparison_id: str,
        strategy_instance_id: str,
        alternatives: tuple[ManagementPathAlternative, ...],
    ) -> ManagementComparison:
        if not alternatives:
            raise StrategyManagementError("at least one management alternative is required")

        def _score(item: ManagementPathAlternative) -> float:
            expected_value = item.expected_value or 0.0
            pop = item.probability_of_profit or 0.0
            tail = item.tail_risk or 0.0
            complexity_penalty = item.complexity * 0.1
            return expected_value + pop - tail - complexity_penalty

        selected = max(alternatives, key=_score)
        return ManagementComparison(
            comparison_id=comparison_id,
            strategy_instance_id=strategy_instance_id,
            alternatives=alternatives,
            selected_action=selected.action,
        )


class StrategyManagementAnalytics:
    def summarize_rolls(
        self,
        *,
        plans: tuple[RollPlan, ...],
    ) -> RollAnalyticsSummary:
        roll_count = len(plans)
        credits = [
            item.estimated_net_credit_or_debit
            for item in plans
            if item.estimated_net_credit_or_debit is not None
            and item.estimated_net_credit_or_debit > 0
        ]
        debits = [
            abs(item.estimated_net_credit_or_debit)
            for item in plans
            if item.estimated_net_credit_or_debit is not None
            and item.estimated_net_credit_or_debit < 0
        ]
        avg_dte = [float(item.target_dte or 0) for item in plans]
        avg_strike = [float(item.target_strike or 0.0) for item in plans]
        avg_delta = [float(item.target_delta or 0.0) for item in plans]
        theta_changes = [
            item.post_roll_greeks.get("theta", 0.0) - item.pre_roll_greeks.get("theta", 0.0)
            for item in plans
        ]
        vega_changes = [
            item.post_roll_greeks.get("vega", 0.0) - item.pre_roll_greeks.get("vega", 0.0)
            for item in plans
        ]
        gamma_changes = [
            item.post_roll_greeks.get("gamma", 0.0) - item.pre_roll_greeks.get("gamma", 0.0)
            for item in plans
        ]
        margin_changes = [
            float(item.post_roll_margin or 0.0) - float(item.pre_roll_margin or 0.0)
            for item in plans
        ]
        buying_power_changes = [
            float(item.post_roll_capital_usage or 0.0) - float(item.pre_roll_capital_usage or 0.0)
            for item in plans
        ]
        wins = [item.expected_improvement.total_score > 0 for item in plans]

        return RollAnalyticsSummary(
            roll_count=roll_count,
            roll_frequency=float(roll_count),
            average_credit=(sum(credits) / len(credits)) if credits else 0.0,
            average_debit=(sum(debits) / len(debits)) if debits else 0.0,
            cumulative_roll_credit=sum(credits),
            cumulative_roll_debit=sum(debits),
            fees=sum(item.fees for item in plans),
            average_dte_extension=(sum(avg_dte) / len(avg_dte)) if avg_dte else 0.0,
            average_strike_move=(sum(avg_strike) / len(avg_strike)) if avg_strike else 0.0,
            average_delta_change=(sum(avg_delta) / len(avg_delta)) if avg_delta else 0.0,
            theta_change=(sum(theta_changes) / len(theta_changes)) if theta_changes else 0.0,
            vega_change=(sum(vega_changes) / len(vega_changes)) if vega_changes else 0.0,
            gamma_change=(sum(gamma_changes) / len(gamma_changes)) if gamma_changes else 0.0,
            margin_change=(sum(margin_changes) / len(margin_changes)) if margin_changes else 0.0,
            buying_power_change=(sum(buying_power_changes) / len(buying_power_changes))
            if buying_power_changes
            else 0.0,
            win_rate_after_roll=(sum(1 for item in wins if item) / len(wins)) if wins else 0.0,
        )

    def summarize_conversions(
        self,
        *,
        conversions: tuple[ConversionPlan, ...],
    ) -> ConversionAnalyticsSummary:
        if not conversions:
            return ConversionAnalyticsSummary(
                conversion_count=0,
                conversion_cost=0.0,
                basis_change=0.0,
                risk_reduction=0.0,
                margin_change=0.0,
                expected_value_change=0.0,
                probability_of_profit_change=0.0,
                tail_risk_change=0.0,
                success_rate=0.0,
                failure_rate=0.0,
                reversal_rate=0.0,
                average_time_to_close_days=0.0,
            )

        costs = [float(item.conversion_cost or 0.0) for item in conversions]
        compatible = [item.compatible for item in conversions]

        return ConversionAnalyticsSummary(
            conversion_count=len(conversions),
            conversion_cost=sum(costs),
            basis_change=0.0,
            risk_reduction=0.0,
            margin_change=0.0,
            expected_value_change=0.0,
            probability_of_profit_change=0.0,
            tail_risk_change=0.0,
            success_rate=sum(1 for item in compatible if item) / len(compatible),
            failure_rate=sum(1 for item in compatible if not item) / len(compatible),
            reversal_rate=0.0,
            average_time_to_close_days=0.0,
        )


def validate_basis_transfer_invariants(
    result: BasisTrackingResult,
    *,
    tolerance: float = 1e-9,
) -> tuple[bool, tuple[str, ...]]:
    violations: list[str] = []

    expected_cycle_basis = result.target_leg_basis + result.preserved_leg_basis
    if abs(result.new_strategy_cycle_basis - expected_cycle_basis) > tolerance:
        violations.append("new_strategy_cycle_basis_mismatch")

    expected_cumulative_roll_cost = (
        result.cumulative_debits - result.cumulative_credits + result.fees
    )
    if abs(result.cumulative_roll_cost - expected_cumulative_roll_cost) > tolerance:
        violations.append("cumulative_roll_cost_mismatch")

    expected_transfer = result.new_strategy_cycle_basis - result.original_basis
    if abs(result.cost_basis_transfer - expected_transfer) > tolerance:
        violations.append("cost_basis_transfer_mismatch")

    return (len(violations) == 0, tuple(violations))


def default_roll_policy_registry() -> RollPolicyRegistry:
    registry = RollPolicyRegistry()
    for item in (
        RollPolicyDefinition(
            canonical_identifier="roll.pmcc_short_call_core",
            aliases=("pmcc_short_call", "pmcc_50_profit"),
            version="8C-v1",
            supported_strategy_families=("covered", "diagonal"),
            supported_lifecycle_states=(
                RollLifecycleState.OPEN,
                RollLifecycleState.MANAGED,
            ),
            supported_exercise_styles=("american", "european"),
            supported_settlement_types=("physical", "cash"),
            required_market_data=("quotes", "liquidity", "spread"),
            required_volatility_data=("iv_rank", "term_structure"),
            parameter_schema={
                "profit_target": {"type": "number", "default": 0.5},
                "delta_threshold": {"type": "number", "default": 0.4},
                "dte_threshold": {"type": "integer", "default": 21},
            },
            default_priority=10,
            status=RollPolicyStatus.MANDATORY,
            known_limitations=("research_only",),
        ),
        RollPolicyDefinition(
            canonical_identifier="roll.calendar_front_leg_replacement",
            aliases=("calendar_front_roll",),
            version="8C-v1",
            supported_strategy_families=("calendar", "diagonal"),
            supported_lifecycle_states=(RollLifecycleState.OPEN,),
            supported_exercise_styles=("american", "european"),
            supported_settlement_types=("cash", "physical"),
            required_market_data=("quotes", "earnings_calendar"),
            required_volatility_data=("front_iv", "back_iv", "term_structure"),
            parameter_schema={
                "target_dte": {"type": "integer", "default": 30},
                "earnings_aware": {"type": "boolean", "default": True},
            },
            default_priority=20,
            status=RollPolicyStatus.ADVISORY,
            known_limitations=("term_structure_model_based",),
        ),
    ):
        registry.register_policy(item)
    return registry
