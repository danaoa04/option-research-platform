"""Add volatility observation and time-slice persistence tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_volatility_analytics_foundation"
down_revision = "0002_corporate_actions_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "volatility_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("valuation_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expiration", sa.Date(), nullable=False),
        sa.Column("strike", sa.Numeric(20, 8), nullable=False),
        sa.Column("option_type", sa.String(length=8), nullable=False),
        sa.Column("moneyness", sa.Numeric(20, 10), nullable=False),
        sa.Column("forward_moneyness", sa.Numeric(20, 10), nullable=True),
        sa.Column("delta", sa.Numeric(20, 10), nullable=True),
        sa.Column("implied_volatility", sa.Numeric(20, 10), nullable=False),
        sa.Column("quote_source", sa.String(length=16), nullable=False),
        sa.Column("pricing_model", sa.String(length=64), nullable=False),
        sa.Column("solver_method", sa.String(length=32), nullable=False),
        sa.Column("solver_status", sa.String(length=32), nullable=False),
        sa.Column("pricing_error", sa.Numeric(20, 12), nullable=True),
        sa.Column("bid", sa.Numeric(20, 8), nullable=True),
        sa.Column("ask", sa.Numeric(20, 8), nullable=True),
        sa.Column("midpoint", sa.Numeric(20, 8), nullable=True),
        sa.Column("spread_width", sa.Numeric(20, 8), nullable=True),
        sa.Column("volume", sa.Integer(), nullable=True),
        sa.Column("open_interest", sa.Integer(), nullable=True),
        sa.Column("stale_age_seconds", sa.Numeric(20, 6), nullable=True),
        sa.Column("vega", sa.Numeric(20, 12), nullable=True),
        sa.Column("tree_sensitivity", sa.Numeric(20, 12), nullable=True),
        sa.Column("quality_score", sa.Numeric(20, 8), nullable=True),
        sa.Column("quality_flags", sa.JSON(), nullable=False),
        sa.Column("contract_metadata", sa.JSON(), nullable=False),
        sa.Column("solver_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "manifest_id",
            sa.Integer(),
            sa.ForeignKey("dataset_manifests.id"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "symbol",
            "valuation_timestamp",
            "expiration",
            "strike",
            "option_type",
            "quote_source",
            "pricing_model",
            "manifest_id",
        ),
        sa.CheckConstraint("strike >= 0", name="vol_obs_strike_non_negative"),
        sa.CheckConstraint("implied_volatility >= 0", name="vol_obs_iv_non_negative"),
        sa.CheckConstraint("moneyness >= 0", name="vol_obs_moneyness_non_negative"),
    )
    op.create_index(
        "ix_vol_obs_symbol_ts_exp",
        "volatility_observations",
        ["symbol", "valuation_timestamp", "expiration"],
    )
    op.create_index(
        "ix_vol_obs_symbol_quality",
        "volatility_observations",
        ["symbol", "quality_score"],
    )

    op.create_table(
        "volatility_time_slices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slice_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("valuation_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("slice_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("input_manifests", sa.JSON(), nullable=False),
        sa.Column("solver_metadata", sa.JSON(), nullable=False),
        sa.Column("filtering_policy", sa.JSON(), nullable=False),
        sa.Column("interpolation_policy", sa.JSON(), nullable=False),
        sa.Column("tree_step_policy", sa.JSON(), nullable=False),
        sa.Column("quality_thresholds", sa.JSON(), nullable=False),
        sa.Column("node_count", sa.Integer(), nullable=False),
        sa.Column("excluded_observation_count", sa.Integer(), nullable=False),
        sa.Column("checksums", sa.JSON(), nullable=False),
        sa.Column("git_commit", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "parent_snapshot_id",
            sa.String(length=96),
            sa.ForeignKey("dataset_snapshots.id"),
            nullable=True,
        ),
        sa.UniqueConstraint("slice_id"),
    )
    op.create_index(
        "ix_vol_slices_symbol_ts",
        "volatility_time_slices",
        ["symbol", "valuation_timestamp"],
    )
    op.create_index(
        "ix_vol_slices_kind_status",
        "volatility_time_slices",
        ["slice_kind", "status"],
    )

    op.create_table(
        "volatility_time_slice_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "slice_id",
            sa.Integer(),
            sa.ForeignKey("volatility_time_slices.id"),
            nullable=False,
        ),
        sa.Column("tenor_days", sa.Integer(), nullable=False),
        sa.Column("x", sa.Numeric(20, 10), nullable=False),
        sa.Column("implied_volatility", sa.Numeric(20, 10), nullable=False),
        sa.Column("node_kind", sa.String(length=24), nullable=False),
        sa.Column("confidence_score", sa.Numeric(20, 10), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.UniqueConstraint("slice_id", "tenor_days", "x", "node_kind"),
    )
    op.create_index(
        "ix_vol_slice_nodes_slice",
        "volatility_time_slice_nodes",
        ["slice_id", "node_kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_vol_slice_nodes_slice", table_name="volatility_time_slice_nodes")
    op.drop_table("volatility_time_slice_nodes")

    op.drop_index("ix_vol_slices_kind_status", table_name="volatility_time_slices")
    op.drop_index("ix_vol_slices_symbol_ts", table_name="volatility_time_slices")
    op.drop_table("volatility_time_slices")

    op.drop_index("ix_vol_obs_symbol_quality", table_name="volatility_observations")
    op.drop_index("ix_vol_obs_symbol_ts_exp", table_name="volatility_observations")
    op.drop_table("volatility_observations")
