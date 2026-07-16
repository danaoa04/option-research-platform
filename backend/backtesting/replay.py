"""Deterministic historical replay service for backtest event inspection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
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


@dataclass(slots=True)
class BacktestReplayEngine:
    events: tuple[DeterministicEvent, ...]
    snapshots: list[ReplaySnapshot] = field(default_factory=list)
    cursor: int = 0
    status: ReplayStatus = ReplayStatus.PAUSED
    replay_speed: float = 1.0
    filter_event_types: tuple[str, ...] = ()

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
        snapshot = ReplaySnapshot(
            snapshot_id=snapshot_id,
            cursor=index,
            timestamp=self.events[index].timestamp,
            strategy_state=strategy_state,
            leg_state=leg_state,
            portfolio_state=portfolio_state,
            cash_state=cash_state,
            greeks=greeks,
            volatility_state=volatility_state,
            open_order_intents=open_order_intents,
            pending_fills=pending_fills,
            lifecycle_state=lifecycle_state,
            source_checksums=source_checksums,
            roll_context=roll_context or {},
            conversion_context=conversion_context or {},
        )
        self.snapshots.append(snapshot)
        return snapshot

    def restore_snapshot(self, *, snapshot_id: str) -> ReplaySnapshot | None:
        for snapshot in self.snapshots:
            if snapshot.snapshot_id == snapshot_id:
                self.cursor = snapshot.cursor
                return snapshot
        return None
