"""Repositories for backtest margin, cash, borrow, and liquidation persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import Select, Table, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import (
    BacktestAccountConfigurationRecord,
    BacktestBorrowAccrualRecord,
    BacktestBorrowRecord,
    BacktestBrokerPolicyComparisonRecord,
    BacktestBuyingPowerSnapshotRecord,
    BacktestCashBalanceRecord,
    BacktestCashSettlementFlowRecord,
    BacktestCollateralRecord,
    BacktestInterestAccrualRecord,
    BacktestLiquidationOutcomeRecord,
    BacktestLiquidationPlanRecord,
    BacktestLiquidationStepRecord,
    BacktestMarginCalculationRecord,
    BacktestMarginCallEventRecord,
    BacktestMarginPolicyRecord,
    BacktestMarginReconciliationRecord,
    BacktestMarginReproducibilityChecksumRecord,
)

from .base import RepositoryBase


class _BulkRunScopedRepository(RepositoryBase[object]):
    model: type
    conflict_columns: tuple[str, ...]
    update_columns: tuple[str, ...]

    def upsert_rows(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        table = cast(Table, getattr(self.model, "__table__"))
        stmt = sqlite_insert(table).values(list(rows)).execution_options(dml_strategy="raw")
        index_elements = [getattr(table.c, key) for key in self.conflict_columns]
        set_payload = {key: getattr(stmt.excluded, key) for key in self.update_columns}
        self.session.execute(
            stmt.on_conflict_do_update(index_elements=index_elements, set_=set_payload)
        )


class BacktestAccountConfigurationRepository(_BulkRunScopedRepository):
    model = BacktestAccountConfigurationRecord
    conflict_columns = ("run_row_id", "account_id")
    update_columns = (
        "account_type",
        "base_currency",
        "starting_cash",
        "reserve_cash",
        "settled_cash",
        "unsettled_cash",
        "interest_policy_json",
        "margin_policy_json",
        "borrow_policy_json",
        "commission_fee_policy_json",
        "house_margin_overlay_json",
        "risk_limits_json",
        "liquidation_policy_json",
        "metadata",
    )


class BacktestMarginPolicyRepository(_BulkRunScopedRepository):
    model = BacktestMarginPolicyRecord
    conflict_columns = ("run_row_id", "account_id", "policy_name", "policy_version")
    update_columns = (
        "supported_account_types",
        "supported_instrument_types",
        "limitations",
        "metadata",
    )


class BacktestMarginCalculationRepository(_BulkRunScopedRepository):
    model = BacktestMarginCalculationRecord
    conflict_columns = ("run_row_id", "calculation_id")
    update_columns = (
        "account_id",
        "event_timestamp",
        "event_type",
        "policy_name",
        "policy_version",
        "strategy_id",
        "position_id",
        "initial_requirement",
        "maintenance_requirement",
        "option_buying_power_effect",
        "stock_buying_power_effect",
        "pending_order_reservation",
        "assignment_reservation",
        "exercise_reservation",
        "settlement_reservation",
        "concentration_add_ons",
        "event_risk_add_ons",
        "house_margin_add_ons",
        "post_trade_buying_power",
        "excess_liquidity",
        "cushion",
        "warnings",
        "diagnostics_json",
    )

    def history(self, *, run_row_id: int, account_id: str) -> list[BacktestMarginCalculationRecord]:
        stmt: Select[tuple[BacktestMarginCalculationRecord]] = (
            select(BacktestMarginCalculationRecord)
            .where(
                BacktestMarginCalculationRecord.run_row_id == run_row_id,
                BacktestMarginCalculationRecord.account_id == account_id,
            )
            .order_by(BacktestMarginCalculationRecord.event_timestamp.asc())
        )
        return list(self.session.execute(stmt).scalars())


class BacktestBuyingPowerSnapshotRepository(_BulkRunScopedRepository):
    model = BacktestBuyingPowerSnapshotRecord
    conflict_columns = ("run_row_id", "account_id", "event_timestamp")
    update_columns = (
        "available_buying_power",
        "initial_requirement",
        "maintenance_requirement",
        "excess_liquidity",
        "cushion",
        "free_cash",
        "settled_cash",
        "unsettled_cash",
        "reserved_cash",
        "collateral_cash",
        "diagnostics_json",
    )

    def as_of(
        self,
        *,
        run_row_id: int,
        account_id: str,
        as_of: datetime,
    ) -> BacktestBuyingPowerSnapshotRecord | None:
        stmt: Select[tuple[BacktestBuyingPowerSnapshotRecord]] = (
            select(BacktestBuyingPowerSnapshotRecord)
            .where(
                BacktestBuyingPowerSnapshotRecord.run_row_id == run_row_id,
                BacktestBuyingPowerSnapshotRecord.account_id == account_id,
                BacktestBuyingPowerSnapshotRecord.event_timestamp <= as_of,
            )
            .order_by(BacktestBuyingPowerSnapshotRecord.event_timestamp.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()


class BacktestCollateralRecordRepository(_BulkRunScopedRepository):
    model = BacktestCollateralRecord
    conflict_columns = (
        "run_row_id",
        "account_id",
        "event_timestamp",
        "position_id",
        "collateral_type",
    )
    update_columns = (
        "strategy_id",
        "amount",
        "covered",
        "warnings",
        "metadata",
    )


class BacktestCashBalanceRepository(_BulkRunScopedRepository):
    model = BacktestCashBalanceRecord
    conflict_columns = ("run_row_id", "account_id", "event_timestamp")
    update_columns = (
        "settled_cash",
        "unsettled_cash",
        "reserved_cash",
        "collateral_cash",
        "free_cash",
        "net_cash",
        "metadata",
    )

    def as_of(
        self,
        *,
        run_row_id: int,
        account_id: str,
        as_of: datetime,
    ) -> BacktestCashBalanceRecord | None:
        stmt: Select[tuple[BacktestCashBalanceRecord]] = (
            select(BacktestCashBalanceRecord)
            .where(
                BacktestCashBalanceRecord.run_row_id == run_row_id,
                BacktestCashBalanceRecord.account_id == account_id,
                BacktestCashBalanceRecord.event_timestamp <= as_of,
            )
            .order_by(BacktestCashBalanceRecord.event_timestamp.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def history(self, *, run_row_id: int, account_id: str) -> list[BacktestCashBalanceRecord]:
        stmt: Select[tuple[BacktestCashBalanceRecord]] = (
            select(BacktestCashBalanceRecord)
            .where(
                BacktestCashBalanceRecord.run_row_id == run_row_id,
                BacktestCashBalanceRecord.account_id == account_id,
            )
            .order_by(BacktestCashBalanceRecord.event_timestamp.asc())
        )
        return list(self.session.execute(stmt).scalars())


class BacktestCashSettlementFlowRepository(_BulkRunScopedRepository):
    model = BacktestCashSettlementFlowRecord
    conflict_columns = ("run_row_id", "posting_id")
    update_columns = (
        "account_id",
        "event_type",
        "amount",
        "trade_timestamp",
        "effective_timestamp",
        "settlement_timestamp",
        "settled_delta",
        "unsettled_delta",
        "reserved_delta",
        "collateral_delta",
        "strategy_id",
        "position_id",
        "metadata",
    )


class BacktestInterestAccrualRepository(_BulkRunScopedRepository):
    model = BacktestInterestAccrualRecord
    conflict_columns = ("run_row_id", "accrual_id")
    update_columns = (
        "account_id",
        "event_timestamp",
        "balance_basis",
        "annual_rate",
        "accrued_amount",
        "is_debit",
        "source_curve",
        "assumptions_json",
    )


class BacktestBorrowRecordRepository(_BulkRunScopedRepository):
    model = BacktestBorrowRecord
    conflict_columns = ("run_row_id", "borrow_id")
    update_columns = (
        "account_id",
        "symbol",
        "event_timestamp",
        "available",
        "annualized_rate",
        "hard_to_borrow",
        "locate_required",
        "buy_in_risk",
        "recall_risk",
        "warnings",
        "metadata",
    )


class BacktestBorrowAccrualRepository(_BulkRunScopedRepository):
    model = BacktestBorrowAccrualRecord
    conflict_columns = ("run_row_id", "accrual_id")
    update_columns = (
        "account_id",
        "symbol",
        "event_timestamp",
        "share_quantity",
        "annualized_rate",
        "accrued_amount",
        "hard_to_borrow",
        "warnings",
        "metadata",
    )


class BacktestMarginCallEventRepository(_BulkRunScopedRepository):
    model = BacktestMarginCallEventRecord
    conflict_columns = ("run_row_id", "call_id")
    update_columns = (
        "account_id",
        "event_timestamp",
        "reason",
        "severity",
        "amount_required",
        "deadline_placeholder",
        "diagnostics_json",
        "reason_codes",
    )

    def history(self, *, run_row_id: int, account_id: str) -> list[BacktestMarginCallEventRecord]:
        stmt: Select[tuple[BacktestMarginCallEventRecord]] = (
            select(BacktestMarginCallEventRecord)
            .where(
                BacktestMarginCallEventRecord.run_row_id == run_row_id,
                BacktestMarginCallEventRecord.account_id == account_id,
            )
            .order_by(BacktestMarginCallEventRecord.event_timestamp.asc())
        )
        return list(self.session.execute(stmt).scalars())


class BacktestLiquidationPlanRepository(_BulkRunScopedRepository):
    model = BacktestLiquidationPlanRecord
    conflict_columns = ("run_row_id", "plan_id")
    update_columns = (
        "account_id",
        "event_timestamp",
        "policy",
        "deficit_to_resolve",
        "strategy_preserving",
        "solved",
        "warnings",
        "diagnostics_json",
    )


class BacktestLiquidationStepRepository(_BulkRunScopedRepository):
    model = BacktestLiquidationStepRecord
    conflict_columns = ("run_row_id", "step_id")
    update_columns = (
        "plan_id",
        "strategy_id",
        "position_id",
        "quantity_fraction",
        "expected_margin_relief",
        "expected_cash_impact",
        "expected_realized_loss",
        "remaining_deficit",
        "warnings",
        "metadata",
    )


class BacktestLiquidationOutcomeRepository(_BulkRunScopedRepository):
    model = BacktestLiquidationOutcomeRecord
    conflict_columns = ("run_row_id", "plan_id", "event_timestamp")
    update_columns = (
        "realized_loss",
        "residual_margin_deficit",
        "residual_buying_power",
        "residual_excess_liquidity",
        "residual_stock_exposure",
        "residual_strategy_breakage",
        "residual_greeks_json",
        "warnings",
        "diagnostics_json",
    )


class BacktestBrokerPolicyComparisonRepository(_BulkRunScopedRepository):
    model = BacktestBrokerPolicyComparisonRecord
    conflict_columns = ("run_row_id", "comparison_id")
    update_columns = (
        "account_id",
        "event_timestamp",
        "left_policy",
        "right_policy",
        "initial_requirement_diff",
        "maintenance_requirement_diff",
        "buying_power_diff",
        "ambiguity_warnings",
        "diagnostics_json",
    )


class BacktestMarginReconciliationRepository(_BulkRunScopedRepository):
    model = BacktestMarginReconciliationRecord
    conflict_columns = ("run_row_id", "reconciliation_id")
    update_columns = (
        "account_id",
        "event_timestamp",
        "reconciled",
        "failure_codes",
        "diagnostics_json",
    )


class BacktestMarginReproducibilityChecksumRepository(_BulkRunScopedRepository):
    model = BacktestMarginReproducibilityChecksumRecord
    conflict_columns = ("run_row_id", "checksum_key")
    update_columns = ("checksum_value", "metadata")
