"""Add Sprint 8C strategy management foundation tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016_strategy_management_foundation"
down_revision = "0015_strategy_policy_library_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roll_policy_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_identifier", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=48), nullable=False),
        sa.Column("aliases_json", sa.JSON(), nullable=False),
        sa.Column("supported_strategy_families", sa.JSON(), nullable=False),
        sa.Column("supported_lifecycle_states", sa.JSON(), nullable=False),
        sa.Column("supported_exercise_styles", sa.JSON(), nullable=False),
        sa.Column("supported_settlement_types", sa.JSON(), nullable=False),
        sa.Column("required_market_data", sa.JSON(), nullable=False),
        sa.Column("required_volatility_data", sa.JSON(), nullable=False),
        sa.Column("parameter_schema_json", sa.JSON(), nullable=False),
        sa.Column("default_priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("plugin_namespace", sa.String(length=160), nullable=True),
        sa.Column("deprecated", sa.Boolean(), nullable=False),
        sa.Column("replacement_identifier", sa.String(length=160), nullable=True),
        sa.Column("known_limitations", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_identifier"),
    )
    op.create_index(
        "ix_roll_policy_registry_family",
        "roll_policy_registry",
        ["default_priority", "canonical_identifier"],
    )

    op.create_table(
        "roll_policy_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_identifier", sa.String(length=160), nullable=False),
        sa.Column("alias", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("alias"),
    )
    op.create_index(
        "ix_roll_policy_aliases_identifier",
        "roll_policy_aliases",
        ["canonical_identifier", "alias"],
    )

    op.create_table(
        "backtest_roll_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=160), nullable=False),
        sa.Column("strategy_identifier", sa.String(length=160), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=160), nullable=False),
        sa.Column("position_identifier", sa.String(length=160), nullable=False),
        sa.Column("source_legs_json", sa.JSON(), nullable=False),
        sa.Column("preserved_legs_json", sa.JSON(), nullable=False),
        sa.Column("close_quantity", sa.Integer(), nullable=False),
        sa.Column("target_quantity", sa.Integer(), nullable=False),
        sa.Column("target_expiration_policy", sa.String(length=128), nullable=False),
        sa.Column("target_strike_policy", sa.String(length=128), nullable=False),
        sa.Column("requested_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trigger", sa.String(length=128), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "request_id"),
    )
    op.create_index(
        "ix_backtest_roll_requests_run_ts",
        "backtest_roll_requests",
        ["run_id", "requested_timestamp"],
    )

    op.create_table(
        "backtest_roll_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=160), nullable=False),
        sa.Column("candidate_id", sa.String(length=160), nullable=False),
        sa.Column("roll_type", sa.String(length=64), nullable=False),
        sa.Column("target_legs_json", sa.JSON(), nullable=False),
        sa.Column("estimated_net_credit_or_debit", sa.Numeric(20, 8), nullable=True),
        sa.Column("liquidity_score", sa.Numeric(20, 10), nullable=False),
        sa.Column("quality_score", sa.Numeric(20, 10), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "candidate_id"),
    )
    op.create_index(
        "ix_backtest_roll_candidates_run",
        "backtest_roll_candidates",
        ["run_id", "request_id"],
    )

    op.create_table(
        "backtest_roll_eligibility_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=160), nullable=False),
        sa.Column("candidate_id", sa.String(length=160), nullable=False),
        sa.Column("eligibility_id", sa.String(length=160), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("rejections_json", sa.JSON(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "eligibility_id"),
    )
    op.create_index(
        "ix_backtest_roll_eligibility_run",
        "backtest_roll_eligibility_results",
        ["run_id", "request_id"],
    )

    op.create_table(
        "backtest_roll_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("execution_id", sa.String(length=160), nullable=False),
        sa.Column("plan_id", sa.String(length=160), nullable=False),
        sa.Column("request_id", sa.String(length=160), nullable=False),
        sa.Column("execution_style", sa.String(length=64), nullable=False),
        sa.Column("all_or_none_research", sa.Boolean(), nullable=False),
        sa.Column("sequential_legging", sa.Boolean(), nullable=False),
        sa.Column("requested_net_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "execution_id"),
    )
    op.create_index(
        "ix_backtest_roll_executions_run",
        "backtest_roll_executions",
        ["run_id", "plan_id"],
    )

    op.create_table(
        "backtest_roll_fills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("execution_id", sa.String(length=160), nullable=False),
        sa.Column("leg_label", sa.String(length=128), nullable=False),
        sa.Column("fill_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fill_quantity", sa.Integer(), nullable=False),
        sa.Column("fill_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("fees", sa.Numeric(20, 8), nullable=False),
        sa.Column("slippage", sa.Numeric(20, 8), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "execution_id", "fill_timestamp", "leg_label"),
    )
    op.create_index(
        "ix_backtest_roll_fills_run_ts",
        "backtest_roll_fills",
        ["run_id", "fill_timestamp"],
    )

    op.create_table(
        "backtest_partial_roll_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("state_id", sa.String(length=160), nullable=False),
        sa.Column("plan_id", sa.String(length=160), nullable=False),
        sa.Column("temporary_naked_exposure", sa.Boolean(), nullable=False),
        sa.Column("residual_quantities_json", sa.JSON(), nullable=False),
        sa.Column("risk_escalated", sa.Boolean(), nullable=False),
        sa.Column("timeout_seconds", sa.Numeric(20, 8), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "state_id"),
    )
    op.create_index(
        "ix_backtest_partial_roll_states_run",
        "backtest_partial_roll_states",
        ["run_id", "plan_id"],
    )

    op.create_table(
        "backtest_roll_reconciliations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("reconciliation_id", sa.String(length=160), nullable=False),
        sa.Column("plan_id", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("retry_scheduled", sa.Boolean(), nullable=False),
        sa.Column("cancel_scheduled", sa.Boolean(), nullable=False),
        sa.Column("fallback_close_scheduled", sa.Boolean(), nullable=False),
        sa.Column("state_transition", sa.String(length=64), nullable=False),
        sa.Column("recorded_temporary_exposure", sa.Boolean(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "reconciliation_id"),
    )
    op.create_index(
        "ix_backtest_roll_reconciliations_run",
        "backtest_roll_reconciliations",
        ["run_id", "plan_id"],
    )

    op.create_table(
        "backtest_basis_transfers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("basis_transfer_id", sa.String(length=160), nullable=False),
        sa.Column("plan_id", sa.String(length=160), nullable=False),
        sa.Column("original_basis", sa.Numeric(20, 8), nullable=False),
        sa.Column("cumulative_credits", sa.Numeric(20, 8), nullable=False),
        sa.Column("cumulative_debits", sa.Numeric(20, 8), nullable=False),
        sa.Column("fees", sa.Numeric(20, 8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(20, 8), nullable=False),
        sa.Column("basis_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "basis_transfer_id"),
    )
    op.create_index(
        "ix_backtest_basis_transfers_run",
        "backtest_basis_transfers",
        ["run_id", "plan_id"],
    )

    op.create_table(
        "backtest_conversion_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("conversion_id", sa.String(length=160), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=160), nullable=False),
        sa.Column("source_strategy", sa.String(length=128), nullable=False),
        sa.Column("target_strategy", sa.String(length=128), nullable=False),
        sa.Column("legs_closed_json", sa.JSON(), nullable=False),
        sa.Column("legs_preserved_json", sa.JSON(), nullable=False),
        sa.Column("legs_opened_json", sa.JSON(), nullable=False),
        sa.Column("conversion_cost", sa.Numeric(20, 8), nullable=True),
        sa.Column("compatible", sa.Boolean(), nullable=False),
        sa.Column("warnings_json", sa.JSON(), nullable=False),
        sa.Column("reproducibility_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "conversion_id"),
    )
    op.create_index(
        "ix_backtest_conversion_plans_run",
        "backtest_conversion_plans",
        ["run_id", "strategy_instance_id"],
    )

    op.create_table(
        "backtest_conversion_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("execution_id", sa.String(length=160), nullable=False),
        sa.Column("conversion_id", sa.String(length=160), nullable=False),
        sa.Column("execution_status", sa.String(length=64), nullable=False),
        sa.Column("execution_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "execution_id"),
    )
    op.create_index(
        "ix_backtest_conversion_executions_run",
        "backtest_conversion_executions",
        ["run_id", "conversion_id"],
    )

    op.create_table(
        "backtest_management_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("comparison_id", sa.String(length=160), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=160), nullable=False),
        sa.Column("alternatives_json", sa.JSON(), nullable=False),
        sa.Column("selected_action", sa.String(length=64), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "comparison_id"),
    )
    op.create_index(
        "ix_backtest_management_comparisons_run",
        "backtest_management_comparisons",
        ["run_id", "strategy_instance_id"],
    )

    op.create_table(
        "backtest_roll_analytics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("analytics_id", sa.String(length=160), nullable=False),
        sa.Column("roll_metrics_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "analytics_id"),
    )
    op.create_index(
        "ix_backtest_roll_analytics_run_ts",
        "backtest_roll_analytics",
        ["run_id", "created_at"],
    )

    op.create_table(
        "backtest_conversion_analytics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("analytics_id", sa.String(length=160), nullable=False),
        sa.Column("conversion_metrics_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "analytics_id"),
    )
    op.create_index(
        "ix_backtest_conversion_analytics_run_ts",
        "backtest_conversion_analytics",
        ["run_id", "created_at"],
    )

    op.create_table(
        "strategy_management_optimizer_contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_id", sa.String(length=160), nullable=False),
        sa.Column("strategy_identifier", sa.String(length=160), nullable=False),
        sa.Column("contract_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("contract_id"),
    )
    op.create_index(
        "ix_strategy_mgmt_optimizer_contracts_strategy",
        "strategy_management_optimizer_contracts",
        ["strategy_identifier", "created_at"],
    )

    op.create_table(
        "strategy_management_checksums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checksum_key", sa.String(length=160), nullable=False),
        sa.Column("checksum_value", sa.String(length=256), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("checksum_key"),
    )
    op.create_index(
        "ix_strategy_management_checksums_created",
        "strategy_management_checksums",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_strategy_management_checksums_created",
        table_name="strategy_management_checksums",
    )
    op.drop_table("strategy_management_checksums")

    op.drop_index(
        "ix_strategy_mgmt_optimizer_contracts_strategy",
        table_name="strategy_management_optimizer_contracts",
    )
    op.drop_table("strategy_management_optimizer_contracts")

    op.drop_index(
        "ix_backtest_conversion_analytics_run_ts",
        table_name="backtest_conversion_analytics",
    )
    op.drop_table("backtest_conversion_analytics")

    op.drop_index("ix_backtest_roll_analytics_run_ts", table_name="backtest_roll_analytics")
    op.drop_table("backtest_roll_analytics")

    op.drop_index(
        "ix_backtest_management_comparisons_run",
        table_name="backtest_management_comparisons",
    )
    op.drop_table("backtest_management_comparisons")

    op.drop_index(
        "ix_backtest_conversion_executions_run",
        table_name="backtest_conversion_executions",
    )
    op.drop_table("backtest_conversion_executions")

    op.drop_index("ix_backtest_conversion_plans_run", table_name="backtest_conversion_plans")
    op.drop_table("backtest_conversion_plans")

    op.drop_index("ix_backtest_basis_transfers_run", table_name="backtest_basis_transfers")
    op.drop_table("backtest_basis_transfers")

    op.drop_index(
        "ix_backtest_roll_reconciliations_run",
        table_name="backtest_roll_reconciliations",
    )
    op.drop_table("backtest_roll_reconciliations")

    op.drop_index(
        "ix_backtest_partial_roll_states_run",
        table_name="backtest_partial_roll_states",
    )
    op.drop_table("backtest_partial_roll_states")

    op.drop_index("ix_backtest_roll_fills_run_ts", table_name="backtest_roll_fills")
    op.drop_table("backtest_roll_fills")

    op.drop_index("ix_backtest_roll_executions_run", table_name="backtest_roll_executions")
    op.drop_table("backtest_roll_executions")

    op.drop_index(
        "ix_backtest_roll_eligibility_run",
        table_name="backtest_roll_eligibility_results",
    )
    op.drop_table("backtest_roll_eligibility_results")

    op.drop_index("ix_backtest_roll_candidates_run", table_name="backtest_roll_candidates")
    op.drop_table("backtest_roll_candidates")

    op.drop_index("ix_backtest_roll_requests_run_ts", table_name="backtest_roll_requests")
    op.drop_table("backtest_roll_requests")

    op.drop_index("ix_roll_policy_aliases_identifier", table_name="roll_policy_aliases")
    op.drop_table("roll_policy_aliases")

    op.drop_index("ix_roll_policy_registry_family", table_name="roll_policy_registry")
    op.drop_table("roll_policy_registry")
