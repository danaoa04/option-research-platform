"""As-of portfolio query services with nearest-prior semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .guards import NoLookAheadGuard
from .models import CashLedgerEntry, PortfolioSnapshot, PositionState


@dataclass(slots=True, frozen=True)
class AsOfResult[T]:
    value: T | None
    exact_match: bool
    as_of: datetime
    observed_timestamp: datetime | None


@dataclass(slots=True)
class BacktestAsOfQueryService:
    guard: NoLookAheadGuard

    def portfolio_state_as_of(
        self,
        *,
        as_of: datetime,
        snapshots: tuple[PortfolioSnapshot, ...],
    ) -> AsOfResult[PortfolioSnapshot]:
        return self._nearest(
            as_of=as_of, rows=snapshots, timestamp_getter=lambda row: row.timestamp
        )

    def open_positions_as_of(
        self,
        *,
        as_of: datetime,
        positions: tuple[PositionState, ...],
    ) -> tuple[PositionState, ...]:
        as_of_ts = _ensure_aware(as_of)
        output: list[PositionState] = []
        for position in positions:
            opened = _ensure_aware(position.opened_at)
            closed = _ensure_aware(position.closed_at) if position.closed_at is not None else None
            if opened <= as_of_ts and (closed is None or closed > as_of_ts):
                output.append(position)
        return tuple(output)

    def cash_ledger_as_of(
        self,
        *,
        as_of: datetime,
        entries: tuple[CashLedgerEntry, ...],
    ) -> tuple[CashLedgerEntry, ...]:
        as_of_ts = _ensure_aware(as_of)
        return tuple(entry for entry in entries if _ensure_aware(entry.timestamp) <= as_of_ts)

    def greeks_as_of(
        self,
        *,
        as_of: datetime,
        snapshots: tuple[PortfolioSnapshot, ...],
    ) -> AsOfResult[dict[str, float]]:
        nearest = self.portfolio_state_as_of(as_of=as_of, snapshots=snapshots)
        return AsOfResult(
            value=nearest.value.portfolio_greeks if nearest.value is not None else None,
            exact_match=nearest.exact_match,
            as_of=nearest.as_of,
            observed_timestamp=nearest.observed_timestamp,
        )

    def compare_runs(
        self,
        *,
        left: tuple[PortfolioSnapshot, ...],
        right: tuple[PortfolioSnapshot, ...],
    ) -> tuple[dict[str, Any], ...]:
        by_ts = {row.timestamp: row for row in right}
        output: list[dict[str, Any]] = []
        for row in left:
            peer = by_ts.get(row.timestamp)
            if peer is None:
                continue
            output.append(
                {
                    "timestamp": row.timestamp,
                    "left_equity": row.cash_balance + row.unrealized_pnl + row.realized_pnl,
                    "right_equity": peer.cash_balance + peer.unrealized_pnl + peer.realized_pnl,
                    "delta_realized_pnl": row.realized_pnl - peer.realized_pnl,
                    "delta_unrealized_pnl": row.unrealized_pnl - peer.unrealized_pnl,
                }
            )
        return tuple(output)

    def allocation_vs_realized_as_of(
        self,
        *,
        as_of: datetime,
        selected_allocation: tuple[dict[str, Any], ...],
        realized_allocation: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, Any], ...]:
        as_of_ts = _ensure_aware(as_of)
        selected = {
            str(item["candidate_id"]): item
            for item in selected_allocation
            if _ensure_aware(item["timestamp"]) <= as_of_ts
        }
        realized = {
            str(item["candidate_id"]): item
            for item in realized_allocation
            if _ensure_aware(item["timestamp"]) <= as_of_ts
        }
        keys = sorted(set(selected).union(realized))
        output: list[dict[str, Any]] = []
        for key in keys:
            left_row = selected.get(key, {})
            right_row = realized.get(key, {})
            output.append(
                {
                    "candidate_id": key,
                    "selected_weight": float(left_row.get("weight", 0.0)),
                    "realized_weight": float(right_row.get("weight", 0.0)),
                    "weight_delta": float(right_row.get("weight", 0.0))
                    - float(left_row.get("weight", 0.0)),
                }
            )
        return tuple(output)

    def candidate_selection_report_as_of(
        self,
        *,
        as_of: datetime,
        reports: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, Any], ...]:
        as_of_ts = _ensure_aware(as_of)
        return tuple(
            item
            for item in reports
            if _ensure_aware(item.get("timestamp")) <= as_of_ts
        )

    def constraint_violations_as_of(
        self,
        *,
        as_of: datetime,
        violations: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, Any], ...]:
        as_of_ts = _ensure_aware(as_of)
        return tuple(
            item
            for item in violations
            if _ensure_aware(item.get("timestamp")) <= as_of_ts
            and not bool(item.get("passed", True))
        )

    def risk_contribution_history_as_of(
        self,
        *,
        as_of: datetime,
        risk_history: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, Any], ...]:
        as_of_ts = _ensure_aware(as_of)
        return tuple(
            item
            for item in risk_history
            if _ensure_aware(item.get("timestamp")) <= as_of_ts
        )

    def strategy_state_as_of(
        self,
        *,
        as_of: datetime,
        strategy_states: tuple[dict[str, Any], ...],
        strategy_instance_id: str,
    ) -> AsOfResult[dict[str, Any]]:
        relevant = tuple(
            row
            for row in strategy_states
            if str(row.get("strategy_instance_id")) == strategy_instance_id
        )
        return self._nearest(
            as_of=as_of,
            rows=relevant,
            timestamp_getter=lambda row: row.get("as_of_timestamp"),
        )

    def leg_state_as_of(
        self,
        *,
        as_of: datetime,
        leg_states: tuple[dict[str, Any], ...],
        position_instance_id: str,
        leg_label: str,
    ) -> AsOfResult[dict[str, Any]]:
        relevant = tuple(
            row
            for row in leg_states
            if str(row.get("position_instance_id")) == position_instance_id
            and str(row.get("leg_label")) == leg_label
        )
        return self._nearest(
            as_of=as_of,
            rows=relevant,
            timestamp_getter=lambda row: row.get("as_of_timestamp"),
        )

    def transition_history(
        self,
        *,
        transitions: tuple[dict[str, Any], ...],
        strategy_instance_id: str,
    ) -> tuple[dict[str, Any], ...]:
        relevant = [
            row
            for row in transitions
            if str(row.get("strategy_instance_id")) == strategy_instance_id
        ]
        return tuple(sorted(relevant, key=lambda row: int(row.get("sequence_number", 0))))

    def roll_history(
        self,
        *,
        rolls: tuple[dict[str, Any], ...],
        strategy_instance_id: str,
    ) -> tuple[dict[str, Any], ...]:
        relevant = [
            row
            for row in rolls
            if str(row.get("strategy_instance_id")) == strategy_instance_id
        ]
        return tuple(sorted(relevant, key=lambda row: _ensure_aware(row.get("created_at"))))

    def lifecycle_trigger_history(
        self,
        *,
        triggers: tuple[dict[str, Any], ...],
        strategy_instance_id: str,
    ) -> tuple[dict[str, Any], ...]:
        relevant = [
            row
            for row in triggers
            if str(row.get("strategy_instance_id", row.get("strategy_id", "")))
            == strategy_instance_id
        ]
        return tuple(
            sorted(relevant, key=lambda row: _ensure_aware(row.get("trigger_timestamp")))
        )

    def open_and_closed_strategy_instances(
        self,
        *,
        strategy_states: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, Any], ...]:
        latest_by_instance: dict[str, dict[str, Any]] = {}
        for row in strategy_states:
            instance_id = str(row.get("strategy_instance_id"))
            current = latest_by_instance.get(instance_id)
            if current is None:
                latest_by_instance[instance_id] = row
                continue
            if _ensure_aware(row.get("as_of_timestamp")) >= _ensure_aware(
                current.get("as_of_timestamp")
            ):
                latest_by_instance[instance_id] = row
        return tuple(
            sorted(
                latest_by_instance.values(),
                key=lambda row: str(row.get("strategy_instance_id")),
            )
        )

    def unresolved_failures(
        self,
        *,
        integrity_failures: tuple[dict[str, Any], ...],
        resolved_failure_keys: tuple[str, ...],
    ) -> tuple[dict[str, Any], ...]:
        resolved = set(resolved_failure_keys)
        return tuple(
            item
            for item in integrity_failures
            if str(item.get("failure_key", "")) not in resolved
        )

    def residual_exposure_after_expiration(
        self,
        *,
        expiration_history: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, Any], ...]:
        return tuple(
            item
            for item in expiration_history
            if bool(item.get("residual_exposure_detected", False))
        )

    def _nearest[T](
        self,
        *,
        as_of: datetime,
        rows: tuple[T, ...],
        timestamp_getter: Any,
    ) -> AsOfResult[T]:
        as_of_ts = _ensure_aware(as_of)
        selected: T | None = None
        selected_ts: datetime | None = None
        for row in rows:
            row_ts = _ensure_aware(timestamp_getter(row))
            if row_ts > as_of_ts:
                continue
            if selected_ts is None or row_ts >= selected_ts:
                selected = row
                selected_ts = row_ts

        if selected_ts is not None:
            self.guard.assert_visible(as_of=as_of_ts, record_timestamp=selected_ts)
        return AsOfResult(
            value=selected,
            exact_match=selected_ts == as_of_ts,
            as_of=as_of_ts,
            observed_timestamp=selected_ts,
        )


def _ensure_aware(value: datetime | None) -> datetime:
    if value is None:
        return datetime(1970, 1, 1, tzinfo=UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
