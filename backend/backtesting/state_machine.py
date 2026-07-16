"""Strategy state-machine primitives for deterministic multi-leg backtesting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any


class LifecycleState(StrEnum):
    CONFIGURED = "configured"
    WAITING_FOR_ENTRY = "waiting_for_entry"
    ENTRY_SIGNALED = "entry_signaled"
    ENTRY_PENDING = "entry_pending"
    PARTIALLY_OPEN = "partially_open"
    OPEN = "open"
    MANAGEMENT_PENDING = "management_pending"
    EXIT_SIGNALED = "exit_signaled"
    EXIT_PENDING = "exit_pending"
    PARTIALLY_CLOSED = "partially_closed"
    ROLL_SIGNALED = "roll_signaled"
    ROLL_PENDING = "roll_pending"
    EXPIRED = "expired"
    PENDING_EXERCISE_OR_ASSIGNMENT = "pending_exercise_or_assignment"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TransitionTrigger(StrEnum):
    ENTRY_POLICY = "entry_policy"
    ENTRY_PLAN_CREATED = "entry_plan_created"
    ENTRY_INTENTS_SUBMITTED = "entry_intents_submitted"
    FILL_RECONCILIATION = "fill_reconciliation"
    MANAGEMENT_POLICY = "management_policy"
    EXIT_POLICY = "exit_policy"
    ROLL_POLICY = "roll_policy"
    EXPIRATION = "expiration"
    EXPIRATION_RESIDUAL = "expiration_residual"
    RISK_BREACH = "risk_breach"
    CANCELLATION = "cancellation"
    FAILURE = "failure"
    FINALIZATION = "finalization"


class GuardName(StrEnum):
    DATA_AVAILABLE = "data_available"
    MARKET_OPEN = "market_open"
    QUOTE_FRESHNESS = "quote_freshness"
    LIQUIDITY_THRESHOLD = "liquidity_threshold"
    BID_ASK_WIDTH = "bid_ask_width"
    CAPITAL_AVAILABLE = "capital_available"
    STRATEGY_VALIDITY = "strategy_validity"
    LEG_COMPATIBILITY = "leg_compatibility"
    EXPIRATION_ORDERING = "expiration_ordering"
    EXERCISE_STYLE_COMPATIBILITY = "exercise_style_compatibility"
    MINIMUM_QUALITY_SCORE = "minimum_quality_score"
    NO_CONFLICTING_LIFECYCLE_ACTION = "no_conflicting_lifecycle_action"
    NO_DUPLICATE_ORDER_INTENT = "no_duplicate_order_intent"
    NO_LOOK_AHEAD_COMPLIANCE = "no_look_ahead_compliance"
    MAXIMUM_OPEN_POSITIONS = "maximum_open_positions"
    EVENT_RISK_RESTRICTIONS = "event_risk_restrictions"
    EARNINGS_WINDOW_RESTRICTIONS = "earnings_window_restrictions"
    CORPORATE_ACTION_RESTRICTIONS = "corporate_action_restrictions"


class ActionName(StrEnum):
    CREATE_ENTRY_PLAN = "create_entry_plan"
    SUBMIT_RESEARCH_ORDER_INTENTS = "submit_research_order_intents"
    RECONCILE_FILLS = "reconcile_fills"
    ACTIVATE_POSITION = "activate_position"
    MARK_POSITION = "mark_position"
    TRIGGER_MANAGEMENT = "trigger_management"
    TRIGGER_EXIT = "trigger_exit"
    TRIGGER_ROLL = "trigger_roll"
    PROCESS_EXPIRATION = "process_expiration"
    CANCEL_PENDING_ACTION = "cancel_pending_action"
    FAIL_POSITION = "fail_position"
    CLOSE_POSITION = "close_position"
    FINALIZE_STRATEGY_INSTANCE = "finalize_strategy_instance"


@dataclass(slots=True, frozen=True)
class GuardResult:
    guard: GuardName
    passed: bool
    reason_code: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ActionPlan:
    action: ActionName
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class StateTransitionRecord:
    sequence_number: int
    prior_state: LifecycleState
    next_state: LifecycleState
    timestamp: datetime
    trigger: TransitionTrigger
    guard_results: tuple[GuardResult, ...]
    action_plan: tuple[ActionPlan, ...]
    data_snapshot_reference: str
    strategy_identifier: str
    position_identifier: str
    software_git_commit: str
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    checksum_metadata: dict[str, str] = field(default_factory=dict)


class InvalidTransitionError(RuntimeError):
    """Raised when a lifecycle transition is invalid or non-deterministic."""


_ALLOWED_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.CONFIGURED: frozenset(
        {
            LifecycleState.WAITING_FOR_ENTRY,
            LifecycleState.CANCELLED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.WAITING_FOR_ENTRY: frozenset(
        {
            LifecycleState.ENTRY_SIGNALED,
            LifecycleState.CANCELLED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.ENTRY_SIGNALED: frozenset(
        {
            LifecycleState.ENTRY_PENDING,
            LifecycleState.CANCELLED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.ENTRY_PENDING: frozenset(
        {
            LifecycleState.PARTIALLY_OPEN,
            LifecycleState.OPEN,
            LifecycleState.CANCELLED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.PARTIALLY_OPEN: frozenset(
        {
            LifecycleState.OPEN,
            LifecycleState.CANCELLED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.OPEN: frozenset(
        {
            LifecycleState.MANAGEMENT_PENDING,
            LifecycleState.EXIT_SIGNALED,
            LifecycleState.ROLL_SIGNALED,
            LifecycleState.EXPIRED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.MANAGEMENT_PENDING: frozenset(
        {
            LifecycleState.OPEN,
            LifecycleState.EXIT_SIGNALED,
            LifecycleState.ROLL_SIGNALED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.EXIT_SIGNALED: frozenset(
        {
            LifecycleState.EXIT_PENDING,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.EXIT_PENDING: frozenset(
        {
            LifecycleState.PARTIALLY_CLOSED,
            LifecycleState.CLOSED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.PARTIALLY_CLOSED: frozenset(
        {
            LifecycleState.CLOSED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.ROLL_SIGNALED: frozenset(
        {
            LifecycleState.ROLL_PENDING,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.ROLL_PENDING: frozenset(
        {
            LifecycleState.OPEN,
            LifecycleState.PARTIALLY_OPEN,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.EXPIRED: frozenset(
        {
            LifecycleState.PENDING_EXERCISE_OR_ASSIGNMENT,
            LifecycleState.CLOSED,
        }
    ),
    LifecycleState.PENDING_EXERCISE_OR_ASSIGNMENT: frozenset(
        {
            LifecycleState.CLOSED,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.CLOSED: frozenset(),
    LifecycleState.CANCELLED: frozenset(),
    LifecycleState.FAILED: frozenset(),
}


@dataclass(slots=True)
class StrategyStateMachine:
    strategy_identifier: str
    position_identifier: str
    software_git_commit: str
    state: LifecycleState = LifecycleState.CONFIGURED
    sequence_number: int = 0
    transitions: list[StateTransitionRecord] = field(default_factory=list)

    def transition(
        self,
        *,
        next_state: LifecycleState,
        timestamp: datetime,
        trigger: TransitionTrigger,
        guard_results: tuple[GuardResult, ...],
        action_plan: tuple[ActionPlan, ...],
        data_snapshot_reference: str,
        warnings: tuple[str, ...] = (),
        failures: tuple[str, ...] = (),
    ) -> StateTransitionRecord:
        normalized_timestamp = _ensure_aware(timestamp)
        self._assert_can_transition(next_state=next_state)
        self._assert_guards(guard_results=guard_results)
        self._assert_ordering(timestamp=normalized_timestamp)
        self.sequence_number += 1

        checksum = self._transition_checksum(
            sequence_number=self.sequence_number,
            prior_state=self.state,
            next_state=next_state,
            timestamp=normalized_timestamp,
            trigger=trigger,
            snapshot=data_snapshot_reference,
        )
        record = StateTransitionRecord(
            sequence_number=self.sequence_number,
            prior_state=self.state,
            next_state=next_state,
            timestamp=normalized_timestamp,
            trigger=trigger,
            guard_results=guard_results,
            action_plan=action_plan,
            data_snapshot_reference=data_snapshot_reference,
            strategy_identifier=self.strategy_identifier,
            position_identifier=self.position_identifier,
            software_git_commit=self.software_git_commit,
            warnings=warnings,
            failures=failures,
            checksum_metadata={"row_checksum": checksum},
        )
        self.state = next_state
        self.transitions.append(record)
        return record

    def _assert_can_transition(self, *, next_state: LifecycleState) -> None:
        allowed = _ALLOWED_TRANSITIONS[self.state]
        if next_state not in allowed:
            raise InvalidTransitionError(
                f"invalid transition: state={self.state.value} next_state={next_state.value}"
            )

    def _assert_guards(self, *, guard_results: tuple[GuardResult, ...]) -> None:
        failed = [item for item in guard_results if not item.passed]
        if failed:
            reasons = ",".join(f"{item.guard.value}:{item.reason_code}" for item in failed)
            raise InvalidTransitionError(f"transition guards failed: {reasons}")

    def _assert_ordering(self, *, timestamp: datetime) -> None:
        if not self.transitions:
            return
        last = self.transitions[-1]
        if timestamp < last.timestamp:
            raise InvalidTransitionError(
                "transition timestamp is non-deterministic: "
                f"timestamp={timestamp.isoformat()} "
                f"last={last.timestamp.isoformat()}"
            )

    @staticmethod
    def _transition_checksum(
        *,
        sequence_number: int,
        prior_state: LifecycleState,
        next_state: LifecycleState,
        timestamp: datetime,
        trigger: TransitionTrigger,
        snapshot: str,
    ) -> str:
        payload = (
            f"{sequence_number}|{prior_state.value}|{next_state.value}|"
            f"{timestamp.isoformat()}|{trigger.value}|{snapshot}"
        )
        return sha256(payload.encode("utf-8")).hexdigest()


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
