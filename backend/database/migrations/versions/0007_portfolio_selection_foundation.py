"""Add portfolio selection persistence tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_portfolio_selection_foundation"
down_revision = "0006_validation_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("problem_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_name", sa.String(length=128), nullable=False),
        sa.Column("allocation_problem", sa.JSON(), nullable=False),
        sa.Column("objectives_json", sa.JSON(), nullable=False),
        sa.Column("constraints_json", sa.JSON(), nullable=False),
        sa.Column("correlation_policy", sa.JSON(), nullable=False),
        sa.Column("sizing_policy", sa.JSON(), nullable=False),
        sa.Column("rebalance_policy", sa.JSON(), nullable=False),
        sa.Column("eligible_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("allocation_count", sa.Integer(), nullable=False),
        sa.Column("reserve_cash", sa.Numeric(20, 8), nullable=False),
        sa.Column("available_capital", sa.Numeric(20, 8), nullable=False),
        sa.Column("checksums", sa.JSON(), nullable=False),
        sa.Column("software_git_commit", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column("dataset_manifests", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        "ix_portfolio_runs_strategy_ts",
        "portfolio_runs",
        ["strategy_name", "created_at"],
    )

    op.create_table(
        "portfolio_eligible_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("portfolio_runs.id"), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("validation_snapshot", sa.JSON(), nullable=False),
        sa.Column("exposure_snapshot", sa.JSON(), nullable=False),
        sa.Column("stats_snapshot", sa.JSON(), nullable=False),
        sa.Column("returns", sa.JSON(), nullable=False),
        sa.Column("pnl", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "candidate_id"),
    )
    op.create_index(
        "ix_portfolio_eligible_run",
        "portfolio_eligible_candidates",
        ["run_row_id", "candidate_id"],
    )

    op.create_table(
        "portfolio_rejected_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("portfolio_runs.id"), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("rejection_reasons", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "candidate_id"),
    )
    op.create_index(
        "ix_portfolio_rejected_run",
        "portfolio_rejected_candidates",
        ["run_row_id", "candidate_id"],
    )

    op.create_table(
        "portfolio_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("portfolio_runs.id"), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("weight", sa.Numeric(20, 10), nullable=False),
        sa.Column("capital", sa.Numeric(20, 8), nullable=False),
        sa.Column("contracts", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(20, 10), nullable=False),
        sa.UniqueConstraint("run_row_id", "candidate_id"),
    )
    op.create_index(
        "ix_portfolio_allocations_run",
        "portfolio_allocations",
        ["run_row_id", "candidate_id"],
    )

    op.create_table(
        "portfolio_constraint_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("portfolio_runs.id"), nullable=False),
        sa.Column("constraint_name", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("observed", sa.Numeric(20, 10), nullable=False),
        sa.Column("threshold", sa.Numeric(20, 10), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=True),
        sa.UniqueConstraint("run_row_id", "constraint_name", "candidate_id"),
    )
    op.create_index(
        "ix_portfolio_constraints_run",
        "portfolio_constraint_outcomes",
        ["run_row_id", "constraint_name"],
    )

    op.create_table(
        "portfolio_correlations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("portfolio_runs.id"), nullable=False),
        sa.Column("left_id", sa.String(length=128), nullable=False),
        sa.Column("right_id", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Numeric(20, 10), nullable=False),
        sa.Column("uncertainty", sa.Numeric(20, 10), nullable=False),
        sa.Column("effective_sample_size", sa.Integer(), nullable=False),
        sa.Column("sparse_warning", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("run_row_id", "left_id", "right_id", "kind"),
    )
    op.create_index(
        "ix_portfolio_correlations_run",
        "portfolio_correlations",
        ["run_row_id", "kind"],
    )

    op.create_table(
        "portfolio_clusters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("portfolio_runs.id"), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("cluster_id", sa.String(length=256), nullable=False),
        sa.Column("confidence", sa.Numeric(20, 10), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "candidate_id"),
    )
    op.create_index(
        "ix_portfolio_clusters_run",
        "portfolio_clusters",
        ["run_row_id", "cluster_id"],
    )

    op.create_table(
        "portfolio_risk_contributions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("portfolio_runs.id"), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("contribution_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "candidate_id"),
    )
    op.create_index(
        "ix_portfolio_risk_contrib_run",
        "portfolio_risk_contributions",
        ["run_row_id", "candidate_id"],
    )

    op.create_table(
        "portfolio_scenarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("portfolio_runs.id"), nullable=False),
        sa.Column("scenario_name", sa.String(length=128), nullable=False),
        sa.Column("portfolio_return", sa.Numeric(20, 10), nullable=False),
        sa.Column("portfolio_drawdown", sa.Numeric(20, 10), nullable=False),
        sa.Column("expected_shortfall", sa.Numeric(20, 10), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "scenario_name"),
    )
    op.create_index(
        "ix_portfolio_scenarios_run",
        "portfolio_scenarios",
        ["run_row_id", "scenario_name"],
    )

    op.create_table(
        "portfolio_rebalance_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("portfolio_runs.id"), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("previous_weight", sa.Numeric(20, 10), nullable=False),
        sa.Column("target_weight", sa.Numeric(20, 10), nullable=False),
        sa.Column("delta_weight", sa.Numeric(20, 10), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("trigger", sa.String(length=64), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.UniqueConstraint("run_row_id", "candidate_id"),
    )
    op.create_index(
        "ix_portfolio_rebalance_run",
        "portfolio_rebalance_plans",
        ["run_row_id", "as_of_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_rebalance_run", table_name="portfolio_rebalance_plans")
    op.drop_table("portfolio_rebalance_plans")

    op.drop_index("ix_portfolio_scenarios_run", table_name="portfolio_scenarios")
    op.drop_table("portfolio_scenarios")

    op.drop_index("ix_portfolio_risk_contrib_run", table_name="portfolio_risk_contributions")
    op.drop_table("portfolio_risk_contributions")

    op.drop_index("ix_portfolio_clusters_run", table_name="portfolio_clusters")
    op.drop_table("portfolio_clusters")

    op.drop_index("ix_portfolio_correlations_run", table_name="portfolio_correlations")
    op.drop_table("portfolio_correlations")

    op.drop_index("ix_portfolio_constraints_run", table_name="portfolio_constraint_outcomes")
    op.drop_table("portfolio_constraint_outcomes")

    op.drop_index("ix_portfolio_allocations_run", table_name="portfolio_allocations")
    op.drop_table("portfolio_allocations")

    op.drop_index("ix_portfolio_rejected_run", table_name="portfolio_rejected_candidates")
    op.drop_table("portfolio_rejected_candidates")

    op.drop_index("ix_portfolio_eligible_run", table_name="portfolio_eligible_candidates")
    op.drop_table("portfolio_eligible_candidates")

    op.drop_index("ix_portfolio_runs_strategy_ts", table_name="portfolio_runs")
    op.drop_table("portfolio_runs")
