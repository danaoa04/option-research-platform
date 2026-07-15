"""Repositories for Sprint 7C execution calibration persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import Select, Table, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import (
    BacktestExecutionBrokerPolicyVersionRecord,
    BacktestExecutionCalibrationChecksumRecord,
    BacktestExecutionCalibrationDatasetRecord,
    BacktestExecutionCalibrationDriftRecord,
    BacktestExecutionFillQualityObservationRecord,
    BacktestExecutionPartialFillModelRecord,
    BacktestExecutionPolicyComparisonRecord,
    BacktestExecutionQualityScoreRecord,
    BacktestExecutionRealVsSimulatedRecord,
    BacktestExecutionSlippageModelRecord,
    BacktestExecutionSpreadCaptureModelRecord,
    BacktestExecutionStressTestResultRecord,
    BacktestExecutionTransactionCostPolicyRecord,
    BacktestExecutionValidationRunRecord,
)

from .base import RepositoryBase


class _BulkRunScopedRepository(RepositoryBase[object]):
    model: type
    conflict_columns: tuple[str, ...]
    update_columns: tuple[str, ...]

    def upsert_rows(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        table = cast(Table, getattr(self.model, "__table__"))
        stmt = sqlite_insert(table).values(list(rows)).execution_options(dml_strategy="raw")
        index_elements = [getattr(table.c, key) for key in self.conflict_columns]
        set_payload = {key: getattr(stmt.excluded, key) for key in self.update_columns}
        self.session.execute(
            stmt.on_conflict_do_update(index_elements=index_elements, set_=set_payload)
        )


class BacktestExecutionCalibrationDatasetRepository(_BulkRunScopedRepository):
    model = BacktestExecutionCalibrationDatasetRecord
    conflict_columns = ("run_row_id", "dataset_id")
    update_columns = (
        "source_type",
        "provider_manifest",
        "broker_policy_version",
        "sample_count",
        "filters_json",
        "metadata",
        "created_at",
    )


class BacktestExecutionFillQualityObservationRepository(_BulkRunScopedRepository):
    model = BacktestExecutionFillQualityObservationRecord
    conflict_columns = ("run_row_id", "observation_id")
    update_columns = (
        "dataset_id",
        "event_timestamp",
        "symbol",
        "contract_identifier",
        "market_regime",
        "liquidity_regime",
        "volatility_regime",
        "strategy_family",
        "fill_ratio",
        "price_improvement",
        "price_disimprovement",
        "effective_spread",
        "realized_spread",
        "quoted_spread",
        "spread_capture",
        "slippage_vs_midpoint",
        "slippage_vs_arrival",
        "implementation_shortfall",
        "cancellation_rate",
        "timeout_rate",
        "partial_fill_rate",
        "delay_to_fill_seconds",
        "residual_quantity",
        "legging_cost",
        "opportunity_cost",
        "execution_cost_bps",
        "execution_cost_dollars",
        "metadata",
    )


class BacktestExecutionSlippageModelRepository(_BulkRunScopedRepository):
    model = BacktestExecutionSlippageModelRecord
    conflict_columns = ("run_row_id", "model_id")
    update_columns = (
        "dataset_id",
        "model_name",
        "calibrated_parameters",
        "confidence_intervals",
        "sample_size",
        "fit_diagnostics",
        "residual_analysis",
        "regime_coverage",
        "warnings",
        "validity_status",
        "calibrated_at",
    )


class BacktestExecutionSpreadCaptureModelRepository(_BulkRunScopedRepository):
    model = BacktestExecutionSpreadCaptureModelRecord
    conflict_columns = ("run_row_id", "model_id")
    update_columns = (
        "dataset_id",
        "model_name",
        "calibrated_parameters",
        "confidence_intervals",
        "sample_size",
        "fit_diagnostics",
        "residual_analysis",
        "regime_coverage",
        "warnings",
        "validity_status",
        "calibrated_at",
    )


class BacktestExecutionPartialFillModelRepository(_BulkRunScopedRepository):
    model = BacktestExecutionPartialFillModelRecord
    conflict_columns = ("run_row_id", "model_id")
    update_columns = (
        "dataset_id",
        "fill_probability",
        "expected_fill_ratio",
        "cancellation_probability",
        "timeout_probability",
        "retry_probability",
        "expected_residual_quantity",
        "multi_leg_completion_probability",
        "legging_exposure_duration_seconds",
        "conditioned_on",
        "warnings",
        "calibrated_at",
    )


class BacktestExecutionTransactionCostPolicyRepository(_BulkRunScopedRepository):
    model = BacktestExecutionTransactionCostPolicyRecord
    conflict_columns = ("run_row_id", "policy_id")
    update_columns = (
        "policy_name",
        "policy_version",
        "policy_json",
        "metadata",
        "created_at",
    )


class BacktestExecutionBrokerPolicyVersionRepository(_BulkRunScopedRepository):
    model = BacktestExecutionBrokerPolicyVersionRecord
    conflict_columns = ("run_row_id", "policy_name", "policy_version")
    update_columns = (
        "effective_date",
        "source_reference_metadata",
        "assumptions",
        "supported_instruments",
        "unsupported_instruments",
        "known_differences_from_official",
        "deprecated_versions",
    )


class BacktestExecutionPolicyComparisonRepository(_BulkRunScopedRepository):
    model = BacktestExecutionPolicyComparisonRecord
    conflict_columns = ("run_row_id", "comparison_id")
    update_columns = (
        "event_timestamp",
        "left_policy",
        "right_policy",
        "commissions_diff",
        "exchange_fees_diff",
        "exercise_assignment_fees_diff",
        "buying_power_effect_diff",
        "maintenance_requirement_diff",
        "interest_diff",
        "borrow_cost_diff",
        "total_transaction_cost_diff",
        "total_return_diff",
        "cagr_diff",
        "drawdown_diff",
        "rejected_trades_diff",
        "margin_breaches_diff",
        "liquidations_diff",
        "net_performance_diff",
        "ambiguity_warnings",
    )


class BacktestExecutionQualityScoreRepository(_BulkRunScopedRepository):
    model = BacktestExecutionQualityScoreRecord
    conflict_columns = ("run_row_id", "score_id")
    update_columns = (
        "event_timestamp",
        "symbol",
        "contract_identifier",
        "total_score",
        "confidence",
        "component_scores",
        "component_weights",
        "warnings",
    )

    def history(
        self,
        *,
        run_row_id: int,
        symbol: str | None = None,
    ) -> list[BacktestExecutionQualityScoreRecord]:
        stmt: Select[tuple[BacktestExecutionQualityScoreRecord]] = select(
            BacktestExecutionQualityScoreRecord
        ).where(BacktestExecutionQualityScoreRecord.run_row_id == run_row_id)
        if symbol:
            stmt = stmt.where(BacktestExecutionQualityScoreRecord.symbol == symbol)
        stmt = stmt.order_by(BacktestExecutionQualityScoreRecord.event_timestamp.asc())
        return list(self.session.execute(stmt).scalars())


class BacktestExecutionRealVsSimulatedRepository(_BulkRunScopedRepository):
    model = BacktestExecutionRealVsSimulatedRecord
    conflict_columns = ("run_row_id", "comparison_id")
    update_columns = (
        "event_timestamp",
        "symbol",
        "contract_identifier",
        "simulated_fill_price",
        "real_fill_price",
        "expected_fill_distribution",
        "price_error",
        "cost_error",
        "timing_error_seconds",
        "partial_fill_error",
        "fee_error",
        "policy_mismatch",
        "warnings",
    )


class BacktestExecutionValidationRunRepository(_BulkRunScopedRepository):
    model = BacktestExecutionValidationRunRecord
    conflict_columns = ("run_row_id", "validation_run_id")
    update_columns = (
        "split_type",
        "train_size",
        "validation_size",
        "error_distribution",
        "calibration_drift",
        "parameter_drift",
        "out_of_sample_cost_error",
        "overconfidence_score",
        "warnings",
        "created_at",
    )


class BacktestExecutionCalibrationDriftRepository(_BulkRunScopedRepository):
    model = BacktestExecutionCalibrationDriftRecord
    conflict_columns = ("run_row_id", "drift_id")
    update_columns = (
        "event_timestamp",
        "model_name",
        "calibration_drift",
        "parameter_drift",
        "diagnostics_json",
    )


class BacktestExecutionStressTestResultRepository(_BulkRunScopedRepository):
    model = BacktestExecutionStressTestResultRecord
    conflict_columns = ("run_row_id", "scenario_name", "event_timestamp")
    update_columns = (
        "total_cost_delta",
        "avg_fill_ratio",
        "avg_delay_seconds",
        "warnings",
        "diagnostics_json",
    )


class BacktestExecutionCalibrationChecksumRepository(_BulkRunScopedRepository):
    model = BacktestExecutionCalibrationChecksumRecord
    conflict_columns = ("run_row_id", "checksum_key")
    update_columns = ("checksum_value", "metadata")


class BacktestExecutionFillQualityQueryRepository(
    RepositoryBase[BacktestExecutionFillQualityObservationRecord]
):
    def history(
        self,
        *,
        run_row_id: int,
        symbol: str | None = None,
        strategy_family: str | None = None,
    ) -> list[BacktestExecutionFillQualityObservationRecord]:
        stmt: Select[tuple[BacktestExecutionFillQualityObservationRecord]] = select(
            BacktestExecutionFillQualityObservationRecord
        ).where(BacktestExecutionFillQualityObservationRecord.run_row_id == run_row_id)
        if symbol:
            stmt = stmt.where(BacktestExecutionFillQualityObservationRecord.symbol == symbol)
        if strategy_family:
            stmt = stmt.where(
                BacktestExecutionFillQualityObservationRecord.strategy_family == strategy_family
            )
        stmt = stmt.order_by(BacktestExecutionFillQualityObservationRecord.event_timestamp.asc())
        return list(self.session.execute(stmt).scalars())


class BacktestExecutionStressTestQueryRepository(
    RepositoryBase[BacktestExecutionStressTestResultRecord]
):
    def history(
        self,
        *,
        run_row_id: int,
        as_of: datetime | None = None,
    ) -> list[BacktestExecutionStressTestResultRecord]:
        stmt: Select[tuple[BacktestExecutionStressTestResultRecord]] = select(
            BacktestExecutionStressTestResultRecord
        ).where(BacktestExecutionStressTestResultRecord.run_row_id == run_row_id)
        if as_of is not None:
            stmt = stmt.where(BacktestExecutionStressTestResultRecord.event_timestamp <= as_of)
        stmt = stmt.order_by(BacktestExecutionStressTestResultRecord.event_timestamp.asc())
        return list(self.session.execute(stmt).scalars())
