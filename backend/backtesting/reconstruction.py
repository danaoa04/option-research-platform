"""Deterministic trade and strategy-cycle reconstruction from immutable ledgers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import LedgerRecord


@dataclass(slots=True, frozen=True)
class ReconstructedTrade:
    trade_id: str
    strategy_id: str
    position_id: str
    entry_intents: tuple[dict[str, Any], ...]
    fills: tuple[dict[str, Any], ...]
    management_actions: tuple[dict[str, Any], ...]
    rolls: tuple[dict[str, Any], ...]
    adjustments: tuple[dict[str, Any], ...]
    expiration_events: tuple[dict[str, Any], ...]
    closing_fills: tuple[dict[str, Any], ...]
    realized_pnl: float
    fees: float
    cash_movements: float
    final_state: str
    source_event_ids: tuple[str, ...]
    source_checksums: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class StrategyCycle:
    cycle_id: str
    strategy_id: str
    initial_position: str
    child_positions: tuple[str, ...]
    roll_chain: tuple[str, ...]
    cumulative_debit_credit: float
    cumulative_fees: float
    cumulative_pnl: float
    maximum_capital_usage: float
    total_holding_duration_seconds: float
    final_result: str
    lifecycle_reasons: tuple[str, ...]


@dataclass(slots=True)
class TradeReconstructionService:
    def reconstruct_trades(
        self,
        *,
        ledgers: tuple[LedgerRecord, ...],
    ) -> tuple[ReconstructedTrade, ...]:
        by_position: dict[str, list[LedgerRecord]] = {}
        for record in ledgers:
            if not record.position_id:
                continue
            by_position.setdefault(record.position_id, []).append(record)

        output: list[ReconstructedTrade] = []
        for position_id, records in by_position.items():
            ordered = sorted(records, key=lambda item: (item.timestamp, item.sequence_number))
            strategy_id = ordered[0].strategy_id
            entry = [
                row.payload
                for row in ordered
                if row.record_type in {"position_open", "entry_plan"}
            ]
            fills = [row.payload for row in ordered if row.record_type in {"fill", "partial_fill"}]
            management = [row.payload for row in ordered if row.record_type == "management"]
            rolls = [row.payload for row in ordered if row.record_type.startswith("roll")]
            adjustments = [row.payload for row in ordered if row.record_type == "adjustment"]
            expiration = [row.payload for row in ordered if row.record_type == "expiration"]
            closing = [
                row.payload
                for row in ordered
                if row.record_type in {"position_close", "closing_fill"}
            ]
            realized_pnl = sum(float(row.payload.get("realized_pnl", 0.0)) for row in ordered)
            fees = sum(float(row.payload.get("fees", 0.0)) for row in ordered)
            cash = sum(float(row.payload.get("cash_movement", 0.0)) for row in ordered)
            source_event_ids = tuple(str(row.payload.get("event_id", "")) for row in ordered)
            source_checksums = tuple(
                str(row.checksum_metadata.get("row_checksum", "")) for row in ordered
            )
            output.append(
                ReconstructedTrade(
                    trade_id=f"{strategy_id}:{position_id}",
                    strategy_id=strategy_id,
                    position_id=position_id,
                    entry_intents=tuple(entry),
                    fills=tuple(fills),
                    management_actions=tuple(management),
                    rolls=tuple(rolls),
                    adjustments=tuple(adjustments),
                    expiration_events=tuple(expiration),
                    closing_fills=tuple(closing),
                    realized_pnl=realized_pnl,
                    fees=fees,
                    cash_movements=cash,
                    final_state="closed" if closing else "open",
                    source_event_ids=source_event_ids,
                    source_checksums=source_checksums,
                )
            )
        return tuple(output)

    def reconstruct_cycles(
        self,
        *,
        trades: tuple[ReconstructedTrade, ...],
    ) -> tuple[StrategyCycle, ...]:
        by_strategy: dict[str, list[ReconstructedTrade]] = {}
        for trade in trades:
            by_strategy.setdefault(trade.strategy_id, []).append(trade)

        cycles: list[StrategyCycle] = []
        for strategy_id, rows in by_strategy.items():
            ordered = sorted(rows, key=lambda item: item.trade_id)
            initial = ordered[0].position_id
            child = tuple(item.position_id for item in ordered[1:])
            roll_chain = tuple(
                item.trade_id for item in ordered if item.rolls
            )
            cycles.append(
                StrategyCycle(
                    cycle_id=f"cycle:{strategy_id}:{initial}",
                    strategy_id=strategy_id,
                    initial_position=initial,
                    child_positions=child,
                    roll_chain=roll_chain,
                    cumulative_debit_credit=sum(item.cash_movements for item in ordered),
                    cumulative_fees=sum(item.fees for item in ordered),
                    cumulative_pnl=sum(item.realized_pnl for item in ordered),
                    maximum_capital_usage=max(
                        [
                            float(payload.get("capital_usage", 0.0))
                            for trade in ordered
                            for payload in trade.entry_intents
                        ]
                        or [0.0]
                    ),
                    total_holding_duration_seconds=float(len(ordered)) * 60.0,
                    final_result=(
                        "closed"
                        if all(item.final_state == "closed" for item in ordered)
                        else "open"
                    ),
                    lifecycle_reasons=tuple(
                        reason
                        for trade in ordered
                        for reason in (
                            str(payload.get("reason_code", ""))
                            for payload in trade.management_actions
                        )
                        if reason
                    ),
                )
            )
        return tuple(cycles)
