"""Add Sprint 7C execution calibration, policy, validation, and stress persistence."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013_execution_calibration_policy_validation"
down_revision = "0012_margin_buying_power_liquidation_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_execution_calibration_datasets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("provider_manifest", sa.String(length=256), nullable=False),
        sa.Column("broker_policy_version", sa.String(length=128), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id", "dataset_id"),
    )
    op.create_index(
        "ix_backtest_exec_cal_datasets_run_ts",
        "backtest_execution_calibration_datasets",
        ["run_row_id", "created_at"],
    )

    op.create_table(
        "backtest_execution_fill_quality_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("observation_id", sa.String(length=128), nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("contract_identifier", sa.String(length=128), nullable=False),
        sa.Column("market_regime", sa.String(length=32), nullable=False),
        sa.Column("liquidity_regime", sa.String(length=32), nullable=False),
        sa.Column("volatility_regime", sa.String(length=32), nullable=False),
        sa.Column("strategy_family", sa.String(length=64), nullable=False),
        sa.Column("fill_ratio", sa.Numeric(20, 8), nullable=False),
        sa.Column("price_improvement", sa.Numeric(20, 8), nullable=False),
        sa.Column("price_disimprovement", sa.Numeric(20, 8), nullable=False),
        sa.Column("effective_spread", sa.Numeric(20, 8), nullable=True),
        sa.Column("realized_spread", sa.Numeric(20, 8), nullable=True),
        sa.Column("quoted_spread", sa.Numeric(20, 8), nullable=True),
        sa.Column("spread_capture", sa.Numeric(20, 8), nullable=True),
        sa.Column("slippage_vs_midpoint", sa.Numeric(20, 8), nullable=True),
        sa.Column("slippage_vs_arrival", sa.Numeric(20, 8), nullable=True),
        sa.Column("implementation_shortfall", sa.Numeric(20, 8), nullable=True),
        sa.Column("cancellation_rate", sa.Numeric(20, 8), nullable=False),
        sa.Column("timeout_rate", sa.Numeric(20, 8), nullable=False),
        sa.Column("partial_fill_rate", sa.Numeric(20, 8), nullable=False),
        sa.Column("delay_to_fill_seconds", sa.Numeric(20, 8), nullable=False),
        sa.Column("residual_quantity", sa.Integer(), nullable=False),
        sa.Column("legging_cost", sa.Numeric(20, 8), nullable=False),
        sa.Column("opportunity_cost", sa.Numeric(20, 8), nullable=False),
        sa.Column("execution_cost_bps", sa.Numeric(20, 8), nullable=False),
        sa.Column("execution_cost_dollars", sa.Numeric(20, 8), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "observation_id"),
    )
    op.create_index(
        "ix_backtest_exec_fill_quality_run_ts",
        "backtest_execution_fill_quality_observations",
        ["run_row_id", "event_timestamp"],
    )
    op.create_index(
        "ix_backtest_exec_fill_quality_symbol",
        "backtest_execution_fill_quality_observations",
        ["symbol", "event_timestamp"],
    )

    op.create_table(
        "backtest_execution_slippage_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("calibrated_parameters", sa.JSON(), nullable=False),
        sa.Column("confidence_intervals", sa.JSON(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("fit_diagnostics", sa.JSON(), nullable=False),
        sa.Column("residual_analysis", sa.JSON(), nullable=False),
        sa.Column("regime_coverage", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("validity_status", sa.String(length=32), nullable=False),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id", "model_id"),
    )
    op.create_index(
        "ix_backtest_exec_slippage_models_run",
        "backtest_execution_slippage_models",
        ["run_row_id", "calibrated_at"],
    )

    op.create_table(
        "backtest_execution_spread_capture_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("calibrated_parameters", sa.JSON(), nullable=False),
        sa.Column("confidence_intervals", sa.JSON(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("fit_diagnostics", sa.JSON(), nullable=False),
        sa.Column("residual_analysis", sa.JSON(), nullable=False),
        sa.Column("regime_coverage", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("validity_status", sa.String(length=32), nullable=False),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id", "model_id"),
    )
    op.create_index(
        "ix_backtest_exec_spread_models_run",
        "backtest_execution_spread_capture_models",
        ["run_row_id", "calibrated_at"],
    )

    op.create_table(
        "backtest_execution_partial_fill_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("fill_probability", sa.Numeric(20, 8), nullable=False),
        sa.Column("expected_fill_ratio", sa.Numeric(20, 8), nullable=False),
        sa.Column("cancellation_probability", sa.Numeric(20, 8), nullable=False),
        sa.Column("timeout_probability", sa.Numeric(20, 8), nullable=False),
        sa.Column("retry_probability", sa.Numeric(20, 8), nullable=False),
        sa.Column("expected_residual_quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("multi_leg_completion_probability", sa.Numeric(20, 8), nullable=False),
        sa.Column("legging_exposure_duration_seconds", sa.Numeric(20, 8), nullable=False),
        sa.Column("conditioned_on", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id", "model_id"),
    )
    op.create_index(
        "ix_backtest_exec_partial_models_run",
        "backtest_execution_partial_fill_models",
        ["run_row_id", "calibrated_at"],
    )

    op.create_table(
        "backtest_execution_transaction_cost_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("policy_id", sa.String(length=128), nullable=False),
        sa.Column("policy_name", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id", "policy_id"),
    )
    op.create_index(
        "ix_backtest_exec_cost_policies_run",
        "backtest_execution_transaction_cost_policies",
        ["run_row_id", "created_at"],
    )

    op.create_table(
        "backtest_execution_broker_policy_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("policy_name", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("source_reference_metadata", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("supported_instruments", sa.JSON(), nullable=False),
        sa.Column("unsupported_instruments", sa.JSON(), nullable=False),
        sa.Column("known_differences_from_official", sa.JSON(), nullable=False),
        sa.Column("deprecated_versions", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "policy_name", "policy_version"),
    )
    op.create_index(
        "ix_backtest_exec_policy_versions_run",
        "backtest_execution_broker_policy_versions",
        ["run_row_id", "effective_date"],
    )

    op.create_table(
        "backtest_execution_policy_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("comparison_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_policy", sa.String(length=128), nullable=False),
        sa.Column("right_policy", sa.String(length=128), nullable=False),
        sa.Column("commissions_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("exchange_fees_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("exercise_assignment_fees_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("buying_power_effect_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("maintenance_requirement_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("interest_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("borrow_cost_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("total_transaction_cost_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("total_return_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("cagr_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("drawdown_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("rejected_trades_diff", sa.Integer(), nullable=False),
        sa.Column("margin_breaches_diff", sa.Integer(), nullable=False),
        sa.Column("liquidations_diff", sa.Integer(), nullable=False),
        sa.Column("net_performance_diff", sa.Numeric(20, 8), nullable=False),
        sa.Column("ambiguity_warnings", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "comparison_id"),
    )
    op.create_index(
        "ix_backtest_exec_policy_comp_run_ts",
        "backtest_execution_policy_comparisons",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_execution_quality_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("score_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("contract_identifier", sa.String(length=128), nullable=False),
        sa.Column("total_score", sa.Numeric(20, 8), nullable=False),
        sa.Column("confidence", sa.Numeric(20, 8), nullable=False),
        sa.Column("component_scores", sa.JSON(), nullable=False),
        sa.Column("component_weights", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "score_id"),
    )
    op.create_index(
        "ix_backtest_exec_quality_scores_run_ts",
        "backtest_execution_quality_scores",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_execution_real_vs_simulated",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("comparison_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("contract_identifier", sa.String(length=128), nullable=False),
        sa.Column("simulated_fill_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("real_fill_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("expected_fill_distribution", sa.JSON(), nullable=False),
        sa.Column("price_error", sa.Numeric(20, 8), nullable=True),
        sa.Column("cost_error", sa.Numeric(20, 8), nullable=False),
        sa.Column("timing_error_seconds", sa.Numeric(20, 8), nullable=False),
        sa.Column("partial_fill_error", sa.Numeric(20, 8), nullable=False),
        sa.Column("fee_error", sa.Numeric(20, 8), nullable=False),
        sa.Column("policy_mismatch", sa.Boolean(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "comparison_id"),
    )
    op.create_index(
        "ix_backtest_exec_real_vs_sim_run_ts",
        "backtest_execution_real_vs_simulated",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_execution_validation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("validation_run_id", sa.String(length=128), nullable=False),
        sa.Column("split_type", sa.String(length=64), nullable=False),
        sa.Column("train_size", sa.Integer(), nullable=False),
        sa.Column("validation_size", sa.Integer(), nullable=False),
        sa.Column("error_distribution", sa.JSON(), nullable=False),
        sa.Column("calibration_drift", sa.Numeric(20, 8), nullable=False),
        sa.Column("parameter_drift", sa.Numeric(20, 8), nullable=False),
        sa.Column("out_of_sample_cost_error", sa.Numeric(20, 8), nullable=False),
        sa.Column("overconfidence_score", sa.Numeric(20, 8), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_row_id", "validation_run_id"),
    )
    op.create_index(
        "ix_backtest_exec_validation_runs_run",
        "backtest_execution_validation_runs",
        ["run_row_id", "created_at"],
    )

    op.create_table(
        "backtest_execution_calibration_drift",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("drift_id", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("calibration_drift", sa.Numeric(20, 8), nullable=False),
        sa.Column("parameter_drift", sa.Numeric(20, 8), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "drift_id"),
    )
    op.create_index(
        "ix_backtest_exec_cal_drift_run_ts",
        "backtest_execution_calibration_drift",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_execution_stress_test_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("scenario_name", sa.String(length=128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_cost_delta", sa.Numeric(20, 8), nullable=False),
        sa.Column("avg_fill_ratio", sa.Numeric(20, 8), nullable=False),
        sa.Column("avg_delay_seconds", sa.Numeric(20, 8), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "scenario_name", "event_timestamp"),
    )
    op.create_index(
        "ix_backtest_exec_stress_run_ts",
        "backtest_execution_stress_test_results",
        ["run_row_id", "event_timestamp"],
    )

    op.create_table(
        "backtest_execution_calibration_checksums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_row_id", sa.Integer(), sa.ForeignKey("backtest_runs.id"), nullable=False),
        sa.Column("checksum_key", sa.String(length=128), nullable=False),
        sa.Column("checksum_value", sa.String(length=256), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_row_id", "checksum_key"),
    )
    op.create_index(
        "ix_backtest_exec_cal_checksums_run",
        "backtest_execution_calibration_checksums",
        ["run_row_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_backtest_exec_cal_checksums_run",
        table_name="backtest_execution_calibration_checksums",
    )
    op.drop_table("backtest_execution_calibration_checksums")

    op.drop_index(
        "ix_backtest_exec_stress_run_ts",
        table_name="backtest_execution_stress_test_results",
    )
    op.drop_table("backtest_execution_stress_test_results")

    op.drop_index(
        "ix_backtest_exec_cal_drift_run_ts",
        table_name="backtest_execution_calibration_drift",
    )
    op.drop_table("backtest_execution_calibration_drift")

    op.drop_index(
        "ix_backtest_exec_validation_runs_run",
        table_name="backtest_execution_validation_runs",
    )
    op.drop_table("backtest_execution_validation_runs")

    op.drop_index(
        "ix_backtest_exec_real_vs_sim_run_ts",
        table_name="backtest_execution_real_vs_simulated",
    )
    op.drop_table("backtest_execution_real_vs_simulated")

    op.drop_index(
        "ix_backtest_exec_quality_scores_run_ts",
        table_name="backtest_execution_quality_scores",
    )
    op.drop_table("backtest_execution_quality_scores")

    op.drop_index(
        "ix_backtest_exec_policy_comp_run_ts",
        table_name="backtest_execution_policy_comparisons",
    )
    op.drop_table("backtest_execution_policy_comparisons")

    op.drop_index(
        "ix_backtest_exec_policy_versions_run",
        table_name="backtest_execution_broker_policy_versions",
    )
    op.drop_table("backtest_execution_broker_policy_versions")

    op.drop_index(
        "ix_backtest_exec_cost_policies_run",
        table_name="backtest_execution_transaction_cost_policies",
    )
    op.drop_table("backtest_execution_transaction_cost_policies")

    op.drop_index(
        "ix_backtest_exec_partial_models_run",
        table_name="backtest_execution_partial_fill_models",
    )
    op.drop_table("backtest_execution_partial_fill_models")

    op.drop_index(
        "ix_backtest_exec_spread_models_run",
        table_name="backtest_execution_spread_capture_models",
    )
    op.drop_table("backtest_execution_spread_capture_models")

    op.drop_index(
        "ix_backtest_exec_slippage_models_run",
        table_name="backtest_execution_slippage_models",
    )
    op.drop_table("backtest_execution_slippage_models")

    op.drop_index(
        "ix_backtest_exec_fill_quality_symbol",
        table_name="backtest_execution_fill_quality_observations",
    )
    op.drop_index(
        "ix_backtest_exec_fill_quality_run_ts",
        table_name="backtest_execution_fill_quality_observations",
    )
    op.drop_table("backtest_execution_fill_quality_observations")

    op.drop_index(
        "ix_backtest_exec_cal_datasets_run_ts",
        table_name="backtest_execution_calibration_datasets",
    )
    op.drop_table("backtest_execution_calibration_datasets")
