"""Opt-in deterministic benchmarks for historical backtesting foundations."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from time import perf_counter

from .clock import HistoricalEventClock
from .models import ClockEvent, EventClockConfig, EventPriority, EventType, TradingSession


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
