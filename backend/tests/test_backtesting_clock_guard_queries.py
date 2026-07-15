from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from backend.backtesting.clock import HistoricalEventClock
from backend.backtesting.exceptions import NoLookAheadError
from backend.backtesting.guards import NoLookAheadGuard
from backend.backtesting.models import (
    AsOfPolicy,
    ClockEvent,
    DuplicateEventPolicy,
    EventClockConfig,
    EventPriority,
    EventType,
    MissingSessionPolicy,
    PortfolioSnapshot,
    PositionState,
    TradingSession,
)
from backend.backtesting.queries import BacktestAsOfQueryService


def test_event_clock_ordering_and_duplicates() -> None:
    clock = HistoricalEventClock(
        EventClockConfig(
            timezone="UTC",
            market_calendar="XNYS",
            duplicate_event_policy=DuplicateEventPolicy.KEEP_LAST,
        )
    )

    session = TradingSession(
        trade_date=date(2026, 6, 1),
        open_timestamp=datetime(2026, 6, 1, 14, 30, tzinfo=UTC),
        close_timestamp=datetime(2026, 6, 1, 21, 0, tzinfo=UTC),
    )
    events = (
        ClockEvent(
            timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
            event_type=EventType.QUOTE,
            priority=int(EventPriority.QUOTE),
            sequence_hint=1,
            payload={"v": 1},
        ),
        ClockEvent(
            timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
            event_type=EventType.QUOTE,
            priority=int(EventPriority.QUOTE),
            sequence_hint=1,
            payload={"v": 2},
        ),
    )

    built = clock.build(sessions=(session,), timed_events=events)
    quote_events = [item for item in built if item.event_type is EventType.QUOTE]
    assert len(quote_events) == 1
    assert quote_events[0].payload["v"] == 2
    assert quote_events[0].sequence_number > 0


def test_event_clock_missing_sessions_raise_when_configured() -> None:
    clock = HistoricalEventClock(
        EventClockConfig(
            timezone="UTC",
            market_calendar="XNYS",
            missing_session_policy=MissingSessionPolicy.RAISE,
        )
    )
    with pytest.raises(Exception):
        clock.build(sessions=(), timed_events=())


def test_no_lookahead_guard_enforced() -> None:
    guard = NoLookAheadGuard()
    with pytest.raises(NoLookAheadError):
        guard.assert_visible(
            as_of=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
            record_timestamp=datetime(2026, 6, 1, 15, 1, tzinfo=UTC),
        )


def test_asof_queries_nearest_prior_and_comparisons() -> None:
    guard = NoLookAheadGuard()
    service = BacktestAsOfQueryService(guard=guard)

    snapshots = (
        PortfolioSnapshot(
            timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
            cash_balance=1000,
            reserved_capital=100,
            realized_pnl=5,
            unrealized_pnl=2,
            accrued_fees=1,
            dividends=0,
        ),
        PortfolioSnapshot(
            timestamp=datetime(2026, 6, 1, 16, 0, tzinfo=UTC),
            cash_balance=1010,
            reserved_capital=100,
            realized_pnl=7,
            unrealized_pnl=1,
            accrued_fees=1,
            dividends=0,
        ),
    )
    as_of = service.portfolio_state_as_of(
        as_of=datetime(2026, 6, 1, 15, 30, tzinfo=UTC),
        snapshots=snapshots,
    )
    assert as_of.value is not None
    assert as_of.value.timestamp == datetime(2026, 6, 1, 15, 0, tzinfo=UTC)

    positions: tuple[PositionState, ...] = ()
    assert service.open_positions_as_of(
        as_of=datetime(2026, 6, 1, 15, 30, tzinfo=UTC),
        positions=positions,
    ) == ()

    audit = guard.audit_lookup(
        lookup_key="quotes",
        requested_timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
        observed_timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
        as_of_policy=AsOfPolicy.EXACT,
        source_manifest="m-1",
        source_ref="q-1",
        reason_code="decision",
    )
    assert audit.lookup_key == "quotes"

    allocation = service.allocation_vs_realized_as_of(
        as_of=datetime(2026, 6, 1, 15, 30, tzinfo=UTC),
        selected_allocation=(
            {
                "timestamp": datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
                "candidate_id": "a",
                "weight": 0.5,
            },
        ),
        realized_allocation=(
            {
                "timestamp": datetime(2026, 6, 1, 15, 5, tzinfo=UTC),
                "candidate_id": "a",
                "weight": 0.4,
            },
        ),
    )
    assert allocation[0]["weight_delta"] == pytest.approx(-0.1)

    constraints = service.constraint_violations_as_of(
        as_of=datetime(2026, 6, 1, 16, 0, tzinfo=UTC),
        violations=(
            {
                "timestamp": datetime(2026, 6, 1, 15, 45, tzinfo=UTC),
                "constraint": "max_delta",
                "passed": False,
            },
        ),
    )
    assert len(constraints) == 1


def test_strategy_query_helpers_nearest_prior() -> None:
    service = BacktestAsOfQueryService(guard=NoLookAheadGuard())
    as_of = datetime(2026, 6, 1, 15, 30, tzinfo=UTC)
    strategy_state = service.strategy_state_as_of(
        as_of=as_of,
        strategy_instance_id="si-1",
        strategy_states=(
            {
                "strategy_instance_id": "si-1",
                "lifecycle_state": "open",
                "as_of_timestamp": datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
            },
            {
                "strategy_instance_id": "si-1",
                "lifecycle_state": "exit_pending",
                "as_of_timestamp": datetime(2026, 6, 1, 16, 0, tzinfo=UTC),
            },
        ),
    )
    assert strategy_state.value is not None
    assert strategy_state.value["lifecycle_state"] == "open"

    leg_state = service.leg_state_as_of(
        as_of=as_of,
        position_instance_id="pi-1",
        leg_label="short_call",
        leg_states=(
            {
                "position_instance_id": "pi-1",
                "leg_label": "short_call",
                "remaining_quantity": 1,
                "as_of_timestamp": datetime(2026, 6, 1, 15, 5, tzinfo=UTC),
            },
            {
                "position_instance_id": "pi-1",
                "leg_label": "short_call",
                "remaining_quantity": 0,
                "as_of_timestamp": datetime(2026, 6, 1, 16, 5, tzinfo=UTC),
            },
        ),
    )
    assert leg_state.value is not None
    assert leg_state.value["remaining_quantity"] == 1

    unresolved = service.unresolved_failures(
        integrity_failures=(
            {"failure_key": "f-1", "reason_code": "cash_ledger_not_reconciled"},
            {"failure_key": "f-2", "reason_code": "position_closed_with_open_legs"},
        ),
        resolved_failure_keys=("f-1",),
    )
    assert len(unresolved) == 1
    assert unresolved[0]["failure_key"] == "f-2"

    residual = service.residual_exposure_after_expiration(
        expiration_history=(
            {"residual_exposure_detected": False},
            {"residual_exposure_detected": True, "position_instance_id": "pi-1"},
        )
    )
    assert len(residual) == 1
