"""Add Sprint 6C backtest analytics, reconstruction, and replay persistence."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_backtest_analytics_replay_foundation"
down_revision = "0009_strategy_state_machine_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_strategy_analytics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("snapshot_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("total_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("return_value", sa.Numeric(20, 10), nullable=False),
        sa.Column("capital_usage", sa.Numeric(20, 8), nullable=False),
        sa.Column("cash_usage", sa.Numeric(20, 8), nullable=False),
        sa.Column("intrinsic_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("extrinsic_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("greeks", sa.JSON(), nullable=False),
        sa.Column("implied_volatility", sa.Numeric(20, 10), nullable=True),
        sa.Column("realized_volatility", sa.Numeric(20, 10), nullable=True),
        sa.Column("iv_rank", sa.Numeric(20, 10), nullable=True),
        sa.Column("iv_percentile", sa.Numeric(20, 10), nullable=True),
        sa.Column("term_structure_json", sa.JSON(), nullable=False),
        sa.Column("liquidity_json", sa.JSON(), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=64), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "strategy_instance_id", "snapshot_timestamp"),
    )
    op.create_index(
        "ix_backtest_strategy_analytics_run_ts",
        "backtest_strategy_analytics",
        ["run_row_id", "snapshot_timestamp"],
    )

    op.create_table(
        "backtest_portfolio_analytics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("snapshot_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equity", sa.Numeric(20, 8), nullable=False),
        sa.Column("cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("reserved_capital", sa.Numeric(20, 8), nullable=False),
        sa.Column("capital_utilization", sa.Numeric(20, 10), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("greeks", sa.JSON(), nullable=False),
        sa.Column("exposures_json", sa.JSON(), nullable=False),
        sa.Column("risk_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "snapshot_timestamp"),
    )
    op.create_index(
        "ix_backtest_portfolio_analytics_run_ts",
        "backtest_portfolio_analytics",
        ["run_row_id", "snapshot_timestamp"],
    )

    op.create_table(
        "backtest_pnl_attribution",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("snapshot_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("factors_json", sa.JSON(), nullable=False),
        sa.Column("approximation", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("run_row_id", "strategy_instance_id", "snapshot_timestamp"),
    )
    op.create_index(
        "ix_backtest_pnl_attribution_run_ts",
        "backtest_pnl_attribution",
        ["run_row_id", "snapshot_timestamp"],
    )

    op.create_table(
        "backtest_greeks_attribution",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("snapshot_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("greek_changes", sa.JSON(), nullable=False),
        sa.Column("attributable_to", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "strategy_instance_id", "snapshot_timestamp"),
    )
    op.create_index(
        "ix_backtest_greeks_attribution_run_ts",
        "backtest_greeks_attribution",
        ["run_row_id", "snapshot_timestamp"],
    )

    op.create_table(
        "backtest_reconstructed_trades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("trade_id", sa.String(length=256), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("lifecycle_json", sa.JSON(), nullable=False),
        sa.Column("cash_movements", sa.Numeric(20, 8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("fees", sa.Numeric(20, 8), nullable=False),
        sa.Column("final_state", sa.String(length=64), nullable=False),
        sa.Column("source_event_ids", sa.JSON(), nullable=False),
        sa.Column("source_checksums", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "trade_id"),
    )
    op.create_index(
        "ix_backtest_reconstructed_trades_run",
        "backtest_reconstructed_trades",
        ["run_row_id", "strategy_id"],
    )

    op.create_table(
        "backtest_strategy_cycles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("cycle_id", sa.String(length=256), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("initial_position", sa.String(length=128), nullable=False),
        sa.Column("child_positions", sa.JSON(), nullable=False),
        sa.Column("roll_chain", sa.JSON(), nullable=False),
        sa.Column("cumulative_debit_credit", sa.Numeric(20, 8), nullable=False),
        sa.Column("cumulative_fees", sa.Numeric(20, 8), nullable=False),
        sa.Column("cumulative_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("maximum_capital_usage", sa.Numeric(20, 8), nullable=False),
        sa.Column("total_holding_duration_seconds", sa.Numeric(20, 8), nullable=False),
        sa.Column("final_result", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_reasons", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "cycle_id"),
    )
    op.create_index(
        "ix_backtest_strategy_cycles_run",
        "backtest_strategy_cycles",
        ["run_row_id", "strategy_id"],
    )

    op.create_table(
        "backtest_replay_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("cursor", sa.Integer(), nullable=False),
        sa.Column("snapshot_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("source_checksums", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "snapshot_id"),
    )
    op.create_index(
        "ix_backtest_replay_snapshots_run_ts",
        "backtest_replay_snapshots",
        ["run_row_id", "snapshot_timestamp"],
    )

    op.create_table(
        "backtest_event_overlays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("event_sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("effective_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overlay_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "event_sequence_number"),
    )
    op.create_index(
        "ix_backtest_event_overlays_run",
        "backtest_event_overlays",
        ["run_row_id", "event_type"],
    )

    op.create_table(
        "backtest_arbitration_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("decision_id", sa.String(length=128), nullable=False),
        sa.Column("decision_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy", sa.String(length=64), nullable=False),
        sa.Column("accepted_actions", sa.JSON(), nullable=False),
        sa.Column("rejected_actions", sa.JSON(), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "decision_id"),
    )
    op.create_index(
        "ix_backtest_arbitration_decisions_run_ts",
        "backtest_arbitration_decisions",
        ["run_row_id", "decision_timestamp"],
    )

    op.create_table(
        "backtest_comparison_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("comparison_id", sa.String(length=128), nullable=False),
        sa.Column("left_run_id", sa.String(length=128), nullable=False),
        sa.Column("right_run_id", sa.String(length=128), nullable=False),
        sa.Column("comparison_key", sa.String(length=128), nullable=False),
        sa.Column("table_rows", sa.JSON(), nullable=False),
        sa.Column("chart_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id", "comparison_id"),
    )
    op.create_index(
        "ix_backtest_comparison_runs_pair",
        "backtest_comparison_runs",
        ["left_run_id", "right_run_id"],
    )

    op.create_table(
        "backtest_export_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("export_id", sa.String(length=128), nullable=False),
        sa.Column("export_kind", sa.String(length=64), nullable=False),
        sa.Column("artifact_path", sa.String(length=512), nullable=False),
        sa.Column("artifact_checksum", sa.String(length=256), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id", "export_id"),
    )
    op.create_index(
        "ix_backtest_export_metadata_run_ts",
        "backtest_export_metadata",
        ["run_row_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_backtest_export_metadata_run_ts", table_name="backtest_export_metadata")
    op.drop_table("backtest_export_metadata")

    op.drop_index("ix_backtest_comparison_runs_pair", table_name="backtest_comparison_runs")
    op.drop_table("backtest_comparison_runs")

    op.drop_index(
        "ix_backtest_arbitration_decisions_run_ts",
        table_name="backtest_arbitration_decisions",
    )
    op.drop_table("backtest_arbitration_decisions")

    op.drop_index("ix_backtest_event_overlays_run", table_name="backtest_event_overlays")
    op.drop_table("backtest_event_overlays")

    op.drop_index("ix_backtest_replay_snapshots_run_ts", table_name="backtest_replay_snapshots")
    op.drop_table("backtest_replay_snapshots")

    op.drop_index("ix_backtest_strategy_cycles_run", table_name="backtest_strategy_cycles")
    op.drop_table("backtest_strategy_cycles")

    op.drop_index(
        "ix_backtest_reconstructed_trades_run",
        table_name="backtest_reconstructed_trades",
    )
    op.drop_table("backtest_reconstructed_trades")

    op.drop_index("ix_backtest_greeks_attribution_run_ts", table_name="backtest_greeks_attribution")
    op.drop_table("backtest_greeks_attribution")

    op.drop_index("ix_backtest_pnl_attribution_run_ts", table_name="backtest_pnl_attribution")
    op.drop_table("backtest_pnl_attribution")

    op.drop_index(
        "ix_backtest_portfolio_analytics_run_ts",
        table_name="backtest_portfolio_analytics",
    )
    op.drop_table("backtest_portfolio_analytics")

    op.drop_index("ix_backtest_strategy_analytics_run_ts", table_name="backtest_strategy_analytics")
    op.drop_table("backtest_strategy_analytics")
