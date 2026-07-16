"""Add Sprint 9B replay workspace and experiment persistence foundation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_replay_workspace_foundation"
down_revision = "0017_risk_lab_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "replay_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("timeline_id", sa.String(length=128), nullable=False),
        sa.Column("base_branch_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(
        "ix_replay_sessions_run",
        "replay_sessions",
        ["run_id", "created_at"],
    )

    op.create_table(
        "replay_branches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("branch_id", sa.String(length=128), nullable=False),
        sa.Column("parent_branch_id", sa.String(length=128), nullable=True),
        sa.Column("root_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("decision_delta", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "branch_id"),
    )
    op.create_index(
        "ix_replay_branches_session",
        "replay_branches",
        ["session_id", "created_at"],
    )

    op.create_table(
        "replay_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("checkpoint_id", sa.String(length=128), nullable=False),
        sa.Column("branch_id", sa.String(length=128), nullable=False),
        sa.Column("event_index", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "checkpoint_id"),
    )
    op.create_index(
        "ix_replay_checkpoints_session",
        "replay_checkpoints",
        ["session_id", "created_at"],
    )

    op.create_table(
        "replay_bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("bookmark_id", sa.String(length=128), nullable=False),
        sa.Column("branch_id", sa.String(length=128), nullable=False),
        sa.Column("event_index", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "bookmark_id"),
    )
    op.create_index(
        "ix_replay_bookmarks_session",
        "replay_bookmarks",
        ["session_id", "created_at"],
    )

    op.create_table(
        "replay_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("branch_id", sa.String(length=128), nullable=False),
        sa.Column("event_sequence", sa.Integer(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("scenario_id", sa.String(length=128), nullable=True),
        sa.Column("policy_id", sa.String(length=128), nullable=True),
        sa.Column("optimizer_id", sa.String(length=128), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("event_checksum", sa.String(length=256), nullable=False),
        sa.UniqueConstraint("session_id", "branch_id", "event_sequence"),
    )
    op.create_index(
        "ix_replay_events_session_branch",
        "replay_events",
        ["session_id", "branch_id", "event_sequence"],
    )

    op.create_table(
        "replay_annotations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("annotation_id", sa.String(length=128), nullable=False),
        sa.Column("branch_id", sa.String(length=128), nullable=False),
        sa.Column("event_sequence", sa.Integer(), nullable=False),
        sa.Column("note_markdown", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "annotation_id"),
    )
    op.create_index(
        "ix_replay_annotations_session",
        "replay_annotations",
        ["session_id", "created_at"],
    )

    op.create_table(
        "replay_filters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("filter_id", sa.String(length=128), nullable=False),
        sa.Column("branch_id", sa.String(length=128), nullable=False),
        sa.Column("filter_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "filter_id"),
    )
    op.create_index(
        "ix_replay_filters_session",
        "replay_filters",
        ["session_id", "created_at"],
    )

    op.create_table(
        "replay_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("comparison_id", sa.String(length=128), nullable=False),
        sa.Column("left_branch_id", sa.String(length=128), nullable=False),
        sa.Column("right_branch_id", sa.String(length=128), nullable=False),
        sa.Column("comparison_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "comparison_id"),
    )
    op.create_index(
        "ix_replay_comparisons_session",
        "replay_comparisons",
        ["session_id", "created_at"],
    )

    op.create_table(
        "replay_diagnostics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("diagnostic_id", sa.String(length=128), nullable=False),
        sa.Column("branch_id", sa.String(length=128), nullable=False),
        sa.Column("diagnostic_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "diagnostic_id"),
    )
    op.create_index(
        "ix_replay_diagnostics_session",
        "replay_diagnostics",
        ["session_id", "created_at"],
    )

    op.create_table(
        "replay_reproducibility_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("report_id", sa.String(length=128), nullable=False),
        sa.Column("left_run_id", sa.String(length=128), nullable=False),
        sa.Column("right_run_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "report_id"),
    )
    op.create_index(
        "ix_replay_repro_reports_session",
        "replay_reproducibility_reports",
        ["session_id", "created_at"],
    )

    op.create_table(
        "decision_explanations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("explanation_id", sa.String(length=128), nullable=False),
        sa.Column("branch_id", sa.String(length=128), nullable=False),
        sa.Column("event_sequence", sa.Integer(), nullable=False),
        sa.Column("decision_kind", sa.String(length=64), nullable=False),
        sa.Column("explanation_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "explanation_id"),
    )
    op.create_index(
        "ix_decision_explanations_session",
        "decision_explanations",
        ["session_id", "event_sequence"],
    )

    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("experiment_id", sa.String(length=128), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("dataset_refs", sa.JSON(), nullable=False),
        sa.Column("strategy_set", sa.JSON(), nullable=False),
        sa.Column("optimization_set", sa.JSON(), nullable=False),
        sa.Column("scenario_set", sa.JSON(), nullable=False),
        sa.Column("replay_set", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("experiment_id"),
    )
    op.create_index(
        "ix_experiments_created",
        "experiments",
        ["created_at", "version"],
    )

    op.create_table(
        "experiment_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("comparison_id", sa.String(length=128), nullable=False),
        sa.Column("left_experiment_id", sa.String(length=128), nullable=False),
        sa.Column("right_experiment_id", sa.String(length=128), nullable=False),
        sa.Column("comparison_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("comparison_id"),
    )
    op.create_index(
        "ix_experiment_comparisons_pair",
        "experiment_comparisons",
        ["left_experiment_id", "right_experiment_id"],
    )

    op.create_table(
        "workspace_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_key", sa.String(length=160), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_key"),
    )
    op.create_index(
        "ix_workspace_metadata_created",
        "workspace_metadata",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_metadata_created", table_name="workspace_metadata")
    op.drop_table("workspace_metadata")

    op.drop_index("ix_experiment_comparisons_pair", table_name="experiment_comparisons")
    op.drop_table("experiment_comparisons")

    op.drop_index("ix_experiments_created", table_name="experiments")
    op.drop_table("experiments")

    op.drop_index("ix_decision_explanations_session", table_name="decision_explanations")
    op.drop_table("decision_explanations")

    op.drop_index(
        "ix_replay_repro_reports_session",
        table_name="replay_reproducibility_reports",
    )
    op.drop_table("replay_reproducibility_reports")

    op.drop_index("ix_replay_diagnostics_session", table_name="replay_diagnostics")
    op.drop_table("replay_diagnostics")

    op.drop_index("ix_replay_comparisons_session", table_name="replay_comparisons")
    op.drop_table("replay_comparisons")

    op.drop_index("ix_replay_filters_session", table_name="replay_filters")
    op.drop_table("replay_filters")

    op.drop_index("ix_replay_annotations_session", table_name="replay_annotations")
    op.drop_table("replay_annotations")

    op.drop_index("ix_replay_events_session_branch", table_name="replay_events")
    op.drop_table("replay_events")

    op.drop_index("ix_replay_bookmarks_session", table_name="replay_bookmarks")
    op.drop_table("replay_bookmarks")

    op.drop_index("ix_replay_checkpoints_session", table_name="replay_checkpoints")
    op.drop_table("replay_checkpoints")

    op.drop_index("ix_replay_branches_session", table_name="replay_branches")
    op.drop_table("replay_branches")

    op.drop_index("ix_replay_sessions_run", table_name="replay_sessions")
    op.drop_table("replay_sessions")
