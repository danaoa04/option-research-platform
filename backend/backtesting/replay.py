"""Deterministic historical replay service for backtest event inspection."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import Any

from .models import DeterministicEvent


class ReplayStatus(StrEnum):
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass(slots=True, frozen=True)
class ReplaySnapshot:
    snapshot_id: str
    cursor: int
    timestamp: datetime
    strategy_state: dict[str, Any]
    leg_state: dict[str, Any]
    portfolio_state: dict[str, Any]
    cash_state: dict[str, Any]
    greeks: dict[str, float]
    volatility_state: dict[str, Any]
    open_order_intents: tuple[dict[str, Any], ...]
    pending_fills: tuple[dict[str, Any], ...]
    lifecycle_state: str
    source_checksums: dict[str, str]
    roll_context: dict[str, Any] = field(default_factory=dict)
    conversion_context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ReplayInspection:
    event: DeterministicEvent
    information_set: tuple[dict[str, Any], ...]
    quotes: tuple[dict[str, Any], ...]
    greeks: dict[str, float]
    volatility_surface: dict[str, Any]
    lifecycle_decisions: tuple[dict[str, Any], ...]
    portfolio_state: dict[str, Any]
    execution_context: dict[str, Any] = field(default_factory=dict)
    roll_candidates: tuple[dict[str, Any], ...] = ()
    roll_eligibility_failures: tuple[dict[str, Any], ...] = ()
    expected_improvement_components: tuple[dict[str, Any], ...] = ()
    selected_roll: dict[str, Any] = field(default_factory=dict)
    competing_actions: tuple[dict[str, Any], ...] = ()
    estimated_credit_or_debit: float | None = None
    actual_research_fill: dict[str, Any] = field(default_factory=dict)
    basis_update: dict[str, Any] = field(default_factory=dict)
    state_transition: dict[str, Any] = field(default_factory=dict)
    post_roll_greeks: dict[str, float] = field(default_factory=dict)
    post_roll_margin: dict[str, Any] = field(default_factory=dict)
    post_roll_pnl: dict[str, Any] = field(default_factory=dict)
    conversion_path: tuple[dict[str, Any], ...] = ()


@dataclass(slots=True, frozen=True)
class ReplaySession:
    session_id: str
    run_id: str
    timeline_id: str
    base_branch_id: str
    status: str
    metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ReplayBranch:
    branch_id: str
    parent_branch_id: str | None
    root_snapshot_id: str
    decision_delta: dict[str, Any]
    metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ReplayTimelineEvent:
    event_sequence: int
    timestamp: datetime
    event_type: str
    severity: str
    strategy_id: str
    symbol: str
    tags: tuple[str, ...]
    payload: dict[str, Any]
    checksum: str


@dataclass(slots=True, frozen=True)
class ReplayFilter:
    """Explicit, composable filter used by research timeline views."""

    strategy_id: str | None = None
    symbol: str | None = None
    event_types: tuple[str, ...] = ()
    severities: tuple[str, ...] = ()
    scenario_id: str | None = None
    policy_id: str | None = None
    optimizer_id: str | None = None
    branch_id: str | None = None
    user_tags: tuple[str, ...] = ()
    start: datetime | None = None
    end: datetime | None = None


@dataclass(slots=True, frozen=True)
class DecisionExplanation:
    """Machine-readable rationale for an automated research decision."""

    decision_kind: str
    outcome: str
    reasons: tuple[dict[str, Any], ...]
    policy_id: str | None = None
    alternatives: tuple[dict[str, Any], ...] = ()


@dataclass(slots=True, frozen=True)
class ReplayComparison:
    left_branch_id: str
    right_branch_id: str
    matching: bool
    differing_events: tuple[int, ...]
    differing_policy_decisions: tuple[int, ...]
    differing_fills: tuple[int, ...]
    differing_scenarios: tuple[int, ...]
    differing_analytics: tuple[int, ...]


@dataclass(slots=True, frozen=True)
class DecisionGraphNode:
    node_id: str
    kind: str
    payload: dict[str, Any]


@dataclass(slots=True, frozen=True)
class DecisionGraph:
    nodes: tuple[DecisionGraphNode, ...]
    edges: tuple[tuple[str, str], ...]


@dataclass(slots=True)
class BacktestReplayEngine:
    events: tuple[DeterministicEvent, ...]
    snapshots: list[ReplaySnapshot] = field(default_factory=list)
    cursor: int = 0
    status: ReplayStatus = ReplayStatus.PAUSED
    replay_speed: float = 1.0
    filter_event_types: tuple[str, ...] = ()
    replay_session: ReplaySession | None = None
    branches: dict[str, ReplayBranch] = field(default_factory=dict)
    branch_events: dict[str, list[ReplayTimelineEvent]] = field(default_factory=dict)

    def play(self) -> ReplayStatus:
        self.status = ReplayStatus.PLAYING
        return self.status

    def pause(self) -> ReplayStatus:
        self.status = ReplayStatus.PAUSED
        return self.status

    def step_forward(self) -> DeterministicEvent | None:
        if self.cursor >= len(self.events):
            return None
        event = self.events[self.cursor]
        self.cursor += 1
        return event

    def step_backward(self) -> DeterministicEvent | None:
        if self.cursor <= 1:
            self.cursor = 0
            return None
        self.cursor -= 1
        return self.events[self.cursor - 1]

    def jump_to_timestamp(self, *, timestamp: datetime) -> DeterministicEvent | None:
        for index, event in enumerate(self.events):
            if event.timestamp >= timestamp:
                self.cursor = index
                return event
        self.cursor = len(self.events)
        return None

    def jump_to_reason(self, *, reason_code: str) -> DeterministicEvent | None:
        for index, event in enumerate(self.events):
            if str(event.payload.get("reason_code", "")) == reason_code:
                self.cursor = index
                return event
        return None

    def jump_to_event_type(self, *, event_type: str) -> DeterministicEvent | None:
        for index, event in enumerate(self.events):
            if event.event_type.value == event_type:
                self.cursor = index
                return event
        return None

    def set_replay_speed(self, *, speed: float) -> float:
        self.replay_speed = max(0.1, speed)
        return self.replay_speed

    def set_filter_event_types(self, *, event_types: tuple[str, ...]) -> tuple[str, ...]:
        self.filter_event_types = event_types
        return self.filter_event_types

    def inspect_current(
        self,
        *,
        information_set: tuple[dict[str, Any], ...],
        quotes: tuple[dict[str, Any], ...],
        greeks: dict[str, float],
        volatility_surface: dict[str, Any],
        lifecycle_decisions: tuple[dict[str, Any], ...],
        portfolio_state: dict[str, Any],
        execution_context: dict[str, Any] | None = None,
        roll_candidates: tuple[dict[str, Any], ...] = (),
        roll_eligibility_failures: tuple[dict[str, Any], ...] = (),
        expected_improvement_components: tuple[dict[str, Any], ...] = (),
        selected_roll: dict[str, Any] | None = None,
        competing_actions: tuple[dict[str, Any], ...] = (),
        estimated_credit_or_debit: float | None = None,
        actual_research_fill: dict[str, Any] | None = None,
        basis_update: dict[str, Any] | None = None,
        state_transition: dict[str, Any] | None = None,
        post_roll_greeks: dict[str, float] | None = None,
        post_roll_margin: dict[str, Any] | None = None,
        post_roll_pnl: dict[str, Any] | None = None,
        conversion_path: tuple[dict[str, Any], ...] = (),
    ) -> ReplayInspection | None:
        if not self.events or self.cursor >= len(self.events):
            return None
        event = self.events[self.cursor]
        return ReplayInspection(
            event=event,
            information_set=information_set,
            quotes=quotes,
            greeks=greeks,
            volatility_surface=volatility_surface,
            lifecycle_decisions=lifecycle_decisions,
            portfolio_state=portfolio_state,
            execution_context=execution_context or {},
            roll_candidates=roll_candidates,
            roll_eligibility_failures=roll_eligibility_failures,
            expected_improvement_components=expected_improvement_components,
            selected_roll=selected_roll or {},
            competing_actions=competing_actions,
            estimated_credit_or_debit=estimated_credit_or_debit,
            actual_research_fill=actual_research_fill or {},
            basis_update=basis_update or {},
            state_transition=state_transition or {},
            post_roll_greeks=post_roll_greeks or {},
            post_roll_margin=post_roll_margin or {},
            post_roll_pnl=post_roll_pnl or {},
            conversion_path=conversion_path,
        )

    def create_snapshot(
        self,
        *,
        snapshot_id: str,
        strategy_state: dict[str, Any],
        leg_state: dict[str, Any],
        portfolio_state: dict[str, Any],
        cash_state: dict[str, Any],
        greeks: dict[str, float],
        volatility_state: dict[str, Any],
        open_order_intents: tuple[dict[str, Any], ...],
        pending_fills: tuple[dict[str, Any], ...],
        lifecycle_state: str,
        source_checksums: dict[str, str],
        roll_context: dict[str, Any] | None = None,
        conversion_context: dict[str, Any] | None = None,
    ) -> ReplaySnapshot | None:
        if not self.events:
            return None
        index = min(max(0, self.cursor), len(self.events) - 1)
        # A snapshot must not retain mutable caller-owned dictionaries.  JSON
        # round-tripping also gives deterministic, serializable state.
        snapshot = ReplaySnapshot(
            snapshot_id=snapshot_id,
            cursor=index,
            timestamp=self.events[index].timestamp,
            strategy_state=_immutable_copy(strategy_state),
            leg_state=_immutable_copy(leg_state),
            portfolio_state=_immutable_copy(portfolio_state),
            cash_state=_immutable_copy(cash_state),
            greeks=_immutable_copy(greeks),
            volatility_state=_immutable_copy(volatility_state),
            open_order_intents=tuple(_immutable_copy(item) for item in open_order_intents),
            pending_fills=tuple(_immutable_copy(item) for item in pending_fills),
            lifecycle_state=lifecycle_state,
            source_checksums=_immutable_copy(source_checksums),
            roll_context=_immutable_copy(roll_context or {}),
            conversion_context=_immutable_copy(conversion_context or {}),
        )
        self.snapshots.append(snapshot)
        return snapshot

    def restore_snapshot(self, *, snapshot_id: str) -> ReplaySnapshot | None:
        for snapshot in self.snapshots:
            if snapshot.snapshot_id == snapshot_id:
                self.cursor = snapshot.cursor
                return snapshot
        return None

    def initialize_session(
        self,
        *,
        session_id: str,
        run_id: str,
        timeline_id: str,
        base_branch_id: str = "main",
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> ReplaySession:
        session = ReplaySession(
            session_id=session_id,
            run_id=run_id,
            timeline_id=timeline_id,
            base_branch_id=base_branch_id,
            status=status,
            metadata=metadata or {},
        )
        self.replay_session = session
        if base_branch_id not in self.branches:
            self.branches[base_branch_id] = ReplayBranch(
                branch_id=base_branch_id,
                parent_branch_id=None,
                root_snapshot_id="",
                decision_delta={},
                metadata={},
            )
        self.branch_events.setdefault(base_branch_id, [])
        return session

    def create_branch(
        self,
        *,
        branch_id: str,
        parent_branch_id: str,
        root_snapshot_id: str,
        decision_delta: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ReplayBranch:
        if parent_branch_id not in self.branches:
            raise ValueError(f"unknown replay parent branch: {parent_branch_id}")
        if branch_id in self.branches:
            raise ValueError(f"replay branch already exists: {branch_id}")
        snapshot = next(
            (item for item in self.snapshots if item.snapshot_id == root_snapshot_id),
            None,
        )
        parent_events = list(self.branch_events.get(parent_branch_id, []))
        if snapshot is not None:
            parent_events = [
                item for item in parent_events if item.event_sequence <= snapshot.cursor
            ]
        branch = ReplayBranch(
            branch_id=branch_id,
            parent_branch_id=parent_branch_id,
            root_snapshot_id=root_snapshot_id,
            decision_delta=decision_delta or {},
            metadata=metadata or {},
        )
        self.branches[branch_id] = branch
        self.branch_events[branch_id] = parent_events
        return branch

    def append_branch_event(
        self,
        *,
        branch_id: str,
        event_type: str,
        severity: str,
        strategy_id: str,
        symbol: str,
        timestamp: datetime,
        tags: tuple[str, ...],
        payload: dict[str, Any],
    ) -> ReplayTimelineEvent:
        events = self.branch_events.setdefault(branch_id, [])
        event_sequence = len(events)
        checksum = _checksum(
            {
                "branch_id": branch_id,
                "event_sequence": event_sequence,
                "timestamp": timestamp.isoformat(),
                "event_type": event_type,
                "payload": payload,
            }
        )
        event = ReplayTimelineEvent(
            event_sequence=event_sequence,
            timestamp=timestamp,
            event_type=event_type,
            severity=severity,
            strategy_id=strategy_id,
            symbol=symbol,
            tags=tags,
            payload=_immutable_copy(payload),
            checksum=checksum,
        )
        events.append(event)
        return event

    def branch_timeline(self, branch_id: str) -> tuple[ReplayTimelineEvent, ...]:
        return tuple(self.branch_events.get(branch_id, []))

    def deterministic_branch_checksum(self, branch_id: str) -> str:
        timeline = self.branch_events.get(branch_id, [])
        payload = [
            {
                "event_sequence": item.event_sequence,
                "timestamp": item.timestamp.isoformat(),
                "event_type": item.event_type,
                "checksum": item.checksum,
            }
            for item in timeline
        ]
        return _checksum(payload)

    def filter_timeline(self, replay_filter: ReplayFilter) -> tuple[ReplayTimelineEvent, ...]:
        """Return deterministic, ordered events matching all supplied facets."""
        branch_ids = (
            (replay_filter.branch_id,) if replay_filter.branch_id else tuple(self.branch_events)
        )
        selected: list[ReplayTimelineEvent] = []
        for branch_id in branch_ids:
            for event in self.branch_events.get(branch_id, []):
                data = event.payload
                if replay_filter.strategy_id and event.strategy_id != replay_filter.strategy_id:
                    continue
                if replay_filter.symbol and event.symbol != replay_filter.symbol:
                    continue
                if replay_filter.event_types and event.event_type not in replay_filter.event_types:
                    continue
                if replay_filter.severities and event.severity not in replay_filter.severities:
                    continue
                if (
                    replay_filter.scenario_id
                    and data.get("scenario_id") != replay_filter.scenario_id
                ):
                    continue
                if replay_filter.policy_id and data.get("policy_id") != replay_filter.policy_id:
                    continue
                if (
                    replay_filter.optimizer_id
                    and data.get("optimizer_id") != replay_filter.optimizer_id
                ):
                    continue
                if replay_filter.user_tags and not set(replay_filter.user_tags).intersection(
                    event.tags
                ):
                    continue
                if replay_filter.start and event.timestamp < replay_filter.start:
                    continue
                if replay_filter.end and event.timestamp > replay_filter.end:
                    continue
                selected.append(event)
        return tuple(
            sorted(selected, key=lambda item: (item.timestamp, item.event_sequence, item.checksum))
        )

    def compare_branches(self, left_branch_id: str, right_branch_id: str) -> ReplayComparison:
        left = self.branch_timeline(left_branch_id)
        right = self.branch_timeline(right_branch_id)
        differing = tuple(
            index
            for index in range(max(len(left), len(right)))
            if index >= len(left)
            or index >= len(right)
            or left[index].checksum != right[index].checksum
        )

        def categories(name: str) -> tuple[int, ...]:
            return tuple(
                index
                for index in differing
                if any(
                    index < len(timeline)
                    and (timeline[index].event_type == name or name in timeline[index].event_type)
                    for timeline in (left, right)
                )
            )

        return ReplayComparison(
            left_branch_id,
            right_branch_id,
            not differing,
            differing,
            categories("policy"),
            categories("fill"),
            categories("scenario"),
            categories("analytics"),
        )

    def decision_graph(self, branch_id: str) -> DecisionGraph:
        """Build the fixed state→policy→decision→execution→portfolio→analytics chain."""
        nodes: list[DecisionGraphNode] = []
        edges: list[tuple[str, str]] = []
        for event in self.branch_timeline(branch_id):
            previous: str | None = None
            for kind in (
                "state",
                "policy",
                "decision",
                "execution",
                "portfolio",
                "analytics",
                "next_state",
            ):
                node_id = f"{branch_id}:{event.event_sequence}:{kind}"
                nodes.append(
                    DecisionGraphNode(
                        node_id, kind, {"event_checksum": event.checksum, **event.payload}
                    )
                )
                if previous:
                    edges.append((previous, node_id))
                previous = node_id
        return DecisionGraph(tuple(nodes), tuple(edges))

    @staticmethod
    def explain_decision(
        *,
        decision_kind: str,
        outcome: str,
        policy_id: str | None,
        reasons: tuple[dict[str, Any], ...],
        alternatives: tuple[dict[str, Any], ...] = (),
    ) -> DecisionExplanation:
        """Create a structured explanation; each reason has a stable machine key."""
        normalized = tuple(
            {
                "code": str(reason.get("code", "unspecified")),
                "observed": reason.get("observed"),
                "threshold": reason.get("threshold"),
                "comparison": str(reason.get("comparison", "")),
                "passed": bool(reason.get("passed", outcome == "approved")),
                **{
                    key: value
                    for key, value in reason.items()
                    if key not in {"code", "observed", "threshold", "comparison", "passed"}
                },
            }
            for reason in reasons
        )
        return DecisionExplanation(decision_kind, outcome, normalized, policy_id, alternatives)


def _immutable_copy(value: Any) -> Any:
    """Copy JSON-compatible replay state and prevent accidental top-level mutation."""
    copied = json.loads(json.dumps(value, sort_keys=True, default=str))
    return _freeze(copied)


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _checksum(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()
