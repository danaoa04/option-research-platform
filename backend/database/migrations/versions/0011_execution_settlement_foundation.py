"""Add Sprint 7A execution, exercise/assignment, and settlement persistence."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_execution_settlement_foundation"
down_revision = "0010_backtest_analytics_replay_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_execution_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("leg_id", sa.String(length=128), nullable=False),
        sa.Column("contract_identifier", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("effect", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("requested_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("order_type", sa.String(length=32), nullable=False),
        sa.Column("limit_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("mark_price_policy", sa.String(length=64), nullable=False),
        sa.Column("execution_delay_policy", sa.JSON(), nullable=False),
        sa.Column("fill_model_policy", sa.JSON(), nullable=False),
        sa.Column("slippage_policy", sa.JSON(), nullable=False),
        sa.Column("commission_policy", sa.JSON(), nullable=False),
        sa.Column("exchange_fee_policy", sa.JSON(), nullable=False),
        sa.Column("minimum_fill_quantity", sa.Integer(), nullable=False),
        sa.Column("all_or_none_research", sa.Boolean(), nullable=False),
        sa.Column("maximum_legging_delay_seconds", sa.Numeric(20, 8), nullable=False),
        sa.Column("lifecycle_trigger", sa.String(length=128), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("dataset_manifest", sa.String(length=256), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "request_id"),
    )
    op.create_index(
        "ix_backtest_execution_requests_run_ts",
        "backtest_execution_requests",
        ["run_row_id", "requested_timestamp"],
    )

    op.create_table(
        "backtest_quote_selections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("selected_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quote_age_seconds", sa.Numeric(20, 8), nullable=True),
        sa.Column("spread_width", sa.Numeric(20, 8), nullable=True),
        sa.Column("selected_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("quality_flags", sa.JSON(), nullable=False),
        sa.Column("stale_data", sa.Boolean(), nullable=False),
        sa.Column("crossed_market", sa.Boolean(), nullable=False),
        sa.Column("source_manifest", sa.String(length=256), nullable=True),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "request_id"),
    )
    op.create_index(
        "ix_backtest_quote_selections_run",
        "backtest_quote_selections",
        ["run_row_id", "selected_timestamp"],
    )

    op.create_table(
        "backtest_fill_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("attempt_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fill_model", sa.String(length=64), nullable=False),
        sa.Column("requested_quantity", sa.Integer(), nullable=False),
        sa.Column("filled_quantity", sa.Integer(), nullable=False),
        sa.Column("remaining_quantity", sa.Integer(), nullable=False),
        sa.Column("fill_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("slippage", sa.Numeric(20, 8), nullable=False),
        sa.Column("spread_capture", sa.Numeric(20, 8), nullable=True),
        sa.Column("quote_quality", sa.Numeric(20, 8), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("failure_reason", sa.String(length=128), nullable=True),
        sa.UniqueConstraint("run_row_id", "request_id", "attempt_timestamp"),
    )
    op.create_index(
        "ix_backtest_fill_attempts_run",
        "backtest_fill_attempts",
        ["run_row_id", "attempt_timestamp"],
    )

    op.create_table(
        "backtest_execution_fills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("fill_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fill_quantity", sa.Integer(), nullable=False),
        sa.Column("fill_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "request_id", "fill_timestamp"),
    )
    op.create_index(
        "ix_backtest_execution_fills_run",
        "backtest_execution_fills",
        ["run_row_id", "fill_timestamp"],
    )

    op.create_table(
        "backtest_fee_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fee_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "request_id", "event_timestamp", "fee_type"),
    )
    op.create_index(
        "ix_backtest_fee_items_run",
        "backtest_fee_items",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_exercise_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("decision_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column("rationale", sa.String(length=256), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "request_id", "decision_timestamp"),
    )
    op.create_index(
        "ix_backtest_exercise_decisions_run",
        "backtest_exercise_decisions",
        ["run_row_id", "decision_timestamp"],
    )

    op.create_table(
        "backtest_assignment_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("decision_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column("partial_assignment", sa.Boolean(), nullable=False),
        sa.Column("assignment_quantity", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.String(length=256), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "request_id", "decision_timestamp"),
    )
    op.create_index(
        "ix_backtest_assignment_decisions_run",
        "backtest_assignment_decisions",
        ["run_row_id", "decision_timestamp"],
    )

    op.create_table(
        "backtest_expiration_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("expiration_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("intrinsic_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("in_the_money", sa.Boolean(), nullable=False),
        sa.Column("cash_settled", sa.Boolean(), nullable=False),
        sa.Column("physically_settled", sa.Boolean(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "request_id", "expiration_timestamp"),
    )
    op.create_index(
        "ix_backtest_expiration_events_run",
        "backtest_expiration_events",
        ["run_row_id", "expiration_timestamp"],
    )

    op.create_table(
        "backtest_physical_settlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("settlement_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stock_position_change", sa.Integer(), nullable=False),
        sa.Column("strike_cash_movement", sa.Numeric(20, 8), nullable=False),
        sa.Column("fees", sa.Numeric(20, 8), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "request_id", "settlement_timestamp"),
    )
    op.create_index(
        "ix_backtest_physical_settlements_run",
        "backtest_physical_settlements",
        ["run_row_id", "settlement_timestamp"],
    )

    op.create_table(
        "backtest_cash_settlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("settlement_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cash_movement", sa.Numeric(20, 8), nullable=False),
        sa.Column("fees", sa.Numeric(20, 8), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "request_id", "settlement_timestamp"),
    )
    op.create_index(
        "ix_backtest_cash_settlements_run",
        "backtest_cash_settlements",
        ["run_row_id", "settlement_timestamp"],
    )

    op.create_table(
        "backtest_dividend_settlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("ex_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("record_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payable_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("special_dividend", sa.Boolean(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "strategy_id", "position_id", "ex_date"),
    )
    op.create_index(
        "ix_backtest_dividend_settlements_run",
        "backtest_dividend_settlements",
        ["run_row_id", "ex_date"],
    )

    op.create_table(
        "backtest_stock_positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("cost_basis", sa.Numeric(20, 8), nullable=False),
        sa.Column("as_of_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "run_row_id",
            "symbol",
            "strategy_id",
            "position_id",
            "as_of_timestamp",
        ),
    )
    op.create_index(
        "ix_backtest_stock_positions_run",
        "backtest_stock_positions",
        ["run_row_id", "as_of_timestamp"],
    )

    op.create_table(
        "backtest_cost_basis_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_cycle_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("option_cost_basis", sa.Numeric(20, 8), nullable=False),
        sa.Column("stock_cost_basis", sa.Numeric(20, 8), nullable=False),
        sa.Column("cumulative_debits", sa.Numeric(20, 8), nullable=False),
        sa.Column("cumulative_credits", sa.Numeric(20, 8), nullable=False),
        sa.Column("cumulative_fees", sa.Numeric(20, 8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("as_of_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "strategy_cycle_id", "as_of_timestamp"),
    )
    op.create_index(
        "ix_backtest_cost_basis_records_run",
        "backtest_cost_basis_records",
        ["run_row_id", "as_of_timestamp"],
    )

    op.create_table(
        "backtest_ledger_postings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("posting_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("posting_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "posting_id"),
    )
    op.create_index(
        "ix_backtest_ledger_postings_run",
        "backtest_ledger_postings",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_pin_risk_diagnostics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("at_risk", sa.Boolean(), nullable=False),
        sa.Column("within_band", sa.Boolean(), nullable=False),
        sa.Column("warning_codes", sa.JSON(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "request_id", "event_timestamp"),
    )
    op.create_index(
        "ix_backtest_pin_risk_diagnostics_run",
        "backtest_pin_risk_diagnostics",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_settlement_reconciliation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reconciled", sa.Boolean(), nullable=False),
        sa.Column("failure_codes", sa.JSON(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "strategy_id", "position_id", "event_timestamp"),
    )
    op.create_index(
        "ix_backtest_settlement_reconciliation_run",
        "backtest_settlement_reconciliation",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_execution_reproducibility_checksums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("checksum_key", sa.String(length=128), nullable=False),
        sa.Column("checksum_value", sa.String(length=256), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "checksum_key"),
    )
    op.create_index(
        "ix_backtest_execution_repro_checksums_run",
        "backtest_execution_reproducibility_checksums",
        ["run_row_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_backtest_execution_repro_checksums_run",
        table_name="backtest_execution_reproducibility_checksums",
    )
    op.drop_table("backtest_execution_reproducibility_checksums")

    op.drop_index(
        "ix_backtest_settlement_reconciliation_run",
        table_name="backtest_settlement_reconciliation",
    )
    op.drop_table("backtest_settlement_reconciliation")

    op.drop_index(
        "ix_backtest_pin_risk_diagnostics_run",
        table_name="backtest_pin_risk_diagnostics",
    )
    op.drop_table("backtest_pin_risk_diagnostics")

    op.drop_index("ix_backtest_ledger_postings_run", table_name="backtest_ledger_postings")
    op.drop_table("backtest_ledger_postings")

    op.drop_index(
        "ix_backtest_cost_basis_records_run",
        table_name="backtest_cost_basis_records",
    )
    op.drop_table("backtest_cost_basis_records")

    op.drop_index("ix_backtest_stock_positions_run", table_name="backtest_stock_positions")
    op.drop_table("backtest_stock_positions")

    op.drop_index(
        "ix_backtest_dividend_settlements_run",
        table_name="backtest_dividend_settlements",
    )
    op.drop_table("backtest_dividend_settlements")

    op.drop_index(
        "ix_backtest_cash_settlements_run",
        table_name="backtest_cash_settlements",
    )
    op.drop_table("backtest_cash_settlements")

    op.drop_index(
        "ix_backtest_physical_settlements_run",
        table_name="backtest_physical_settlements",
    )
    op.drop_table("backtest_physical_settlements")

    op.drop_index(
        "ix_backtest_expiration_events_run",
        table_name="backtest_expiration_events",
    )
    op.drop_table("backtest_expiration_events")

    op.drop_index(
        "ix_backtest_assignment_decisions_run",
        table_name="backtest_assignment_decisions",
    )
    op.drop_table("backtest_assignment_decisions")

    op.drop_index(
        "ix_backtest_exercise_decisions_run",
        table_name="backtest_exercise_decisions",
    )
    op.drop_table("backtest_exercise_decisions")

    op.drop_index("ix_backtest_fee_items_run", table_name="backtest_fee_items")
    op.drop_table("backtest_fee_items")

    op.drop_index("ix_backtest_execution_fills_run", table_name="backtest_execution_fills")
    op.drop_table("backtest_execution_fills")

    op.drop_index("ix_backtest_fill_attempts_run", table_name="backtest_fill_attempts")
    op.drop_table("backtest_fill_attempts")

    op.drop_index("ix_backtest_quote_selections_run", table_name="backtest_quote_selections")
    op.drop_table("backtest_quote_selections")

    op.drop_index(
        "ix_backtest_execution_requests_run_ts",
        table_name="backtest_execution_requests",
    )
    op.drop_table("backtest_execution_requests")
