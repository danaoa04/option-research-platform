"""Add Sprint 8B strategy policy library foundation tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_strategy_policy_library_foundation"
down_revision = "0014_strategy_library_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategy_policy_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_id", sa.String(length=160), nullable=False),
        sa.Column("policy_name", sa.String(length=160), nullable=False),
        sa.Column("policy_family", sa.String(length=48), nullable=False),
        sa.Column("policy_version", sa.String(length=48), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("required_data", sa.JSON(), nullable=False),
        sa.Column("supported_strategies", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("deprecated", sa.Boolean(), nullable=False),
        sa.Column("replacement_policy_id", sa.String(length=160), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("policy_id"),
    )
    op.create_index(
        "ix_strategy_policy_registry_family",
        "strategy_policy_registry",
        ["policy_family", "policy_name"],
    )

    op.create_table(
        "strategy_policy_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_id", sa.String(length=160), nullable=False),
        sa.Column("alias", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("alias"),
    )
    op.create_index(
        "ix_strategy_policy_aliases_policy",
        "strategy_policy_aliases",
        ["policy_id", "alias"],
    )

    op.create_table(
        "strategy_policy_set_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("set_id", sa.String(length=160), nullable=False),
        sa.Column("set_version", sa.String(length=48), nullable=False),
        sa.Column("strategy_identifier", sa.String(length=160), nullable=False),
        sa.Column("conflict_mode", sa.String(length=48), nullable=False),
        sa.Column("entry_policies", sa.JSON(), nullable=False),
        sa.Column("exit_policies", sa.JSON(), nullable=False),
        sa.Column("management_policies", sa.JSON(), nullable=False),
        sa.Column("earnings_policies", sa.JSON(), nullable=False),
        sa.Column("dividend_policies", sa.JSON(), nullable=False),
        sa.Column("roll_policies", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("set_id", "set_version"),
    )
    op.create_index(
        "ix_strategy_policy_set_versions_strategy",
        "strategy_policy_set_versions",
        ["strategy_identifier", "set_id", "set_version"],
    )

    op.create_table(
        "strategy_policy_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("evaluation_id", sa.String(length=160), nullable=False),
        sa.Column("strategy_identifier", sa.String(length=160), nullable=False),
        sa.Column("policy_set_id", sa.String(length=160), nullable=False),
        sa.Column("policy_set_version", sa.String(length=48), nullable=False),
        sa.Column("policy_id", sa.String(length=160), nullable=False),
        sa.Column("policy_version", sa.String(length=48), nullable=False),
        sa.Column("policy_family", sa.String(length=48), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("observed_values_json", sa.JSON(), nullable=False),
        sa.Column("thresholds_json", sa.JSON(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Numeric(8, 6), nullable=False),
        sa.Column("required_data_present", sa.Boolean(), nullable=False),
        sa.Column("data_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "evaluation_id"),
    )
    op.create_index(
        "ix_strategy_policy_evaluations_run_ts",
        "strategy_policy_evaluations",
        ["run_id", "event_timestamp"],
    )

    op.create_table(
        "strategy_policy_conflicts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("conflict_id", sa.String(length=160), nullable=False),
        sa.Column("strategy_identifier", sa.String(length=160), nullable=False),
        sa.Column("policy_set_id", sa.String(length=160), nullable=False),
        sa.Column("policy_set_version", sa.String(length=48), nullable=False),
        sa.Column("conflict_mode", sa.String(length=48), nullable=False),
        sa.Column("winning_policy_id", sa.String(length=160), nullable=True),
        sa.Column("matched_signals_json", sa.JSON(), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "conflict_id"),
    )
    op.create_index(
        "ix_strategy_policy_conflicts_run_ts",
        "strategy_policy_conflicts",
        ["run_id", "event_timestamp"],
    )

    op.create_table(
        "strategy_policy_checksums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checksum_key", sa.String(length=160), nullable=False),
        sa.Column("checksum_value", sa.String(length=256), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("checksum_key"),
    )
    op.create_index(
        "ix_strategy_policy_checksums_created",
        "strategy_policy_checksums",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_strategy_policy_checksums_created", table_name="strategy_policy_checksums")
    op.drop_table("strategy_policy_checksums")

    op.drop_index("ix_strategy_policy_conflicts_run_ts", table_name="strategy_policy_conflicts")
    op.drop_table("strategy_policy_conflicts")

    op.drop_index(
        "ix_strategy_policy_evaluations_run_ts",
        table_name="strategy_policy_evaluations",
    )
    op.drop_table("strategy_policy_evaluations")

    op.drop_index(
        "ix_strategy_policy_set_versions_strategy",
        table_name="strategy_policy_set_versions",
    )
    op.drop_table("strategy_policy_set_versions")

    op.drop_index("ix_strategy_policy_aliases_policy", table_name="strategy_policy_aliases")
    op.drop_table("strategy_policy_aliases")

    op.drop_index("ix_strategy_policy_registry_family", table_name="strategy_policy_registry")
    op.drop_table("strategy_policy_registry")
