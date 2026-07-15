"""Add calendar and multi-expiry research persistence tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_calendar_research_engine"
down_revision = "0003_volatility_analytics_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_type", sa.String(length=48), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("exit_date", sa.Date(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("software_version", sa.String(length=64), nullable=False),
        sa.Column(
            "manifest_id",
            sa.Integer(),
            sa.ForeignKey("dataset_manifests.id"),
            nullable=False,
        ),
        sa.Column("run_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checksums", sa.JSON(), nullable=False),
        sa.Column("quality_score", sa.Numeric(20, 8), nullable=True),
        sa.Column("summary_metrics", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_research_runs_symbol_ts", "research_runs", ["symbol", "run_timestamp"])
    op.create_index("ix_research_runs_quality", "research_runs", ["quality_score"])

    op.create_table(
        "research_opportunities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("research_runs.id"), nullable=False),
        sa.Column("as_of_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opportunity_score", sa.Numeric(20, 10), nullable=False),
        sa.Column("confidence", sa.Numeric(20, 10), nullable=False),
        sa.Column("historical_pop", sa.Numeric(20, 10), nullable=True),
        sa.Column("expected_value", sa.Numeric(20, 10), nullable=True),
        sa.Column("theta_capture", sa.Numeric(20, 10), nullable=True),
        sa.Column("quality_score", sa.Numeric(20, 10), nullable=True),
        sa.Column("term_structure_regime", sa.String(length=32), nullable=True),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "as_of_timestamp"),
    )
    op.create_index(
        "ix_research_opportunities_score",
        "research_opportunities",
        ["opportunity_score"],
    )
    op.create_index(
        "ix_research_opportunities_asof",
        "research_opportunities",
        ["as_of_timestamp"],
    )
    op.create_index(
        "ix_research_opportunities_regime",
        "research_opportunities",
        ["term_structure_regime"],
    )


def downgrade() -> None:
    op.drop_index("ix_research_opportunities_regime", table_name="research_opportunities")
    op.drop_index("ix_research_opportunities_asof", table_name="research_opportunities")
    op.drop_index("ix_research_opportunities_score", table_name="research_opportunities")
    op.drop_table("research_opportunities")

    op.drop_index("ix_research_runs_quality", table_name="research_runs")
    op.drop_index("ix_research_runs_symbol_ts", table_name="research_runs")
    op.drop_table("research_runs")
