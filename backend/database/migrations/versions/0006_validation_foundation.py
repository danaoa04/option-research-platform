"""Add strategy validation persistence tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_validation_foundation"
down_revision = "0005_optimization_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "validation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_name", sa.String(length=128), nullable=False),
        sa.Column("candidate_ordering", sa.JSON(), nullable=False),
        sa.Column("validation_configuration", sa.JSON(), nullable=False),
        sa.Column("cpcv_definition", sa.JSON(), nullable=False),
        sa.Column("comparison_json", sa.JSON(), nullable=False),
        sa.Column("checksums", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.Column("software_git_commit", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        "ix_validation_runs_strategy_ts",
        "validation_runs",
        ["strategy_name", "created_at"],
    )

    op.create_table(
        "validation_candidate_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("validation_runs.id"), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("deflated_sharpe", sa.JSON(), nullable=False),
        sa.Column("pbo", sa.JSON(), nullable=False),
        sa.Column("cpcv", sa.JSON(), nullable=False),
        sa.Column("sensitivity", sa.JSON(), nullable=False),
        sa.Column("neighborhood", sa.JSON(), nullable=False),
        sa.Column("degradation", sa.JSON(), nullable=False),
        sa.Column("regime_robustness", sa.JSON(), nullable=False),
        sa.Column("temporal_stability", sa.JSON(), nullable=False),
        sa.Column("stress_test", sa.JSON(), nullable=False),
        sa.Column("bootstrap", sa.JSON(), nullable=False),
        sa.Column("robustness_score", sa.JSON(), nullable=False),
        sa.Column("gate_result", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.Column("reproducibility_metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "candidate_id"),
    )
    op.create_index(
        "ix_validation_candidate_results_run",
        "validation_candidate_results",
        ["run_row_id", "candidate_id"],
    )
    op.create_index(
        "ix_validation_candidate_results_tier",
        "validation_candidate_results",
        ["tier"],
    )

    op.create_table(
        "validation_folds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("validation_runs.id"), nullable=False),
        sa.Column("split_id", sa.String(length=128), nullable=False),
        sa.Column("fold_index", sa.Integer(), nullable=False),
        sa.Column("split_json", sa.JSON(), nullable=False),
        sa.Column("selection_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "split_id"),
    )
    op.create_index(
        "ix_validation_folds_run",
        "validation_folds",
        ["run_row_id", "split_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_validation_folds_run", table_name="validation_folds")
    op.drop_table("validation_folds")

    op.drop_index(
        "ix_validation_candidate_results_tier",
        table_name="validation_candidate_results",
    )
    op.drop_index(
        "ix_validation_candidate_results_run",
        table_name="validation_candidate_results",
    )
    op.drop_table("validation_candidate_results")

    op.drop_index("ix_validation_runs_strategy_ts", table_name="validation_runs")
    op.drop_table("validation_runs")
