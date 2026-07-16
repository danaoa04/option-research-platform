"""Deterministic historical market-data event clock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from .exceptions import EventClockError
from .models import (
    ClockEvent,
    DeterministicEvent,
    DuplicateEventPolicy,
    EventClockConfig,
    EventPriority,
    EventType,
    MissingSessionPolicy,
    TradingSession,
)


@dataclass(slots=True)
class HistoricalEventClock:
    """Build and replay deterministic event streams for backtesting."""

    config: EventClockConfig

    def build(
        self,
        *,
        sessions: tuple[TradingSession, ...],
        timed_events: tuple[ClockEvent, ...],
    ) -> tuple[DeterministicEvent, ...]:
        valid_sessions = self._validate_sessions(sessions)
        clock_events = list(self._default_session_events(valid_sessions))
        clock_events.extend(timed_events)

        normalized = [
            ClockEvent(
                timestamp=_ensure_aware(item.timestamp),
                event_type=item.event_type,
                priority=self._priority(item.event_type, item.priority),
                sequence_hint=item.sequence_hint,
                payload=dict(item.payload),
            )
            for item in clock_events
        ]
        deduped = self._dedupe(tuple(normalized))
        ordered = sorted(
            deduped,
            key=lambda item: (
                _ensure_aware(item.timestamp),
                item.priority,
                item.event_type.value,
                item.sequence_hint,
            ),
        )

        output: list[DeterministicEvent] = []
        for sequence, event in enumerate(ordered, start=1):
            event_id = self._event_id(sequence=sequence, event=event)
            output.append(
                DeterministicEvent(
                    event_id=event_id,
                    timestamp=_ensure_aware(event.timestamp),
                    event_type=event.event_type,
                    priority=event.priority,
                    sequence_number=sequence,
                    payload=dict(event.payload),
                )
            )
        return tuple(output)

    def _default_session_events(
        self, sessions: tuple[TradingSession, ...]
    ) -> tuple[ClockEvent, ...]:
        events: list[ClockEvent] = []
        for session in sessions:
            if not session.is_trading_day:
                continue
            events.append(
                ClockEvent(
                    timestamp=_ensure_aware(session.open_timestamp),
                    event_type=EventType.SESSION_OPEN,
                    priority=self._priority(EventType.SESSION_OPEN, EventPriority.SESSION_OPEN),
                    payload={"trade_date": session.trade_date.isoformat()},
                )
            )
            events.append(
                ClockEvent(
                    timestamp=_ensure_aware(session.close_timestamp),
                    event_type=EventType.SESSION_CLOSE,
                    priority=self._priority(EventType.SESSION_CLOSE, EventPriority.SESSION_CLOSE),
                    payload={"trade_date": session.trade_date.isoformat()},
                )
            )
        return tuple(events)

    def _validate_sessions(
        self, sessions: tuple[TradingSession, ...]
    ) -> tuple[TradingSession, ...]:
        if not sessions:
            if self.config.missing_session_policy is MissingSessionPolicy.RAISE:
                raise EventClockError("no trading sessions available for configured backtest range")
            return ()

        ordered = sorted(sessions, key=lambda session: session.trade_date)
        for session in ordered:
            if _ensure_aware(session.open_timestamp) >= _ensure_aware(session.close_timestamp):
                raise EventClockError(
                    "session open timestamp must be earlier than close timestamp "
                    f"(trade_date={session.trade_date.isoformat()})"
                )
        return tuple(ordered)

    def _priority(self, event_type: EventType, fallback: int) -> int:
        return self.config.event_priorities.get(event_type, int(fallback))

    def _dedupe(self, events: tuple[ClockEvent, ...]) -> tuple[ClockEvent, ...]:
        if self.config.duplicate_event_policy is DuplicateEventPolicy.KEEP_ALL:
            return events

        by_key: dict[tuple[datetime, EventType, int], ClockEvent] = {}
        for item in events:
            key = (_ensure_aware(item.timestamp), item.event_type, item.sequence_hint)
            if key not in by_key:
                by_key[key] = item
                continue

            if self.config.duplicate_event_policy is DuplicateEventPolicy.KEEP_FIRST:
                continue
            if self.config.duplicate_event_policy is DuplicateEventPolicy.KEEP_LAST:
                by_key[key] = item
                continue
            raise EventClockError(
                "duplicate event detected under strict policy "
                f"(timestamp={item.timestamp.isoformat()} type={item.event_type.value})"
            )
        return tuple(by_key.values())

    def _event_id(self, *, sequence: int, event: ClockEvent) -> str:
        payload = (
            f"{sequence}|{event.timestamp.isoformat()}|{event.event_type.value}|"
            f"{event.priority}|{event.sequence_hint}|{sorted(event.payload.items())}"
        )
        return sha256(payload.encode("utf-8")).hexdigest()


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
