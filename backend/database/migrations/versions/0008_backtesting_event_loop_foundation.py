"""Add Sprint 6A deterministic backtesting persistence foundation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_backtesting_event_loop_foundation"
down_revision = "0007_portfolio_selection_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_name", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reproducibility_json", sa.JSON(), nullable=False),
        sa.Column("checksums", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("software_git_commit", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        "ix_backtest_runs_strategy_ts",
        "backtest_runs",
        ["strategy_name", "created_at"],
    )

    op.create_table(
        "backtest_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=True),
        sa.Column("manifest_reference", sa.String(length=256), nullable=True),
        sa.Column("software_version", sa.String(length=64), nullable=True),
        sa.Column("checksum_metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "sequence_number", "event_type"),
    )
    op.create_index(
        "ix_backtest_events_run_ts",
        "backtest_events",
        ["run_row_id", "event_timestamp"],
    )
    op.create_index("ix_backtest_events_type", "backtest_events", ["event_type"])

    op.create_table(
        "backtest_order_intents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("intent_id", sa.String(length=128), nullable=False),
        sa.Column("requested_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("asset_type", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("contract_identifier", sa.String(length=128), nullable=False),
        sa.Column("price_policy", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_trigger", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "intent_id"),
    )
    op.create_index(
        "ix_backtest_order_intents_run_ts",
        "backtest_order_intents",
        ["run_row_id", "requested_timestamp"],
    )

    op.create_table(
        "backtest_research_fills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("intent_id", sa.String(length=128), nullable=False),
        sa.Column("fill_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("filled", sa.Boolean(), nullable=False),
        sa.Column("fill_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "intent_id"),
    )
    op.create_index(
        "ix_backtest_research_fills_run_ts",
        "backtest_research_fills",
        ["run_row_id", "fill_timestamp"],
    )

    op.create_table(
        "backtest_positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("as_of_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "position_id", "as_of_timestamp"),
    )
    op.create_index(
        "ix_backtest_positions_run_ts",
        "backtest_positions",
        ["run_row_id", "as_of_timestamp"],
    )

    op.create_table(
        "backtest_position_legs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("leg_id", sa.String(length=128), nullable=False),
        sa.Column("contract_identifier", sa.String(length=128), nullable=False),
        sa.Column("asset_type", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("strike", sa.Numeric(20, 8), nullable=True),
        sa.Column("expiration", sa.Date(), nullable=True),
        sa.Column("option_type", sa.String(length=8), nullable=True),
        sa.Column("exercise_style", sa.String(length=16), nullable=True),
        sa.Column("entry_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("current_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("implied_volatility", sa.Numeric(20, 10), nullable=True),
        sa.Column("realised_volatility", sa.Numeric(20, 10), nullable=True),
        sa.Column("pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("capital_usage", sa.Numeric(20, 8), nullable=False),
        sa.Column("data_quality_flags", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("as_of_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id", "position_id", "leg_id", "as_of_timestamp"),
    )
    op.create_index(
        "ix_backtest_position_legs_run_ts",
        "backtest_position_legs",
        ["run_row_id", "as_of_timestamp"],
    )

    op.create_table(
        "backtest_valuations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("valuation_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("leg_id", sa.String(length=128), nullable=True),
        sa.Column("mark_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("market_source", sa.String(length=64), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "valuation_timestamp", "position_id", "leg_id"),
    )
    op.create_index(
        "ix_backtest_valuations_run_ts",
        "backtest_valuations",
        ["run_row_id", "valuation_timestamp"],
    )

    op.create_table(
        "backtest_cash_ledger_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("entry_index", sa.Integer(), nullable=False),
        sa.Column("entry_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("balance_after", sa.Numeric(20, 8), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "entry_index"),
    )
    op.create_index(
        "ix_backtest_cash_ledger_run_ts",
        "backtest_cash_ledger_entries",
        ["run_row_id", "entry_timestamp"],
    )

    op.create_table(
        "backtest_portfolio_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("snapshot_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cash_balance", sa.Numeric(20, 8), nullable=False),
        sa.Column("reserved_capital", sa.Numeric(20, 8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("accrued_fees", sa.Numeric(20, 8), nullable=False),
        sa.Column("dividends", sa.Numeric(20, 8), nullable=False),
        sa.Column("portfolio_greeks", sa.JSON(), nullable=False),
        sa.Column("portfolio_exposure", sa.JSON(), nullable=False),
        sa.Column("capital_utilization", sa.Numeric(20, 10), nullable=False),
        sa.UniqueConstraint("run_row_id", "snapshot_timestamp"),
    )
    op.create_index(
        "ix_backtest_snapshots_run_ts",
        "backtest_portfolio_snapshots",
        ["run_row_id", "snapshot_timestamp"],
    )

    op.create_table(
        "backtest_lifecycle_triggers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("trigger_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("trigger", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("information_set", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "trigger_timestamp", "position_id", "trigger"),
    )
    op.create_index(
        "ix_backtest_lifecycle_run_ts",
        "backtest_lifecycle_triggers",
        ["run_row_id", "trigger_timestamp"],
    )

    op.create_table(
        "backtest_run_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("left_run_id", sa.String(length=128), nullable=False),
        sa.Column("right_run_id", sa.String(length=128), nullable=False),
        sa.Column("comparison_key_checksum", sa.String(length=128), nullable=False),
        sa.Column("comparison_payload", sa.JSON(), nullable=False),
        sa.Column("chart_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("left_run_id", "right_run_id", "comparison_key_checksum"),
    )
    op.create_index(
        "ix_backtest_run_comparisons_pair",
        "backtest_run_comparisons",
        ["left_run_id", "right_run_id"],
    )

    op.create_table(
        "backtest_scenario_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("scenario_name", sa.String(length=128), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "scenario_name"),
    )
    op.create_index(
        "ix_backtest_scenario_results_run",
        "backtest_scenario_results",
        ["run_row_id", "scenario_name"],
    )

    op.create_table(
        "backtest_reproducibility_checksums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("checksum_key", sa.String(length=128), nullable=False),
        sa.Column("checksum_value", sa.String(length=256), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "checksum_key"),
    )
    op.create_index(
        "ix_backtest_repro_checksums_run",
        "backtest_reproducibility_checksums",
        ["run_row_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_backtest_repro_checksums_run",
        table_name="backtest_reproducibility_checksums",
    )
    op.drop_table("backtest_reproducibility_checksums")

    op.drop_index("ix_backtest_scenario_results_run", table_name="backtest_scenario_results")
    op.drop_table("backtest_scenario_results")

    op.drop_index("ix_backtest_run_comparisons_pair", table_name="backtest_run_comparisons")
    op.drop_table("backtest_run_comparisons")

    op.drop_index("ix_backtest_lifecycle_run_ts", table_name="backtest_lifecycle_triggers")
    op.drop_table("backtest_lifecycle_triggers")

    op.drop_index("ix_backtest_snapshots_run_ts", table_name="backtest_portfolio_snapshots")
    op.drop_table("backtest_portfolio_snapshots")

    op.drop_index("ix_backtest_cash_ledger_run_ts", table_name="backtest_cash_ledger_entries")
    op.drop_table("backtest_cash_ledger_entries")

    op.drop_index("ix_backtest_valuations_run_ts", table_name="backtest_valuations")
    op.drop_table("backtest_valuations")

    op.drop_index("ix_backtest_position_legs_run_ts", table_name="backtest_position_legs")
    op.drop_table("backtest_position_legs")

    op.drop_index("ix_backtest_positions_run_ts", table_name="backtest_positions")
    op.drop_table("backtest_positions")

    op.drop_index("ix_backtest_research_fills_run_ts", table_name="backtest_research_fills")
    op.drop_table("backtest_research_fills")

    op.drop_index("ix_backtest_order_intents_run_ts", table_name="backtest_order_intents")
    op.drop_table("backtest_order_intents")

    op.drop_index("ix_backtest_events_type", table_name="backtest_events")
    op.drop_index("ix_backtest_events_run_ts", table_name="backtest_events")
    op.drop_table("backtest_events")

    op.drop_index("ix_backtest_runs_strategy_ts", table_name="backtest_runs")
    op.drop_table("backtest_runs")
