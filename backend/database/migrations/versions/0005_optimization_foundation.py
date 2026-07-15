"""Add optimization engine persistence schema."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_optimization_foundation"
down_revision = "0004_calendar_research_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "optimization_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("problem_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_type", sa.String(length=48), nullable=False),
        sa.Column("symbol_universe", sa.JSON(), nullable=False),
        sa.Column("historical_start_date", sa.Date(), nullable=False),
        sa.Column("historical_end_date", sa.Date(), nullable=False),
        sa.Column("optimization_problem", sa.JSON(), nullable=False),
        sa.Column("parameter_space", sa.JSON(), nullable=False),
        sa.Column("objective_definitions", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("candidate_ordering", sa.JSON(), nullable=False),
        sa.Column("pareto_front_ids", sa.JSON(), nullable=False),
        sa.Column("winner_ids", sa.JSON(), nullable=False),
        sa.Column("dataset_manifests", sa.JSON(), nullable=False),
        sa.Column("volatility_surface_snapshots", sa.JSON(), nullable=False),
        sa.Column("lifecycle_policies", sa.JSON(), nullable=False),
        sa.Column("pricing_model_policies", sa.JSON(), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column("software_git_commit", sa.String(length=64), nullable=False),
        sa.Column("checksums", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("runtime_seconds", sa.Numeric(20, 8), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        "ix_optimization_runs_problem_ts", "optimization_runs", ["problem_id", "created_at"]
    )
    op.create_index("ix_optimization_runs_status", "optimization_runs", ["status"])

    op.create_table(
        "optimization_problems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("problem_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id"),
    )

    op.create_table(
        "optimization_parameter_spaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("parameter_space_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id"),
    )

    op.create_table(
        "optimization_objectives",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("objective_json", sa.JSON(), nullable=False),
        sa.Column("objective_mode", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_optimization_objectives_run", "optimization_objectives", ["run_row_id"])

    op.create_table(
        "optimization_constraints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("constraint_json", sa.JSON(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
    )
    op.create_index("ix_optimization_constraints_run", "optimization_constraints", ["run_row_id"])

    op.create_table(
        "optimization_candidate_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("candidate_json", sa.JSON(), nullable=False),
        sa.Column("objective_metrics", sa.JSON(), nullable=False),
        sa.Column("constraint_results", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("score", sa.Numeric(20, 10), nullable=True),
        sa.Column("runtime_seconds", sa.Numeric(20, 8), nullable=False),
        sa.Column("reproducibility_metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "candidate_id"),
    )
    op.create_index(
        "ix_optimization_candidate_evaluations_run",
        "optimization_candidate_evaluations",
        ["run_row_id"],
    )
    op.create_index(
        "ix_optimization_candidate_evaluations_status",
        "optimization_candidate_evaluations",
        ["status"],
    )

    op.create_table(
        "optimizer_trials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("trial_id", sa.String(length=128), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("trial_json", sa.JSON(), nullable=False),
        sa.Column("input_checksum", sa.String(length=128), nullable=False),
        sa.Column("output_checksum", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("generation_index", sa.Integer(), nullable=False),
        sa.UniqueConstraint("run_row_id", "trial_id"),
    )
    op.create_index("ix_optimizer_trials_run", "optimizer_trials", ["run_row_id"])

    op.create_table(
        "optimization_pareto_fronts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("front_json", sa.JSON(), nullable=False),
        sa.Column("dominated_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id"),
    )

    op.create_table(
        "optimization_selected_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("selection_reason", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "candidate_id"),
    )

    op.create_table(
        "optimization_walk_forward_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("walk_forward_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id"),
    )

    op.create_table(
        "optimization_walk_forward_folds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "walk_forward_run_row_id",
            sa.Integer(),
            sa.ForeignKey("optimization_walk_forward_runs.id"),
            nullable=False,
        ),
        sa.Column("fold_id", sa.String(length=64), nullable=False),
        sa.Column("split_json", sa.JSON(), nullable=False),
        sa.Column(
            "training_run_row_id",
            sa.Integer(),
            sa.ForeignKey("optimization_runs.id"),
            nullable=True,
        ),
        sa.Column("test_checksum", sa.String(length=128), nullable=True),
        sa.UniqueConstraint("walk_forward_run_row_id", "fold_id"),
    )
    op.create_index(
        "ix_optimization_walk_forward_folds_run",
        "optimization_walk_forward_folds",
        ["walk_forward_run_row_id"],
    )

    op.create_table(
        "optimization_fold_selections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "walk_forward_fold_row_id",
            sa.Integer(),
            sa.ForeignKey("optimization_walk_forward_folds.id"),
            nullable=False,
        ),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("selection_reason", sa.JSON(), nullable=False),
        sa.UniqueConstraint("walk_forward_fold_row_id", "candidate_id"),
    )

    op.create_table(
        "optimization_fold_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "walk_forward_fold_row_id",
            sa.Integer(),
            sa.ForeignKey("optimization_walk_forward_folds.id"),
            nullable=False,
        ),
        sa.Column("test_result_json", sa.JSON(), nullable=False),
        sa.Column("training_metrics_json", sa.JSON(), nullable=False),
        sa.Column("validation_metrics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("walk_forward_fold_row_id"),
    )

    op.create_table(
        "optimization_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("checkpoint_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id"),
    )

    op.create_table(
        "optimization_reproducibility_checksums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("checksums_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id"),
    )

    op.create_table(
        "optimization_execution_diagnostics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_row_id", sa.Integer(), sa.ForeignKey("optimization_runs.id"), nullable=False
        ),
        sa.Column("execution_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id"),
    )


def downgrade() -> None:
    op.drop_table("optimization_execution_diagnostics")
    op.drop_table("optimization_reproducibility_checksums")
    op.drop_table("optimization_checkpoints")
    op.drop_table("optimization_fold_results")
    op.drop_table("optimization_fold_selections")
    op.drop_index(
        "ix_optimization_walk_forward_folds_run", table_name="optimization_walk_forward_folds"
    )
    op.drop_table("optimization_walk_forward_folds")
    op.drop_table("optimization_walk_forward_runs")
    op.drop_table("optimization_selected_candidates")
    op.drop_table("optimization_pareto_fronts")
    op.drop_index("ix_optimizer_trials_run", table_name="optimizer_trials")
    op.drop_table("optimizer_trials")
    op.drop_index(
        "ix_optimization_candidate_evaluations_status",
        table_name="optimization_candidate_evaluations",
    )
    op.drop_index(
        "ix_optimization_candidate_evaluations_run", table_name="optimization_candidate_evaluations"
    )
    op.drop_table("optimization_candidate_evaluations")
    op.drop_index("ix_optimization_constraints_run", table_name="optimization_constraints")
    op.drop_table("optimization_constraints")
    op.drop_index("ix_optimization_objectives_run", table_name="optimization_objectives")
    op.drop_table("optimization_objectives")
    op.drop_table("optimization_parameter_spaces")
    op.drop_table("optimization_problems")
    op.drop_index("ix_optimization_runs_status", table_name="optimization_runs")
    op.drop_index("ix_optimization_runs_problem_ts", table_name="optimization_runs")
    op.drop_table("optimization_runs")
