"""Add Sprint 8A strategy library foundation tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014_strategy_library_foundation"
down_revision = "0013_execution_calibration_policy_validation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategy_template_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_identifier", sa.String(length=160), nullable=False),
        sa.Column("strategy_name", sa.String(length=160), nullable=False),
        sa.Column("strategy_family", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=48), nullable=False),
        sa.Column("supported_underlyings", sa.JSON(), nullable=False),
        sa.Column("supported_exercise_styles", sa.JSON(), nullable=False),
        sa.Column("supported_settlement_styles", sa.JSON(), nullable=False),
        sa.Column("supported_account_types", sa.JSON(), nullable=False),
        sa.Column("required_data", sa.JSON(), nullable=False),
        sa.Column("supported_lifecycle_policies", sa.JSON(), nullable=False),
        sa.Column("supported_roll_policies", sa.JSON(), nullable=False),
        sa.Column("known_limitations", sa.JSON(), nullable=False),
        sa.Column("deprecated", sa.Boolean(), nullable=False),
        sa.Column("replacement_identifier", sa.String(length=160), nullable=True),
        sa.Column("plugin_namespace", sa.String(length=160), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_identifier"),
    )
    op.create_index(
        "ix_strategy_template_registry_family",
        "strategy_template_registry",
        ["strategy_family", "strategy_name"],
    )

    op.create_table(
        "strategy_template_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_identifier", sa.String(length=160), nullable=False),
        sa.Column("template_version", sa.String(length=48), nullable=False),
        sa.Column("schema_version", sa.String(length=48), nullable=False),
        sa.Column("parameter_version", sa.String(length=48), nullable=False),
        sa.Column("definition_json", sa.JSON(), nullable=False),
        sa.Column("migration_hook", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_identifier", "template_version"),
    )
    op.create_index(
        "ix_strategy_template_versions_id",
        "strategy_template_versions",
        ["canonical_identifier", "template_version"],
    )

    op.create_table(
        "strategy_template_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_identifier", sa.String(length=160), nullable=False),
        sa.Column("alias", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("alias"),
    )
    op.create_index(
        "ix_strategy_template_aliases_identifier",
        "strategy_template_aliases",
        ["canonical_identifier", "alias"],
    )

    op.create_table(
        "strategy_parameter_schemas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_identifier", sa.String(length=160), nullable=False),
        sa.Column("template_version", sa.String(length=48), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_identifier", "template_version"),
    )
    op.create_index(
        "ix_strategy_parameter_schemas_identifier",
        "strategy_parameter_schemas",
        ["canonical_identifier", "template_version"],
    )

    op.create_table(
        "strategy_definition_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("strategy_definition_id", sa.String(length=160), nullable=False),
        sa.Column("canonical_identifier", sa.String(length=160), nullable=False),
        sa.Column("template_version", sa.String(length=48), nullable=False),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("reproducibility_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("strategy_definition_id"),
    )
    op.create_index(
        "ix_strategy_definition_documents_template",
        "strategy_definition_documents",
        ["canonical_identifier", "template_version"],
    )

    op.create_table(
        "strategy_definition_legs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("strategy_definition_id", sa.String(length=160), nullable=False),
        sa.Column("leg_label", sa.String(length=120), nullable=False),
        sa.Column("leg_kind", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("quantity_ratio", sa.Integer(), nullable=False),
        sa.Column("strike", sa.Numeric(20, 8), nullable=True),
        sa.Column("expiration", sa.Date(), nullable=True),
        sa.Column("option_type", sa.String(length=16), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("strategy_definition_id", "leg_label"),
    )
    op.create_index(
        "ix_strategy_definition_legs_definition",
        "strategy_definition_legs",
        ["strategy_definition_id", "leg_label"],
    )

    op.create_table(
        "strategy_validation_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("strategy_definition_id", sa.String(length=160), nullable=False),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("errors_json", sa.JSON(), nullable=False),
        sa.Column("warnings_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("strategy_definition_id"),
    )
    op.create_index(
        "ix_strategy_validation_results_status",
        "strategy_validation_results",
        ["validation_status", "created_at"],
    )

    op.create_table(
        "strategy_payoff_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("strategy_definition_id", sa.String(length=160), nullable=False),
        sa.Column("payoff_grid_json", sa.JSON(), nullable=False),
        sa.Column("maximum_profit", sa.Numeric(20, 8), nullable=True),
        sa.Column("maximum_loss", sa.Numeric(20, 8), nullable=True),
        sa.Column("breakevens_json", sa.JSON(), nullable=False),
        sa.Column("defined_risk", sa.Boolean(), nullable=False),
        sa.Column("capital_at_risk", sa.Numeric(20, 8), nullable=True),
        sa.Column("credit_or_debit", sa.String(length=16), nullable=False),
        sa.Column("slope_regions_json", sa.JSON(), nullable=False),
        sa.Column("discontinuities_json", sa.JSON(), nullable=False),
        sa.Column("residual_exposure_json", sa.JSON(), nullable=False),
        sa.Column("assignment_sensitive", sa.Boolean(), nullable=False),
        sa.Column("dividend_sensitive", sa.Boolean(), nullable=False),
        sa.Column("warnings_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("strategy_definition_id"),
    )
    op.create_index(
        "ix_strategy_payoff_summaries_definition",
        "strategy_payoff_summaries",
        ["strategy_definition_id", "created_at"],
    )

    op.create_table(
        "strategy_risk_classifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_identifier", sa.String(length=160), nullable=False),
        sa.Column("template_version", sa.String(length=48), nullable=False),
        sa.Column("risk_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_identifier", "template_version"),
    )
    op.create_index(
        "ix_strategy_risk_classifications_identifier",
        "strategy_risk_classifications",
        ["canonical_identifier", "template_version"],
    )

    op.create_table(
        "strategy_compatibility_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_identifier", sa.String(length=160), nullable=False),
        sa.Column("template_version", sa.String(length=48), nullable=False),
        sa.Column("compatibility_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_identifier", "template_version"),
    )
    op.create_index(
        "ix_strategy_compatibility_identifier",
        "strategy_compatibility_metadata",
        ["canonical_identifier", "template_version"],
    )

    op.create_table(
        "strategy_optimizer_contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_identifier", sa.String(length=160), nullable=False),
        sa.Column("template_version", sa.String(length=48), nullable=False),
        sa.Column("contract_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_identifier", "template_version"),
    )
    op.create_index(
        "ix_strategy_optimizer_contracts_identifier",
        "strategy_optimizer_contracts",
        ["canonical_identifier", "template_version"],
    )

    op.create_table(
        "strategy_template_checksums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checksum_key", sa.String(length=160), nullable=False),
        sa.Column("checksum_value", sa.String(length=256), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("checksum_key"),
    )
    op.create_index(
        "ix_strategy_template_checksums_created",
        "strategy_template_checksums",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_strategy_template_checksums_created", table_name="strategy_template_checksums"
    )
    op.drop_table("strategy_template_checksums")

    op.drop_index(
        "ix_strategy_optimizer_contracts_identifier",
        table_name="strategy_optimizer_contracts",
    )
    op.drop_table("strategy_optimizer_contracts")

    op.drop_index(
        "ix_strategy_compatibility_identifier", table_name="strategy_compatibility_metadata"
    )
    op.drop_table("strategy_compatibility_metadata")

    op.drop_index(
        "ix_strategy_risk_classifications_identifier",
        table_name="strategy_risk_classifications",
    )
    op.drop_table("strategy_risk_classifications")

    op.drop_index("ix_strategy_payoff_summaries_definition", table_name="strategy_payoff_summaries")
    op.drop_table("strategy_payoff_summaries")

    op.drop_index("ix_strategy_validation_results_status", table_name="strategy_validation_results")
    op.drop_table("strategy_validation_results")

    op.drop_index("ix_strategy_definition_legs_definition", table_name="strategy_definition_legs")
    op.drop_table("strategy_definition_legs")

    op.drop_index(
        "ix_strategy_definition_documents_template",
        table_name="strategy_definition_documents",
    )
    op.drop_table("strategy_definition_documents")

    op.drop_index(
        "ix_strategy_parameter_schemas_identifier",
        table_name="strategy_parameter_schemas",
    )
    op.drop_table("strategy_parameter_schemas")

    op.drop_index("ix_strategy_template_aliases_identifier", table_name="strategy_template_aliases")
    op.drop_table("strategy_template_aliases")

    op.drop_index("ix_strategy_template_versions_id", table_name="strategy_template_versions")
    op.drop_table("strategy_template_versions")

    op.drop_index("ix_strategy_template_registry_family", table_name="strategy_template_registry")
    op.drop_table("strategy_template_registry")
