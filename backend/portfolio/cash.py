"""Immutable cash-ledger postings and settlement-timing aware balance updates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from .accounts import AccountConfiguration, AccountState


class CashEventType(StrEnum):
    PREMIUM_RECEIVED = "premium_received"
    PREMIUM_PAID = "premium_paid"
    STOCK_PURCHASE = "stock_purchase"
    STOCK_SALE = "stock_sale"
    EXERCISE = "exercise"
    ASSIGNMENT = "assignment"
    DIVIDEND = "dividend"
    FEE = "fee"
    COMMISSION = "commission"
    BORROW_CHARGE = "borrow_charge"
    INTEREST = "interest"
    COLLATERAL = "collateral"
    RESERVATION = "reservation"
    RELEASE = "release"
    LIQUIDATION = "liquidation"


@dataclass(slots=True, frozen=True)
class SettlementTiming:
    equity_trade_days: int = 1
    option_trade_days: int = 1
    exercise_days: int = 1
    assignment_days: int = 1
    cash_settled_option_days: int = 1
    dividend_days: int = 0
    fee_days: int = 0
    interest_days: int = 0
    borrow_days: int = 0


@dataclass(slots=True, frozen=True)
class CashPosting:
    posting_id: str
    event_type: CashEventType
    amount: float
    trade_timestamp: datetime
    effective_timestamp: datetime
    settlement_timestamp: datetime
    settled_delta: float
    unsettled_delta: float
    reserved_delta: float = 0.0
    collateral_delta: float = 0.0
    strategy_id: str | None = None
    position_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CashBalanceSnapshot:
    as_of: datetime
    settled_cash: float
    unsettled_cash: float
    reserved_cash: float
    collateral_cash: float
    free_cash: float
    net_cash: float


@dataclass(slots=True)
class CashLedgerEngine:
    settlement_timing: SettlementTiming = field(default_factory=SettlementTiming)

    def post(
        self,
        *,
        posting_id: str,
        event_type: CashEventType,
        amount: float,
        trade_timestamp: datetime,
        strategy_id: str | None = None,
        position_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CashPosting:
        trade_ts = _aware(trade_timestamp)
        lag_days = self._lag_days(event_type)
        settlement_ts = trade_ts if lag_days == 0 else trade_ts + timedelta(days=lag_days)
        settled_delta = amount if lag_days == 0 else 0.0
        unsettled_delta = 0.0 if lag_days == 0 else amount
        return CashPosting(
            posting_id=posting_id,
            event_type=event_type,
            amount=amount,
            trade_timestamp=trade_ts,
            effective_timestamp=trade_ts,
            settlement_timestamp=settlement_ts,
            settled_delta=settled_delta,
            unsettled_delta=unsettled_delta,
            strategy_id=strategy_id,
            position_id=position_id,
            metadata=dict(metadata or {}),
        )

    def reserve(
        self,
        *,
        posting_id: str,
        amount: float,
        timestamp: datetime,
        strategy_id: str | None = None,
        position_id: str | None = None,
        collateral: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> CashPosting:
        delta_key = "collateral_delta" if collateral else "reserved_delta"
        kwargs = {delta_key: amount}
        return CashPosting(
            posting_id=posting_id,
            event_type=(
                CashEventType.COLLATERAL
                if collateral
                else CashEventType.RESERVATION
            ),
            amount=0.0,
            trade_timestamp=_aware(timestamp),
            effective_timestamp=_aware(timestamp),
            settlement_timestamp=_aware(timestamp),
            settled_delta=0.0,
            unsettled_delta=0.0,
            strategy_id=strategy_id,
            position_id=position_id,
            metadata=dict(metadata or {}),
            **kwargs,
        )

    def snapshot(
        self,
        *,
        configuration: AccountConfiguration,
        postings: tuple[CashPosting, ...],
        as_of: datetime,
    ) -> CashBalanceSnapshot:
        as_of_ts = _aware(as_of)
        settled = float(configuration.settled_cash)
        unsettled = float(configuration.unsettled_cash)
        reserved = 0.0
        collateral = 0.0
        for posting in postings:
            if posting.effective_timestamp > as_of_ts:
                continue
            if posting.settlement_timestamp <= as_of_ts:
                settled += posting.settled_delta + posting.unsettled_delta
            else:
                unsettled += posting.unsettled_delta
                settled += posting.settled_delta
            reserved += posting.reserved_delta
            collateral += posting.collateral_delta
        free_cash = settled - reserved - collateral
        return CashBalanceSnapshot(
            as_of=as_of_ts,
            settled_cash=round(settled, 8),
            unsettled_cash=round(unsettled, 8),
            reserved_cash=round(reserved, 8),
            collateral_cash=round(collateral, 8),
            free_cash=round(free_cash, 8),
            net_cash=round(settled + unsettled, 8),
        )

    def account_state(
        self,
        *,
        configuration: AccountConfiguration,
        balance: CashBalanceSnapshot,
        buying_power: float,
        initial_requirement: float,
        maintenance_requirement: float,
    ) -> AccountState:
        excess = balance.net_cash - maintenance_requirement
        cushion = (
            0.0 if maintenance_requirement <= 0 else excess / maintenance_requirement
        )
        return AccountState(
            account_id=configuration.account_id,
            base_currency=configuration.base_currency,
            settled_cash=balance.settled_cash,
            unsettled_cash=balance.unsettled_cash,
            reserved_cash=balance.reserved_cash,
            collateral_cash=balance.collateral_cash,
            free_cash=balance.free_cash,
            buying_power=buying_power,
            initial_requirement=initial_requirement,
            maintenance_requirement=maintenance_requirement,
            excess_liquidity=round(excess, 8),
            cushion=round(cushion, 8),
            metadata={"account_type": configuration.account_type.value},
        )

    def _lag_days(self, event_type: CashEventType) -> int:
        mapping = {
            CashEventType.STOCK_PURCHASE: self.settlement_timing.equity_trade_days,
            CashEventType.STOCK_SALE: self.settlement_timing.equity_trade_days,
            CashEventType.PREMIUM_RECEIVED: self.settlement_timing.option_trade_days,
            CashEventType.PREMIUM_PAID: self.settlement_timing.option_trade_days,
            CashEventType.EXERCISE: self.settlement_timing.exercise_days,
            CashEventType.ASSIGNMENT: self.settlement_timing.assignment_days,
            CashEventType.DIVIDEND: self.settlement_timing.dividend_days,
            CashEventType.FEE: self.settlement_timing.fee_days,
            CashEventType.COMMISSION: self.settlement_timing.fee_days,
            CashEventType.INTEREST: self.settlement_timing.interest_days,
            CashEventType.BORROW_CHARGE: self.settlement_timing.borrow_days,
            CashEventType.LIQUIDATION: self.settlement_timing.equity_trade_days,
        }
        return mapping.get(event_type, 0)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
