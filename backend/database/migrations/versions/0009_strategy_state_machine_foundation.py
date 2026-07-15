"""Add Sprint 6B strategy state machine and orchestration persistence."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_strategy_state_machine_foundation"
down_revision = "0008_backtesting_event_loop_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_strategy_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("definition_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_name", sa.String(length=128), nullable=False),
        sa.Column("definition_json", sa.JSON(), nullable=False),
        sa.Column("validation_json", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("definition_id"),
    )
    op.create_index(
        "ix_backtest_strategy_definitions_name",
        "backtest_strategy_definitions",
        ["strategy_name"],
    )

    op.create_table(
        "backtest_strategy_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("template_name", sa.String(length=128), nullable=False),
        sa.Column("template_version", sa.String(length=32), nullable=True),
        sa.Column("compiled_definition_id", sa.String(length=128), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "template_name", "strategy_instance_id"),
    )
    op.create_index(
        "ix_backtest_strategy_templates_run",
        "backtest_strategy_templates",
        ["run_row_id", "template_name"],
    )

    op.create_table(
        "backtest_strategy_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("definition_id", sa.String(length=128), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=64), nullable=False),
        sa.Column("state_reason", sa.String(length=128), nullable=True),
        sa.Column("as_of_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "strategy_instance_id", "as_of_timestamp"),
    )
    op.create_index(
        "ix_backtest_strategy_instances_run_ts",
        "backtest_strategy_instances",
        ["run_row_id", "as_of_timestamp"],
    )

    op.create_table(
        "backtest_position_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("position_instance_id", sa.String(length=128), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=64), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("as_of_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "position_instance_id", "as_of_timestamp"),
    )
    op.create_index(
        "ix_backtest_position_instances_run_ts",
        "backtest_position_instances",
        ["run_row_id", "as_of_timestamp"],
    )

    op.create_table(
        "backtest_state_transitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("position_instance_id", sa.String(length=128), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("transition_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prior_state", sa.String(length=64), nullable=False),
        sa.Column("next_state", sa.String(length=64), nullable=False),
        sa.Column("trigger", sa.String(length=128), nullable=False),
        sa.Column("action_plan", sa.JSON(), nullable=False),
        sa.Column("data_snapshot_reference", sa.String(length=256), nullable=False),
        sa.Column("software_git_commit", sa.String(length=64), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.Column("checksum_metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "strategy_instance_id", "sequence_number"),
    )
    op.create_index(
        "ix_backtest_state_transitions_run_ts",
        "backtest_state_transitions",
        ["run_row_id", "transition_timestamp"],
    )

    op.create_table(
        "backtest_transition_guards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column(
            "transition_row_id",
            sa.Integer(),
            sa.ForeignKey("backtest_state_transitions.id"),
            nullable=False,
        ),
        sa.Column("guard_name", sa.String(length=128), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "transition_row_id", "guard_name"),
    )
    op.create_index(
        "ix_backtest_transition_guards_run",
        "backtest_transition_guards",
        ["run_row_id", "guard_name"],
    )

    op.create_table(
        "backtest_roll_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("plan_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("source_position_id", sa.String(length=128), nullable=False),
        sa.Column("roll_kind", sa.String(length=64), nullable=False),
        sa.Column("policy_trigger", sa.String(length=128), nullable=False),
        sa.Column("target_specification", sa.JSON(), nullable=False),
        sa.Column("estimated_credit_or_debit", sa.Numeric(20, 8), nullable=True),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id", "plan_id"),
    )
    op.create_index(
        "ix_backtest_roll_plans_run_ts",
        "backtest_roll_plans",
        ["run_row_id", "created_at"],
    )

    op.create_table(
        "backtest_roll_relationships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("plan_id", sa.String(length=128), nullable=False),
        sa.Column("relationship_type", sa.String(length=64), nullable=False),
        sa.Column("leg_label", sa.String(length=128), nullable=False),
        sa.Column("source_position_id", sa.String(length=128), nullable=True),
        sa.Column("target_position_id", sa.String(length=128), nullable=True),
        sa.UniqueConstraint("run_row_id", "plan_id", "relationship_type", "leg_label"),
    )
    op.create_index(
        "ix_backtest_roll_relationships_run",
        "backtest_roll_relationships",
        ["run_row_id", "plan_id"],
    )

    op.create_table(
        "backtest_partial_fills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("position_instance_id", sa.String(length=128), nullable=False),
        sa.Column("leg_label", sa.String(length=128), nullable=False),
        sa.Column("original_quantity", sa.Integer(), nullable=False),
        sa.Column("filled_quantity", sa.Integer(), nullable=False),
        sa.Column("remaining_quantity", sa.Integer(), nullable=False),
        sa.Column("average_entry_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("fill_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.CheckConstraint("filled_quantity >= 0", name="backtest_partial_fills_non_negative"),
        sa.UniqueConstraint(
            "run_row_id",
            "strategy_instance_id",
            "position_instance_id",
            "leg_label",
            "fill_timestamp",
        ),
    )
    op.create_index(
        "ix_backtest_partial_fills_run_ts",
        "backtest_partial_fills",
        ["run_row_id", "fill_timestamp"],
    )

    op.create_table(
        "backtest_reconciliation_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("position_instance_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("strategy_fill_ratio", sa.Numeric(20, 10), nullable=False),
        sa.Column("retry_eligible", sa.Boolean(), nullable=False),
        sa.Column("cancelled", sa.Boolean(), nullable=False),
        sa.Column("timed_out", sa.Boolean(), nullable=False),
        sa.Column("failure_escalated", sa.Boolean(), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "run_row_id",
            "strategy_instance_id",
            "position_instance_id",
            "event_timestamp",
        ),
    )
    op.create_index(
        "ix_backtest_reconciliation_events_run_ts",
        "backtest_reconciliation_events",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_integrity_failures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("position_instance_id", sa.String(length=128), nullable=False),
        sa.Column("failure_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "run_row_id",
            "strategy_instance_id",
            "position_instance_id",
            "failure_timestamp",
            "reason_code",
        ),
    )
    op.create_index(
        "ix_backtest_integrity_failures_run_ts",
        "backtest_integrity_failures",
        ["run_row_id", "failure_timestamp"],
    )

    op.create_table(
        "backtest_strategy_histories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("strategy_instance_id", sa.String(length=128), nullable=False),
        sa.Column("history_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("history_kind", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("checksum_metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "run_row_id",
            "strategy_instance_id",
            "history_timestamp",
            "history_kind",
        ),
    )
    op.create_index(
        "ix_backtest_strategy_histories_run_ts",
        "backtest_strategy_histories",
        ["run_row_id", "history_timestamp"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_backtest_strategy_histories_run_ts",
        table_name="backtest_strategy_histories",
    )
    op.drop_table("backtest_strategy_histories")

    op.drop_index(
        "ix_backtest_integrity_failures_run_ts",
        table_name="backtest_integrity_failures",
    )
    op.drop_table("backtest_integrity_failures")

    op.drop_index(
        "ix_backtest_reconciliation_events_run_ts",
        table_name="backtest_reconciliation_events",
    )
    op.drop_table("backtest_reconciliation_events")

    op.drop_index("ix_backtest_partial_fills_run_ts", table_name="backtest_partial_fills")
    op.drop_table("backtest_partial_fills")

    op.drop_index(
        "ix_backtest_roll_relationships_run",
        table_name="backtest_roll_relationships",
    )
    op.drop_table("backtest_roll_relationships")

    op.drop_index("ix_backtest_roll_plans_run_ts", table_name="backtest_roll_plans")
    op.drop_table("backtest_roll_plans")

    op.drop_index(
        "ix_backtest_transition_guards_run",
        table_name="backtest_transition_guards",
    )
    op.drop_table("backtest_transition_guards")

    op.drop_index(
        "ix_backtest_state_transitions_run_ts",
        table_name="backtest_state_transitions",
    )
    op.drop_table("backtest_state_transitions")

    op.drop_index(
        "ix_backtest_position_instances_run_ts",
        table_name="backtest_position_instances",
    )
    op.drop_table("backtest_position_instances")

    op.drop_index(
        "ix_backtest_strategy_instances_run_ts",
        table_name="backtest_strategy_instances",
    )
    op.drop_table("backtest_strategy_instances")

    op.drop_index(
        "ix_backtest_strategy_templates_run",
        table_name="backtest_strategy_templates",
    )
    op.drop_table("backtest_strategy_templates")

    op.drop_index(
        "ix_backtest_strategy_definitions_name",
        table_name="backtest_strategy_definitions",
    )
    op.drop_table("backtest_strategy_definitions")
