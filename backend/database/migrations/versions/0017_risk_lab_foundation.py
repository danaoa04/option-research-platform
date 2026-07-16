"""Add Sprint 9A risk lab and scenario engine foundation tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_risk_lab_foundation"
down_revision = "0016_strategy_management_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_factor_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("factor_id", sa.String(length=160), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("shock_type", sa.String(length=64), nullable=False),
        sa.Column("supported_instruments", sa.JSON(), nullable=False),
        sa.Column("supported_aggregation", sa.JSON(), nullable=False),
        sa.Column("transformation_rules", sa.JSON(), nullable=False),
        sa.Column("validation_rules", sa.JSON(), nullable=False),
        sa.Column("known_limitations", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("factor_id"),
    )
    op.create_index(
        "ix_risk_factor_definitions_factor",
        "risk_factor_definitions",
        ["factor_id", "created_at"],
    )

    op.create_table(
        "risk_scenario_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scenario_id", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("scenario_family", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=400), nullable=False),
        sa.Column("source_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scenario_id"),
    )
    op.create_index(
        "ix_risk_scenario_definitions_family",
        "risk_scenario_definitions",
        ["scenario_family", "scenario_id"],
    )

    op.create_table(
        "risk_scenario_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scenario_id", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("valuation_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon_seconds", sa.Numeric(20, 8), nullable=False),
        sa.Column("shock_ordering", sa.JSON(), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("market_regime_assumptions", sa.JSON(), nullable=False),
        sa.Column("execution_assumptions", sa.JSON(), nullable=False),
        sa.Column("margin_assumptions", sa.JSON(), nullable=False),
        sa.Column("data_quality_assumptions", sa.JSON(), nullable=False),
        sa.Column("affected_symbols", sa.JSON(), nullable=False),
        sa.Column("affected_sectors", sa.JSON(), nullable=False),
        sa.Column("affected_strategy_families", sa.JSON(), nullable=False),
        sa.Column("probability_metadata", sa.JSON(), nullable=False),
        sa.Column("reproducibility_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scenario_id", "version"),
    )
    op.create_index(
        "ix_risk_scenario_versions_scenario",
        "risk_scenario_versions",
        ["scenario_id", "version"],
    )

    op.create_table(
        "risk_scenario_shocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scenario_id", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("ordering", sa.Integer(), nullable=False),
        sa.Column("factor_id", sa.String(length=160), nullable=False),
        sa.Column("shock_type", sa.String(length=64), nullable=False),
        sa.Column("magnitude", sa.Numeric(20, 10), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("scenario_id", "version", "ordering", "factor_id"),
    )
    op.create_index(
        "ix_risk_scenario_shocks_scenario",
        "risk_scenario_shocks",
        ["scenario_id", "version"],
    )

    op.create_table(
        "risk_scenario_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("portfolio_id", sa.String(length=160), nullable=False),
        sa.Column("scenario_id", sa.String(length=160), nullable=False),
        sa.Column("scenario_version", sa.String(length=64), nullable=False),
        sa.Column("as_of_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("software_git_commit", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(
        "ix_risk_scenario_runs_ts",
        "risk_scenario_runs",
        ["created_at", "scenario_id"],
    )

    op.create_table(
        "risk_instrument_scenario_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("instrument_id", sa.String(length=160), nullable=False),
        sa.Column("strategy_id", sa.String(length=160), nullable=False),
        sa.Column("original_value", sa.Numeric(20, 10), nullable=False),
        sa.Column("shocked_value", sa.Numeric(20, 10), nullable=False),
        sa.Column("value_change", sa.Numeric(20, 10), nullable=False),
        sa.Column("original_greeks", sa.JSON(), nullable=False),
        sa.Column("shocked_greeks", sa.JSON(), nullable=False),
        sa.Column("model_used", sa.String(length=128), nullable=False),
        sa.Column("convergence_diagnostics", sa.JSON(), nullable=False),
        sa.Column("quality_warnings", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "instrument_id"),
    )
    op.create_index(
        "ix_risk_instrument_results_run",
        "risk_instrument_scenario_results",
        ["run_id", "instrument_id"],
    )

    op.create_table(
        "risk_strategy_scenario_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("strategy_id", sa.String(length=160), nullable=False),
        sa.Column("pnl_impact", sa.Numeric(20, 10), nullable=False),
        sa.Column("greeks_impact", sa.JSON(), nullable=False),
        sa.Column("margin_impact", sa.Numeric(20, 10), nullable=False),
        sa.Column("buying_power_impact", sa.Numeric(20, 10), nullable=False),
        sa.Column("assignment_risk_change", sa.Numeric(20, 10), nullable=False),
        sa.Column("exercise_risk_change", sa.Numeric(20, 10), nullable=False),
        sa.Column("dividend_risk_change", sa.Numeric(20, 10), nullable=False),
        sa.Column("liquidity_impact", sa.Numeric(20, 10), nullable=False),
        sa.Column("management_policy_triggers", sa.JSON(), nullable=False),
        sa.Column("roll_eligibility_changes", sa.JSON(), nullable=False),
        sa.Column("residual_exposure", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "strategy_id"),
    )
    op.create_index(
        "ix_risk_strategy_results_run",
        "risk_strategy_scenario_results",
        ["run_id", "strategy_id"],
    )

    op.create_table(
        "risk_portfolio_scenario_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("portfolio_id", sa.String(length=160), nullable=False),
        sa.Column("portfolio_pnl", sa.Numeric(20, 10), nullable=False),
        sa.Column("portfolio_return", sa.Numeric(20, 10), nullable=False),
        sa.Column("greeks", sa.JSON(), nullable=False),
        sa.Column("expected_shortfall", sa.Numeric(20, 10), nullable=False),
        sa.Column("margin", sa.Numeric(20, 10), nullable=False),
        sa.Column("buying_power", sa.Numeric(20, 10), nullable=False),
        sa.Column("cash", sa.Numeric(20, 10), nullable=False),
        sa.Column("concentration", sa.JSON(), nullable=False),
        sa.Column("liquidity", sa.Numeric(20, 10), nullable=False),
        sa.Column("assignment_exposure", sa.Numeric(20, 10), nullable=False),
        sa.Column("liquidation_requirement", sa.Numeric(20, 10), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "portfolio_id"),
    )
    op.create_index(
        "ix_risk_portfolio_results_run",
        "risk_portfolio_scenario_results",
        ["run_id", "portfolio_id"],
    )

    op.create_table(
        "risk_scenario_greeks_impacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("scope_id", sa.String(length=160), nullable=False),
        sa.Column("delta_change", sa.Numeric(20, 10), nullable=False),
        sa.Column("gamma_change", sa.Numeric(20, 10), nullable=False),
        sa.Column("theta_change", sa.Numeric(20, 10), nullable=False),
        sa.Column("vega_change", sa.Numeric(20, 10), nullable=False),
        sa.Column("rho_change", sa.Numeric(20, 10), nullable=False),
        sa.UniqueConstraint("run_id", "scope", "scope_id"),
    )
    op.create_index(
        "ix_risk_greeks_impacts_run",
        "risk_scenario_greeks_impacts",
        ["run_id", "scope"],
    )

    op.create_table(
        "risk_scenario_margin_impacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("scope_id", sa.String(length=160), nullable=False),
        sa.Column("pre_margin", sa.Numeric(20, 10), nullable=False),
        sa.Column("post_margin", sa.Numeric(20, 10), nullable=False),
        sa.Column("excess_liquidity", sa.Numeric(20, 10), nullable=False),
        sa.Column("deficit", sa.Numeric(20, 10), nullable=False),
        sa.Column("liquidation_requirement", sa.Numeric(20, 10), nullable=False),
        sa.Column("candidate_liquidation_plans", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "scope", "scope_id"),
    )
    op.create_index(
        "ix_risk_margin_impacts_run",
        "risk_scenario_margin_impacts",
        ["run_id", "scope"],
    )

    op.create_table(
        "risk_scenario_liquidity_impacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("scope_id", sa.String(length=160), nullable=False),
        sa.Column("spread_multiplier", sa.Numeric(20, 10), nullable=False),
        sa.Column("stale_quote_rate", sa.Numeric(20, 10), nullable=False),
        sa.Column("no_fill_probability", sa.Numeric(20, 10), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "scope", "scope_id"),
    )
    op.create_index(
        "ix_risk_liquidity_impacts_run",
        "risk_scenario_liquidity_impacts",
        ["run_id", "scope"],
    )

    op.create_table(
        "risk_scenario_matrices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("matrix_id", sa.String(length=160), nullable=False),
        sa.Column("row_key", sa.String(length=128), nullable=False),
        sa.Column("column_key", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "matrix_id", "row_key", "column_key"),
    )
    op.create_index(
        "ix_risk_scenario_matrices_run",
        "risk_scenario_matrices",
        ["run_id", "matrix_id"],
    )

    op.create_table(
        "risk_attributions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("attribution_id", sa.String(length=160), nullable=False),
        sa.Column("components_json", sa.JSON(), nullable=False),
        sa.Column("unexplained_residual", sa.Numeric(20, 10), nullable=False),
        sa.Column("approximate", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("run_id", "attribution_id"),
    )
    op.create_index(
        "ix_risk_attributions_run",
        "risk_attributions",
        ["run_id", "attribution_id"],
    )

    op.create_table(
        "risk_limit_breaches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("metric", sa.String(length=128), nullable=False),
        sa.Column("observed", sa.Numeric(20, 10), nullable=False),
        sa.Column("threshold", sa.Numeric(20, 10), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("remediation_candidates", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "metric"),
    )
    op.create_index(
        "ix_risk_limit_breaches_run",
        "risk_limit_breaches",
        ["run_id", "severity"],
    )

    op.create_table(
        "risk_management_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("comparison_id", sa.String(length=160), nullable=False),
        sa.Column("alternatives_json", sa.JSON(), nullable=False),
        sa.Column("selected_action", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("run_id", "comparison_id"),
    )
    op.create_index(
        "ix_risk_management_comparisons_run",
        "risk_management_comparisons",
        ["run_id", "comparison_id"],
    )

    op.create_table(
        "historical_scenario_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scenario_id", sa.String(length=160), nullable=False),
        sa.Column("scenario_family", sa.String(length=64), nullable=False),
        sa.Column("fixture_payload", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scenario_id"),
    )
    op.create_index(
        "ix_historical_scenario_metadata_family",
        "historical_scenario_metadata",
        ["scenario_family", "scenario_id"],
    )

    op.create_table(
        "risk_quality_diagnostics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=160), nullable=False),
        sa.Column("diagnostic_id", sa.String(length=160), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Numeric(20, 10), nullable=False),
        sa.Column("data_support", sa.Numeric(20, 10), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("model_limitations", sa.JSON(), nullable=False),
        sa.Column("missing_data_warnings", sa.JSON(), nullable=False),
        sa.Column("calibration_status", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("run_id", "diagnostic_id"),
    )
    op.create_index(
        "ix_risk_quality_diagnostics_run",
        "risk_quality_diagnostics",
        ["run_id", "severity"],
    )

    op.create_table(
        "risk_reproducibility_checksums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checksum_key", sa.String(length=160), nullable=False),
        sa.Column("checksum_value", sa.String(length=256), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("checksum_key"),
    )
    op.create_index(
        "ix_risk_reproducibility_checksums_created",
        "risk_reproducibility_checksums",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_risk_reproducibility_checksums_created",
        table_name="risk_reproducibility_checksums",
    )
    op.drop_table("risk_reproducibility_checksums")

    op.drop_index("ix_risk_quality_diagnostics_run", table_name="risk_quality_diagnostics")
    op.drop_table("risk_quality_diagnostics")

    op.drop_index(
        "ix_historical_scenario_metadata_family",
        table_name="historical_scenario_metadata",
    )
    op.drop_table("historical_scenario_metadata")

    op.drop_index(
        "ix_risk_management_comparisons_run",
        table_name="risk_management_comparisons",
    )
    op.drop_table("risk_management_comparisons")

    op.drop_index("ix_risk_limit_breaches_run", table_name="risk_limit_breaches")
    op.drop_table("risk_limit_breaches")

    op.drop_index("ix_risk_attributions_run", table_name="risk_attributions")
    op.drop_table("risk_attributions")

    op.drop_index("ix_risk_scenario_matrices_run", table_name="risk_scenario_matrices")
    op.drop_table("risk_scenario_matrices")

    op.drop_index(
        "ix_risk_liquidity_impacts_run",
        table_name="risk_scenario_liquidity_impacts",
    )
    op.drop_table("risk_scenario_liquidity_impacts")

    op.drop_index("ix_risk_margin_impacts_run", table_name="risk_scenario_margin_impacts")
    op.drop_table("risk_scenario_margin_impacts")

    op.drop_index("ix_risk_greeks_impacts_run", table_name="risk_scenario_greeks_impacts")
    op.drop_table("risk_scenario_greeks_impacts")

    op.drop_index(
        "ix_risk_portfolio_results_run",
        table_name="risk_portfolio_scenario_results",
    )
    op.drop_table("risk_portfolio_scenario_results")

    op.drop_index(
        "ix_risk_strategy_results_run",
        table_name="risk_strategy_scenario_results",
    )
    op.drop_table("risk_strategy_scenario_results")

    op.drop_index(
        "ix_risk_instrument_results_run",
        table_name="risk_instrument_scenario_results",
    )
    op.drop_table("risk_instrument_scenario_results")

    op.drop_index("ix_risk_scenario_runs_ts", table_name="risk_scenario_runs")
    op.drop_table("risk_scenario_runs")

    op.drop_index("ix_risk_scenario_shocks_scenario", table_name="risk_scenario_shocks")
    op.drop_table("risk_scenario_shocks")

    op.drop_index("ix_risk_scenario_versions_scenario", table_name="risk_scenario_versions")
    op.drop_table("risk_scenario_versions")

    op.drop_index(
        "ix_risk_scenario_definitions_family",
        table_name="risk_scenario_definitions",
    )
    op.drop_table("risk_scenario_definitions")

    op.drop_index(
        "ix_risk_factor_definitions_factor",
        table_name="risk_factor_definitions",
    )
    op.drop_table("risk_factor_definitions")
