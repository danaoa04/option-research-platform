"""Add corporate-action reproducibility and snapshot tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_corporate_actions_snapshots"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_vendor_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("data_providers.id"), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("provider_record_id", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("source_metadata", sa.JSON(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("immutable", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("provider_id", "entity_type", "provider_record_id", "checksum"),
    )
    op.create_index(
        "ix_raw_vendor_records_provider_entity",
        "raw_vendor_records",
        ["provider_id", "entity_type"],
    )

    op.create_table(
        "normalized_corporate_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "raw_record_id",
            sa.Integer(),
            sa.ForeignKey("raw_vendor_records.id"),
            nullable=False,
        ),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("data_providers.id"), nullable=False),
        sa.Column(
            "manifest_id",
            sa.Integer(),
            sa.ForeignKey("dataset_manifests.id"),
            nullable=True,
        ),
        sa.Column("underlying_id", sa.Integer(), sa.ForeignKey("underlyings.id"), nullable=False),
        sa.Column("provider_action_id", sa.String(length=128), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("announcement_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ratio", sa.Numeric(20, 8), nullable=True),
        sa.Column("cash_amount", sa.Numeric(20, 8), nullable=True),
        sa.Column("multiplier_after", sa.Numeric(20, 8), nullable=True),
        sa.Column("deliverable_after", sa.Text(), nullable=True),
        sa.Column("terms", sa.JSON(), nullable=True),
        sa.Column("source_metadata", sa.JSON(), nullable=True),
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider_id", "provider_action_id"),
    )
    op.create_index(
        "ix_normalized_corp_actions_underlying_effective",
        "normalized_corporate_actions",
        ["underlying_id", "effective_date"],
    )

    op.create_table(
        "symbol_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("underlying_id", sa.Integer(), sa.ForeignKey("underlyings.id"), nullable=False),
        sa.Column("old_symbol", sa.String(length=32), nullable=False),
        sa.Column("new_symbol", sa.String(length=32), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("announcement_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("data_providers.id"), nullable=False),
        sa.Column(
            "source_action_id",
            sa.Integer(),
            sa.ForeignKey("normalized_corporate_actions.id"),
            nullable=True,
        ),
        sa.Column("source_metadata", sa.JSON(), nullable=True),
        sa.UniqueConstraint("underlying_id", "old_symbol", "new_symbol", "effective_date"),
    )
    op.create_index("ix_symbol_history_old_symbol", "symbol_history", ["old_symbol"])
    op.create_index("ix_symbol_history_new_symbol", "symbol_history", ["new_symbol"])

    op.create_table(
        "adjusted_underlying_price_views",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("underlying_id", sa.Integer(), sa.ForeignKey("underlyings.id"), nullable=False),
        sa.Column(
            "source_price_id",
            sa.BigInteger(),
            sa.ForeignKey("underlying_prices.id"),
            nullable=True,
        ),
        sa.Column(
            "source_action_id",
            sa.Integer(),
            sa.ForeignKey("normalized_corporate_actions.id"),
            nullable=True,
        ),
        sa.Column("view_name", sa.String(length=64), nullable=False),
        sa.Column("policy_name", sa.String(length=64), nullable=False),
        sa.Column("price_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("base_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("adjusted_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("adjustment_details", sa.JSON(), nullable=True),
        sa.CheckConstraint("base_price >= 0", name="adjusted_view_base_price_non_negative"),
        sa.CheckConstraint(
            "adjusted_price >= 0",
            name="adjusted_view_adjusted_price_non_negative",
        ),
        sa.UniqueConstraint("underlying_id", "price_timestamp", "view_name", "policy_name"),
    )
    op.create_index(
        "ix_adjusted_underlying_views_lookup",
        "adjusted_underlying_price_views",
        ["underlying_id", "view_name", "price_timestamp"],
    )

    op.create_table(
        "adjusted_option_contract_views",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "contract_id",
            sa.Integer(),
            sa.ForeignKey("option_contracts.id"),
            nullable=False,
        ),
        sa.Column(
            "source_action_id",
            sa.Integer(),
            sa.ForeignKey("normalized_corporate_actions.id"),
            nullable=True,
        ),
        sa.Column("view_name", sa.String(length=64), nullable=False),
        sa.Column("policy_name", sa.String(length=64), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("adjusted_strike", sa.Numeric(20, 8), nullable=False),
        sa.Column("adjusted_multiplier", sa.Numeric(20, 8), nullable=False),
        sa.Column("deliverable_after", sa.Text(), nullable=True),
        sa.Column("adjustment_details", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "adjusted_multiplier > 0",
            name="adjusted_contract_multiplier_positive",
        ),
        sa.CheckConstraint(
            "adjusted_strike >= 0",
            name="adjusted_contract_strike_non_negative",
        ),
        sa.UniqueConstraint("contract_id", "as_of_date", "view_name", "policy_name"),
    )
    op.create_index(
        "ix_adjusted_option_views_contract",
        "adjusted_option_contract_views",
        ["contract_id", "as_of_date"],
    )

    op.create_table(
        "dataset_snapshots",
        sa.Column("id", sa.String(length=96), primary_key=True),
        sa.Column(
            "manifest_id",
            sa.Integer(),
            sa.ForeignKey("dataset_manifests.id"),
            nullable=False,
        ),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("data_providers.id"), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("dataset_version", sa.String(length=64), nullable=False),
        sa.Column("git_commit", sa.String(length=64), nullable=False),
        sa.Column("date_start", sa.Date(), nullable=False),
        sa.Column("date_end", sa.Date(), nullable=False),
        sa.Column("symbol_scope", sa.JSON(), nullable=False),
        sa.Column("row_counts", sa.JSON(), nullable=False),
        sa.Column("checksums", sa.JSON(), nullable=False),
        sa.Column("transformation_history", sa.JSON(), nullable=False),
        sa.Column("validation_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "parent_snapshot_id",
            sa.String(length=96),
            sa.ForeignKey("dataset_snapshots.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
    )
    op.create_index("ix_dataset_snapshots_manifest", "dataset_snapshots", ["manifest_id"])
    op.create_index(
        "ix_dataset_snapshots_provider_created",
        "dataset_snapshots",
        ["provider_id", "created_at"],
    )

    op.create_table(
        "snapshot_source_manifests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.String(length=96),
            sa.ForeignKey("dataset_snapshots.id"),
            nullable=False,
        ),
        sa.Column(
            "source_manifest_id",
            sa.Integer(),
            sa.ForeignKey("dataset_manifests.id"),
            nullable=False,
        ),
        sa.UniqueConstraint("snapshot_id", "source_manifest_id"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("data_providers.id"), nullable=True),
        sa.Column(
            "manifest_id",
            sa.Integer(),
            sa.ForeignKey("dataset_manifests.id"),
            nullable=True,
        ),
        sa.Column(
            "snapshot_id",
            sa.String(length=96),
            sa.ForeignKey("dataset_snapshots.id"),
            nullable=True,
        ),
        sa.Column("correlation_id", sa.String(length=96), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    op.create_index("ix_audit_events_type_ts", "audit_events", ["event_type", "event_timestamp"])
    op.create_index("ix_audit_events_snapshot", "audit_events", ["snapshot_id"])

    op.add_column(
        "corporate_actions",
        sa.Column("announcement_timestamp", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "corporate_actions",
        sa.Column("provider_action_id", sa.String(length=128), nullable=True),
    )
    op.add_column("corporate_actions", sa.Column("cash_amount", sa.Numeric(20, 8), nullable=True))
    op.add_column(
        "corporate_actions",
        sa.Column("multiplier_after", sa.Numeric(20, 8), nullable=True),
    )
    op.add_column("corporate_actions", sa.Column("deliverable_after", sa.Text(), nullable=True))
    op.add_column("corporate_actions", sa.Column("source_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("corporate_actions", "source_metadata")
    op.drop_column("corporate_actions", "deliverable_after")
    op.drop_column("corporate_actions", "multiplier_after")
    op.drop_column("corporate_actions", "cash_amount")
    op.drop_column("corporate_actions", "provider_action_id")
    op.drop_column("corporate_actions", "announcement_timestamp")

    op.drop_index("ix_audit_events_snapshot", table_name="audit_events")
    op.drop_index("ix_audit_events_type_ts", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_table("snapshot_source_manifests")

    op.drop_index("ix_dataset_snapshots_provider_created", table_name="dataset_snapshots")
    op.drop_index("ix_dataset_snapshots_manifest", table_name="dataset_snapshots")
    op.drop_table("dataset_snapshots")

    op.drop_index("ix_adjusted_option_views_contract", table_name="adjusted_option_contract_views")
    op.drop_table("adjusted_option_contract_views")

    op.drop_index(
        "ix_adjusted_underlying_views_lookup",
        table_name="adjusted_underlying_price_views",
    )
    op.drop_table("adjusted_underlying_price_views")

    op.drop_index("ix_symbol_history_new_symbol", table_name="symbol_history")
    op.drop_index("ix_symbol_history_old_symbol", table_name="symbol_history")
    op.drop_table("symbol_history")

    op.drop_index(
        "ix_normalized_corp_actions_underlying_effective",
        table_name="normalized_corporate_actions",
    )
    op.drop_table("normalized_corporate_actions")

    op.drop_index("ix_raw_vendor_records_provider_entity", table_name="raw_vendor_records")
    op.drop_table("raw_vendor_records")
