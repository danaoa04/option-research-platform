"""Typed execution and settlement query services with nearest-prior semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .guards import NoLookAheadGuard


@dataclass(slots=True, frozen=True)
class QueryAsOfResult:
    value: dict[str, Any] | None
    observed_timestamp: datetime | None


@dataclass(slots=True)
class ExecutionQueryService:
    guard: NoLookAheadGuard

    def execution_history(
        self,
        *,
        requests: tuple[dict[str, Any], ...],
        strategy_id: str,
    ) -> tuple[dict[str, Any], ...]:
        rows = [row for row in requests if str(row.get("strategy_id")) == strategy_id]
        return tuple(sorted(rows, key=lambda row: _aware(row.get("requested_timestamp"))))

    def fill_history(
        self,
        *,
        fills: tuple[dict[str, Any], ...],
        strategy_id: str,
    ) -> tuple[dict[str, Any], ...]:
        rows = [
            row
            for row in fills
            if str(row.get("strategy_id", row.get("strategy", ""))) == strategy_id
        ]
        return tuple(sorted(rows, key=lambda row: _aware(row.get("fill_timestamp"))))

    def fee_history(
        self,
        *,
        fee_items: tuple[dict[str, Any], ...],
        position_id: str,
    ) -> tuple[dict[str, Any], ...]:
        rows = [row for row in fee_items if str(row.get("position_id")) == position_id]
        return tuple(sorted(rows, key=lambda row: _aware(row.get("event_timestamp"))))

    def assignment_history(self, *, rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        return tuple(sorted(rows, key=lambda row: _aware(row.get("decision_timestamp"))))

    def exercise_history(self, *, rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        return tuple(sorted(rows, key=lambda row: _aware(row.get("decision_timestamp"))))

    def expiration_history(self, *, rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        return tuple(sorted(rows, key=lambda row: _aware(row.get("expiration_timestamp"))))

    def settlement_history(self, *, rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        return tuple(sorted(rows, key=lambda row: _aware(row.get("settlement_timestamp"))))

    def dividend_postings(self, *, rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        return tuple(sorted(rows, key=lambda row: _aware(row.get("ex_date"))))

    def stock_positions_as_of(
        self,
        *,
        as_of: datetime,
        rows: tuple[dict[str, Any], ...],
        symbol: str,
    ) -> QueryAsOfResult:
        return self._nearest(
            as_of=as_of,
            rows=tuple(row for row in rows if str(row.get("symbol")) == symbol),
            key="as_of_timestamp",
        )

    def cost_basis_as_of(
        self,
        *,
        as_of: datetime,
        rows: tuple[dict[str, Any], ...],
        strategy_cycle_id: str,
    ) -> QueryAsOfResult:
        return self._nearest(
            as_of=as_of,
            rows=tuple(
                row for row in rows if str(row.get("strategy_cycle_id")) == strategy_cycle_id
            ),
            key="as_of_timestamp",
        )

    def pin_risk_events(self, *, rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        return tuple(row for row in rows if bool(row.get("at_risk", False)))

    def reconciliation_failures(
        self,
        *,
        rows: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, Any], ...]:
        return tuple(row for row in rows if not bool(row.get("reconciled", False)))

    def strategy_cycle_settlement_history(
        self,
        *,
        rows: tuple[dict[str, Any], ...],
        strategy_cycle_id: str,
    ) -> tuple[dict[str, Any], ...]:
        scoped = [
            row
            for row in rows
            if str(row.get("strategy_cycle_id", row.get("cycle_id", ""))) == strategy_cycle_id
        ]
        return tuple(sorted(scoped, key=lambda row: _aware(row.get("settlement_timestamp"))))

    def _nearest(
        self,
        *,
        as_of: datetime,
        rows: tuple[dict[str, Any], ...],
        key: str,
    ) -> QueryAsOfResult:
        as_of_ts = _aware(as_of)
        selected: dict[str, Any] | None = None
        selected_ts: datetime | None = None
        for row in rows:
            row_ts = _aware(row.get(key))
            if row_ts > as_of_ts:
                continue
            if selected_ts is None or row_ts >= selected_ts:
                selected = row
                selected_ts = row_ts
        if selected_ts is not None:
            self.guard.assert_visible(as_of=as_of_ts, record_timestamp=selected_ts)
        return QueryAsOfResult(value=selected, observed_timestamp=selected_ts)


def _aware(value: datetime | None) -> datetime:
    if value is None:
        return datetime(1970, 1, 1, tzinfo=UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
