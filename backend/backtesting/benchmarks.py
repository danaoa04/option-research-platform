"""Opt-in deterministic benchmarks for historical backtesting foundations."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from time import perf_counter

from .clock import HistoricalEventClock
from .models import ClockEvent, EventClockConfig, EventPriority, EventType, TradingSession
from .orchestration import LegFillSnapshot, MultiLegOrchestrator, RollKind
from .state_machine import (
    ActionName,
    ActionPlan,
    GuardName,
    GuardResult,
    LifecycleState,
    StrategyStateMachine,
    TransitionTrigger,
)
from .strategies import compile_template


@dataclass(slots=True, frozen=True)
class BacktestBenchmarkResult:
    name: str
    input_size: int
    elapsed_seconds: float


@dataclass(slots=True)
class BacktestBenchmarkRunner:
    clock: HistoricalEventClock

    @classmethod
    def default(cls) -> BacktestBenchmarkRunner:
        return cls(
            clock=HistoricalEventClock(
                config=EventClockConfig(timezone="UTC", market_calendar="XNYS"),
            )
        )

    def run_all(self) -> list[BacktestBenchmarkResult]:
        if os.getenv("RUN_BACKTEST_BENCHMARKS", "0") != "1":
            return []
        return [
            self._benchmark_one_year_single_symbol(),
            self._benchmark_ten_year_single_symbol(),
            self._benchmark_multi_symbol_event_queue(),
            self._benchmark_large_event_queue(),
            self._benchmark_strategy_instances(count=100),
            self._benchmark_strategy_instances(count=1000),
            self._benchmark_large_transition_history(),
            self._benchmark_partial_fill_reconciliation(),
            self._benchmark_roll_plan_generation(),
            self._benchmark_serial_vs_threaded_placeholder(),
        ]

    def _benchmark_one_year_single_symbol(self) -> BacktestBenchmarkResult:
        sessions = _sessions(years=1)
        timed_events = _intraday_events(sessions=sessions, symbols=("SPY",))
        start = perf_counter()
        _ = self.clock.build(sessions=sessions, timed_events=timed_events)
        elapsed = perf_counter() - start
        return BacktestBenchmarkResult(
            "one_year_single_symbol_backtest",
            len(timed_events),
            elapsed,
        )

    def _benchmark_ten_year_single_symbol(self) -> BacktestBenchmarkResult:
        sessions = _sessions(years=10)
        timed_events = _intraday_events(sessions=sessions, symbols=("SPY",))
        start = perf_counter()
        _ = self.clock.build(sessions=sessions, timed_events=timed_events)
        elapsed = perf_counter() - start
        return BacktestBenchmarkResult(
            "ten_year_single_symbol_backtest",
            len(timed_events),
            elapsed,
        )

    def _benchmark_multi_symbol_event_queue(self) -> BacktestBenchmarkResult:
        sessions = _sessions(years=1)
        timed_events = _intraday_events(sessions=sessions, symbols=("SPY", "QQQ", "IWM", "DIA"))
        start = perf_counter()
        _ = self.clock.build(sessions=sessions, timed_events=timed_events)
        elapsed = perf_counter() - start
        return BacktestBenchmarkResult("multi_symbol_backtest", len(timed_events), elapsed)

    def _benchmark_large_event_queue(self) -> BacktestBenchmarkResult:
        sessions = _sessions(years=2)
        timed_events = _intraday_events(
            sessions=sessions,
            symbols=("SPY", "QQQ", "IWM", "DIA", "XLF", "XLK", "XLE", "XLI"),
        )
        start = perf_counter()
        _ = self.clock.build(sessions=sessions, timed_events=timed_events)
        elapsed = perf_counter() - start
        return BacktestBenchmarkResult("large_event_queue", len(timed_events), elapsed)

    def _benchmark_strategy_instances(self, *, count: int) -> BacktestBenchmarkResult:
        start = perf_counter()
        timestamp = datetime(2026, 6, 1, 14, 30, tzinfo=UTC)
        for idx in range(count):
            machine = StrategyStateMachine(
                strategy_identifier=f"strategy-{idx}",
                position_identifier=f"position-{idx}",
                software_git_commit="benchmark",
            )
            machine.transition(
                next_state=LifecycleState.WAITING_FOR_ENTRY,
                timestamp=timestamp,
                trigger=TransitionTrigger.ENTRY_POLICY,
                guard_results=(
                    GuardResult(guard=GuardName.DATA_AVAILABLE, passed=True, reason_code="ok"),
                ),
                action_plan=(
                    ActionPlan(action=ActionName.CREATE_ENTRY_PLAN, payload={}),
                ),
                data_snapshot_reference=f"snap-{idx}",
            )
        elapsed = perf_counter() - start
        return BacktestBenchmarkResult(
            f"strategy_instances_{count}",
            count,
            elapsed,
        )

    def _benchmark_large_transition_history(self) -> BacktestBenchmarkResult:
        machine = StrategyStateMachine(
            strategy_identifier="strategy-history",
            position_identifier="position-history",
            software_git_commit="benchmark",
        )
        start = perf_counter()
        now = datetime(2026, 6, 1, 14, 30, tzinfo=UTC)
        states = [
            LifecycleState.WAITING_FOR_ENTRY,
            LifecycleState.ENTRY_SIGNALED,
            LifecycleState.ENTRY_PENDING,
            LifecycleState.PARTIALLY_OPEN,
            LifecycleState.OPEN,
            LifecycleState.MANAGEMENT_PENDING,
            LifecycleState.OPEN,
            LifecycleState.EXIT_SIGNALED,
            LifecycleState.EXIT_PENDING,
            LifecycleState.CLOSED,
        ]
        for idx, state in enumerate(states):
            machine.transition(
                next_state=state,
                timestamp=now + timedelta(seconds=idx),
                trigger=TransitionTrigger.ENTRY_POLICY,
                guard_results=(
                    GuardResult(guard=GuardName.DATA_AVAILABLE, passed=True, reason_code="ok"),
                ),
                action_plan=(ActionPlan(action=ActionName.MARK_POSITION, payload={}),),
                data_snapshot_reference=f"snap-{idx}",
            )
        elapsed = perf_counter() - start
        return BacktestBenchmarkResult("large_transition_history", len(states), elapsed)

    def _benchmark_partial_fill_reconciliation(self) -> BacktestBenchmarkResult:
        orchestrator = MultiLegOrchestrator()
        fills = (
            LegFillSnapshot(
                leg_label="short_call",
                original_quantity=10,
                filled_quantity=7,
                remaining_quantity=3,
                average_entry_price=2.1,
                average_exit_price=None,
                current_mark=2.2,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                accrued_fees=1.0,
                multiplier=100,
                cost_basis=2100,
                intrinsic_value=0.0,
                extrinsic_value=2.2,
                lifecycle_status="open",
            ),
        )
        start = perf_counter()
        for _ in range(500):
            _ = orchestrator.reconcile_partial_fills(
                timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
                strategy_instance_id="s",
                position_instance_id="p",
                leg_fills=fills,
                minimum_fill_ratio=0.8,
                timeout_seconds=30,
                elapsed_seconds=40,
                cancellation_on_incomplete_fill=True,
            )
        elapsed = perf_counter() - start
        return BacktestBenchmarkResult("partial_fill_reconciliation", 500, elapsed)

    def _benchmark_roll_plan_generation(self) -> BacktestBenchmarkResult:
        orchestrator = MultiLegOrchestrator()
        definition = compile_template(template_name="pmcc")
        start = perf_counter()
        for idx in range(500):
            _ = orchestrator.plan_roll(
                plan_id=f"roll-{idx}",
                roll_kind=RollKind.LONG_LEG_REPLACEMENT,
                source_position_id="position-1",
                target_strategy_definition=definition,
                target_dte=45,
                target_strike_or_delta=0.3,
                estimated_credit_or_debit=0.25,
                preserved_legs=("short_otm_call",),
                closed_legs=("long_deep_itm_call",),
                opened_legs=("long_deep_itm_call",),
                policy_trigger="delta_threshold",
                reason="pmcc_management",
            )
        elapsed = perf_counter() - start
        return BacktestBenchmarkResult("roll_plan_generation", 500, elapsed)

    def _benchmark_serial_vs_threaded_placeholder(self) -> BacktestBenchmarkResult:
        start = perf_counter()
        serial_count = 0
        for _ in range(10000):
            serial_count += 1
        elapsed = perf_counter() - start
        return BacktestBenchmarkResult("serial_vs_threaded_evaluation", serial_count, elapsed)


def _sessions(*, years: int) -> tuple[TradingSession, ...]:
    start = date(2020, 1, 2)
    sessions: list[TradingSession] = []
    for offset in range(252 * years):
        day = start + timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        sessions.append(
            TradingSession(
                trade_date=day,
                open_timestamp=datetime(day.year, day.month, day.day, 14, 30, tzinfo=UTC),
                close_timestamp=datetime(day.year, day.month, day.day, 21, 0, tzinfo=UTC),
            )
        )
    return tuple(sessions)


def _intraday_events(
    *,
    sessions: tuple[TradingSession, ...],
    symbols: tuple[str, ...],
) -> tuple[ClockEvent, ...]:
    events: list[ClockEvent] = []
    for session in sessions:
        for symbol in symbols:
            for hour in (15, 17, 19, 20):
                timestamp = datetime(
                    session.trade_date.year,
                    session.trade_date.month,
                    session.trade_date.day,
                    hour,
                    0,
                    tzinfo=UTC,
                )
                events.append(
                    ClockEvent(
                        timestamp=timestamp,
                        event_type=EventType.QUOTE,
                        priority=int(EventPriority.QUOTE),
                        payload={"symbol": symbol},
                    )
                )
                events.append(
                    ClockEvent(
                        timestamp=timestamp,
                        event_type=EventType.VALUATION,
                        priority=int(EventPriority.VALUATION),
                        payload={"symbol": symbol},
                    )
                )
    return tuple(events)
