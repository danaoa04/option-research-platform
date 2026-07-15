"""Add Sprint 7B margin, cash, borrow, and liquidation persistence."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_margin_buying_power_liquidation_foundation"
down_revision = "0011_execution_settlement_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_account_configurations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("account_type", sa.String(length=64), nullable=False),
        sa.Column("base_currency", sa.String(length=16), nullable=False),
        sa.Column("starting_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("reserve_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("settled_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("unsettled_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("interest_policy_json", sa.JSON(), nullable=False),
        sa.Column("margin_policy_json", sa.JSON(), nullable=False),
        sa.Column("borrow_policy_json", sa.JSON(), nullable=False),
        sa.Column("commission_fee_policy_json", sa.JSON(), nullable=False),
        sa.Column("house_margin_overlay_json", sa.JSON(), nullable=False),
        sa.Column("risk_limits_json", sa.JSON(), nullable=False),
        sa.Column("liquidation_policy_json", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "account_id"),
    )
    op.create_index(
        "ix_backtest_account_configs_run",
        "backtest_account_configurations",
        ["run_row_id", "account_id"],
    )

    op.create_table(
        "backtest_margin_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("policy_name", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("supported_account_types", sa.JSON(), nullable=False),
        sa.Column("supported_instrument_types", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "account_id", "policy_name", "policy_version"),
    )
    op.create_index(
        "ix_backtest_margin_policies_run",
        "backtest_margin_policies",
        ["run_row_id", "account_id"],
    )

    op.create_table(
        "backtest_margin_calculations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("calculation_id", sa.String(length=128), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("policy_name", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=True),
        sa.Column("position_id", sa.String(length=128), nullable=True),
        sa.Column("initial_requirement", sa.Numeric(20, 8), nullable=False),
        sa.Column("maintenance_requirement", sa.Numeric(20, 8), nullable=False),
        sa.Column("option_buying_power_effect", sa.Numeric(20, 8), nullable=False),
        sa.Column("stock_buying_power_effect", sa.Numeric(20, 8), nullable=False),
        sa.Column("pending_order_reservation", sa.Numeric(20, 8), nullable=False),
        sa.Column("assignment_reservation", sa.Numeric(20, 8), nullable=False),
        sa.Column("exercise_reservation", sa.Numeric(20, 8), nullable=False),
        sa.Column("settlement_reservation", sa.Numeric(20, 8), nullable=False),
        sa.Column("concentration_add_ons", sa.Numeric(20, 8), nullable=False),
        sa.Column("event_risk_add_ons", sa.Numeric(20, 8), nullable=False),
        sa.Column("house_margin_add_ons", sa.Numeric(20, 8), nullable=False),
        sa.Column("post_trade_buying_power", sa.Numeric(20, 8), nullable=False),
        sa.Column("excess_liquidity", sa.Numeric(20, 8), nullable=False),
        sa.Column("cushion", sa.Numeric(20, 8), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "calculation_id"),
    )
    op.create_index(
        "ix_backtest_margin_calculations_run_ts",
        "backtest_margin_calculations",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_buying_power_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_buying_power", sa.Numeric(20, 8), nullable=False),
        sa.Column("initial_requirement", sa.Numeric(20, 8), nullable=False),
        sa.Column("maintenance_requirement", sa.Numeric(20, 8), nullable=False),
        sa.Column("excess_liquidity", sa.Numeric(20, 8), nullable=False),
        sa.Column("cushion", sa.Numeric(20, 8), nullable=False),
        sa.Column("free_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("settled_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("unsettled_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("reserved_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("collateral_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "account_id", "event_timestamp"),
    )
    op.create_index(
        "ix_backtest_buying_power_snapshots_run_ts",
        "backtest_buying_power_snapshots",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_collateral_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=True),
        sa.Column("position_id", sa.String(length=128), nullable=True),
        sa.Column("collateral_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("covered", sa.Boolean(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "run_row_id",
            "account_id",
            "event_timestamp",
            "position_id",
            "collateral_type",
        ),
    )
    op.create_index(
        "ix_backtest_collateral_records_run_ts",
        "backtest_collateral_records",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_cash_balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("unsettled_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("reserved_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("collateral_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("free_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("net_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "account_id", "event_timestamp"),
    )
    op.create_index(
        "ix_backtest_cash_balances_run_ts",
        "backtest_cash_balances",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_cash_settlement_flows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("posting_id", sa.String(length=128), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("trade_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settlement_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_delta", sa.Numeric(20, 8), nullable=False),
        sa.Column("unsettled_delta", sa.Numeric(20, 8), nullable=False),
        sa.Column("reserved_delta", sa.Numeric(20, 8), nullable=False),
        sa.Column("collateral_delta", sa.Numeric(20, 8), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=True),
        sa.Column("position_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "posting_id"),
    )
    op.create_index(
        "ix_backtest_cash_settlement_flows_run_ts",
        "backtest_cash_settlement_flows",
        ["run_row_id", "settlement_timestamp"],
    )

    op.create_table(
        "backtest_interest_accruals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("accrual_id", sa.String(length=128), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("balance_basis", sa.Numeric(20, 8), nullable=False),
        sa.Column("annual_rate", sa.Numeric(20, 10), nullable=False),
        sa.Column("accrued_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("is_debit", sa.Boolean(), nullable=False),
        sa.Column("source_curve", sa.String(length=128), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "accrual_id"),
    )
    op.create_index(
        "ix_backtest_interest_accruals_run_ts",
        "backtest_interest_accruals",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_borrow_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("borrow_id", sa.String(length=128), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("annualized_rate", sa.Numeric(20, 10), nullable=False),
        sa.Column("hard_to_borrow", sa.Boolean(), nullable=False),
        sa.Column("locate_required", sa.Boolean(), nullable=False),
        sa.Column("buy_in_risk", sa.Numeric(20, 8), nullable=False),
        sa.Column("recall_risk", sa.Numeric(20, 8), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "borrow_id"),
    )
    op.create_index(
        "ix_backtest_borrow_records_run_ts",
        "backtest_borrow_records",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_borrow_accruals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("accrual_id", sa.String(length=128), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("share_quantity", sa.Integer(), nullable=False),
        sa.Column("annualized_rate", sa.Numeric(20, 10), nullable=False),
        sa.Column("accrued_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("hard_to_borrow", sa.Boolean(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "accrual_id"),
    )
    op.create_index(
        "ix_backtest_borrow_accruals_run_ts",
        "backtest_borrow_accruals",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_margin_call_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("call_id", sa.String(length=128), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("amount_required", sa.Numeric(20, 8), nullable=False),
        sa.Column("deadline_placeholder", sa.String(length=64), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "call_id"),
    )
    op.create_index(
        "ix_backtest_margin_call_events_run_ts",
        "backtest_margin_call_events",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_liquidation_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("plan_id", sa.String(length=128), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy", sa.String(length=128), nullable=False),
        sa.Column("deficit_to_resolve", sa.Numeric(20, 8), nullable=False),
        sa.Column("strategy_preserving", sa.Boolean(), nullable=False),
        sa.Column("solved", sa.Boolean(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "plan_id"),
    )
    op.create_index(
        "ix_backtest_liquidation_plans_run_ts",
        "backtest_liquidation_plans",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_liquidation_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("plan_id", sa.String(length=128), nullable=False),
        sa.Column("step_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("quantity_fraction", sa.Numeric(20, 8), nullable=False),
        sa.Column("expected_margin_relief", sa.Numeric(20, 8), nullable=False),
        sa.Column("expected_cash_impact", sa.Numeric(20, 8), nullable=False),
        sa.Column("expected_realized_loss", sa.Numeric(20, 8), nullable=False),
        sa.Column("remaining_deficit", sa.Numeric(20, 8), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "step_id"),
    )
    op.create_index(
        "ix_backtest_liquidation_steps_run",
        "backtest_liquidation_steps",
        ["run_row_id", "plan_id"],
    )

    op.create_table(
        "backtest_liquidation_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("plan_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("realized_loss", sa.Numeric(20, 8), nullable=False),
        sa.Column("residual_margin_deficit", sa.Numeric(20, 8), nullable=False),
        sa.Column("residual_buying_power", sa.Numeric(20, 8), nullable=False),
        sa.Column("residual_excess_liquidity", sa.Numeric(20, 8), nullable=False),
        sa.Column("residual_stock_exposure", sa.Numeric(20, 8), nullable=False),
        sa.Column("residual_strategy_breakage", sa.Boolean(), nullable=False),
        sa.Column("residual_greeks_json", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "plan_id", "event_timestamp"),
    )
    op.create_index(
        "ix_backtest_liquidation_outcomes_run_ts",
        "backtest_liquidation_outcomes",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_broker_policy_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("comparison_id", sa.String(length=128), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_policy", sa.String(length=128), nullable=False),
        sa.Column("right_policy", sa.String(length=128), nullable=False),
        sa.Column("initial_requirement_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("maintenance_requirement_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("buying_power_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("ambiguity_warnings", sa.JSON(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "comparison_id"),
    )
    op.create_index(
        "ix_backtest_policy_comparisons_run_ts",
        "backtest_broker_policy_comparisons",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_margin_reconciliations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("reconciliation_id", sa.String(length=128), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reconciled", sa.Boolean(), nullable=False),
        sa.Column("failure_codes", sa.JSON(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "reconciliation_id"),
    )
    op.create_index(
        "ix_backtest_margin_reconciliations_run_ts",
        "backtest_margin_reconciliations",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_margin_reproducibility_checksums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("checksum_key", sa.String(length=128), nullable=False),
        sa.Column("checksum_value", sa.String(length=256), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "checksum_key"),
    )
    op.create_index(
        "ix_backtest_margin_repro_checksums_run",
        "backtest_margin_reproducibility_checksums",
        ["run_row_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_backtest_margin_repro_checksums_run",
        table_name="backtest_margin_reproducibility_checksums",
    )
    op.drop_table("backtest_margin_reproducibility_checksums")

    op.drop_index(
        "ix_backtest_margin_reconciliations_run_ts",
        table_name="backtest_margin_reconciliations",
    )
    op.drop_table("backtest_margin_reconciliations")

    op.drop_index(
        "ix_backtest_policy_comparisons_run_ts",
        table_name="backtest_broker_policy_comparisons",
    )
    op.drop_table("backtest_broker_policy_comparisons")

    op.drop_index(
        "ix_backtest_liquidation_outcomes_run_ts",
        table_name="backtest_liquidation_outcomes",
    )
    op.drop_table("backtest_liquidation_outcomes")

    op.drop_index(
        "ix_backtest_liquidation_steps_run",
        table_name="backtest_liquidation_steps",
    )
    op.drop_table("backtest_liquidation_steps")

    op.drop_index(
        "ix_backtest_liquidation_plans_run_ts",
        table_name="backtest_liquidation_plans",
    )
    op.drop_table("backtest_liquidation_plans")

    op.drop_index(
        "ix_backtest_margin_call_events_run_ts",
        table_name="backtest_margin_call_events",
    )
    op.drop_table("backtest_margin_call_events")

    op.drop_index(
        "ix_backtest_borrow_accruals_run_ts",
        table_name="backtest_borrow_accruals",
    )
    op.drop_table("backtest_borrow_accruals")

    op.drop_index(
        "ix_backtest_borrow_records_run_ts",
        table_name="backtest_borrow_records",
    )
    op.drop_table("backtest_borrow_records")

    op.drop_index(
        "ix_backtest_interest_accruals_run_ts",
        table_name="backtest_interest_accruals",
    )
    op.drop_table("backtest_interest_accruals")

    op.drop_index(
        "ix_backtest_cash_settlement_flows_run_ts",
        table_name="backtest_cash_settlement_flows",
    )
    op.drop_table("backtest_cash_settlement_flows")

    op.drop_index(
        "ix_backtest_cash_balances_run_ts",
        table_name="backtest_cash_balances",
    )
    op.drop_table("backtest_cash_balances")

    op.drop_index(
        "ix_backtest_collateral_records_run_ts",
        table_name="backtest_collateral_records",
    )
    op.drop_table("backtest_collateral_records")

    op.drop_index(
        "ix_backtest_buying_power_snapshots_run_ts",
        table_name="backtest_buying_power_snapshots",
    )
    op.drop_table("backtest_buying_power_snapshots")

    op.drop_index(
        "ix_backtest_margin_calculations_run_ts",
        table_name="backtest_margin_calculations",
    )
    op.drop_table("backtest_margin_calculations")

    op.drop_index(
        "ix_backtest_margin_policies_run",
        table_name="backtest_margin_policies",
    )
    op.drop_table("backtest_margin_policies")

    op.drop_index(
        "ix_backtest_account_configs_run",
        table_name="backtest_account_configurations",
    )
    op.drop_table("backtest_account_configurations")
