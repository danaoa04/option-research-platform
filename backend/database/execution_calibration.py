"""Persistence and query services for Sprint 7C execution calibration data."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256

from sqlalchemy import select

from backend.database.backtesting import BacktestMutationError
from backend.database.dtos import (
    BacktestExecutionBrokerPolicyVersionDTO,
    BacktestExecutionCalibrationChecksumDTO,
    BacktestExecutionCalibrationDatasetDTO,
    BacktestExecutionCalibrationDriftDTO,
    BacktestExecutionFillQualityObservationDTO,
    BacktestExecutionPartialFillModelDTO,
    BacktestExecutionPolicyComparisonDTO,
    BacktestExecutionQualityScoreDTO,
    BacktestExecutionRealVsSimulatedDTO,
    BacktestExecutionSlippageModelDTO,
    BacktestExecutionSpreadCaptureModelDTO,
    BacktestExecutionStressTestResultDTO,
    BacktestExecutionTransactionCostPolicyDTO,
    BacktestExecutionValidationRunDTO,
)
from backend.database.models import (
    BacktestExecutionBrokerPolicyVersionRecord,
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
    BacktestExecutionValidationRunRecord,
)
from backend.database.repositories.backtesting import BacktestRunRepository
from backend.database.repositories.execution_calibration import (
    BacktestExecutionBrokerPolicyVersionRepository,
    BacktestExecutionCalibrationChecksumRepository,
    BacktestExecutionCalibrationDatasetRepository,
    BacktestExecutionCalibrationDriftRepository,
    BacktestExecutionFillQualityObservationRepository,
    BacktestExecutionFillQualityQueryRepository,
    BacktestExecutionPartialFillModelRepository,
    BacktestExecutionPolicyComparisonRepository,
    BacktestExecutionQualityScoreRepository,
    BacktestExecutionRealVsSimulatedRepository,
    BacktestExecutionSlippageModelRepository,
    BacktestExecutionSpreadCaptureModelRepository,
    BacktestExecutionStressTestQueryRepository,
    BacktestExecutionStressTestResultRepository,
    BacktestExecutionTransactionCostPolicyRepository,
    BacktestExecutionValidationRunRepository,
)
from backend.database.session import DatabaseSessionManager


class BacktestExecutionCalibrationPersistenceService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_run_state(
        self,
        *,
        run_id: str,
        calibration_datasets: list[BacktestExecutionCalibrationDatasetDTO],
        fill_quality_observations: list[BacktestExecutionFillQualityObservationDTO],
        slippage_models: list[BacktestExecutionSlippageModelDTO],
        spread_capture_models: list[BacktestExecutionSpreadCaptureModelDTO],
        partial_fill_models: list[BacktestExecutionPartialFillModelDTO],
        transaction_cost_policies: list[BacktestExecutionTransactionCostPolicyDTO],
        broker_policy_versions: list[BacktestExecutionBrokerPolicyVersionDTO],
        policy_comparisons: list[BacktestExecutionPolicyComparisonDTO],
        execution_quality_scores: list[BacktestExecutionQualityScoreDTO],
        real_vs_simulated: list[BacktestExecutionRealVsSimulatedDTO],
        validation_runs: list[BacktestExecutionValidationRunDTO],
        calibration_drift: list[BacktestExecutionCalibrationDriftDTO],
        stress_test_results: list[BacktestExecutionStressTestResultDTO],
        reproducibility_checksums: list[BacktestExecutionCalibrationChecksumDTO],
    ) -> int:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                raise BacktestMutationError(
                    f"backtest run not found for execution calibration state: {run_id}"
                )
            run_row_id = run_row.id

            BacktestExecutionCalibrationDatasetRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{k: v for k, v in asdict(item).items() if k != "metadata_json"},
                        "metadata": item.metadata_json,
                    }
                    for item in calibration_datasets
                ]
            )
            BacktestExecutionFillQualityObservationRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{k: v for k, v in asdict(item).items() if k != "metadata_json"},
                        "metadata": item.metadata_json,
                    }
                    for item in fill_quality_observations
                ]
            )
            BacktestExecutionSlippageModelRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in slippage_models]
            )
            BacktestExecutionSpreadCaptureModelRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in spread_capture_models]
            )
            BacktestExecutionPartialFillModelRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in partial_fill_models]
            )
            BacktestExecutionTransactionCostPolicyRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{k: v for k, v in asdict(item).items() if k != "metadata_json"},
                        "metadata": item.metadata_json,
                    }
                    for item in transaction_cost_policies
                ]
            )
            BacktestExecutionBrokerPolicyVersionRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in broker_policy_versions]
            )
            BacktestExecutionPolicyComparisonRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in policy_comparisons]
            )
            BacktestExecutionQualityScoreRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in execution_quality_scores]
            )
            BacktestExecutionRealVsSimulatedRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in real_vs_simulated]
            )
            BacktestExecutionValidationRunRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in validation_runs]
            )
            BacktestExecutionCalibrationDriftRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in calibration_drift]
            )
            BacktestExecutionStressTestResultRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in stress_test_results]
            )
            BacktestExecutionCalibrationChecksumRepository(session).upsert_rows(
                [
                    {
                        "run_row_id": run_row_id,
                        **{k: v for k, v in asdict(item).items() if k != "metadata_json"},
                        "metadata": item.metadata_json,
                    }
                    for item in reproducibility_checksums
                ]
            )
            return run_row_id


class BacktestExecutionCalibrationQueryService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def fill_quality_history(
        self,
        *,
        run_id: str,
        symbol: str | None = None,
        strategy_family: str | None = None,
    ) -> Sequence[BacktestExecutionFillQualityObservationRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            return BacktestExecutionFillQualityQueryRepository(session).history(
                run_row_id=run_row.id,
                symbol=symbol,
                strategy_family=strategy_family,
            )

    def calibration_summary(
        self,
        *,
        run_id: str,
    ) -> Sequence[BacktestExecutionCalibrationDatasetRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            stmt = (
                select(BacktestExecutionCalibrationDatasetRecord)
                .where(BacktestExecutionCalibrationDatasetRecord.run_row_id == run_row.id)
                .order_by(BacktestExecutionCalibrationDatasetRecord.created_at.asc())
            )
            return list(session.execute(stmt).scalars())

    def slippage_parameters(
        self,
        *,
        run_id: str,
    ) -> Sequence[BacktestExecutionSlippageModelRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            stmt = (
                select(BacktestExecutionSlippageModelRecord)
                .where(BacktestExecutionSlippageModelRecord.run_row_id == run_row.id)
                .order_by(BacktestExecutionSlippageModelRecord.calibrated_at.asc())
            )
            return list(session.execute(stmt).scalars())

    def spread_capture_parameters(
        self,
        *,
        run_id: str,
    ) -> Sequence[BacktestExecutionSpreadCaptureModelRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            stmt = (
                select(BacktestExecutionSpreadCaptureModelRecord)
                .where(BacktestExecutionSpreadCaptureModelRecord.run_row_id == run_row.id)
                .order_by(BacktestExecutionSpreadCaptureModelRecord.calibrated_at.asc())
            )
            return list(session.execute(stmt).scalars())

    def partial_fill_parameters(
        self,
        *,
        run_id: str,
    ) -> Sequence[BacktestExecutionPartialFillModelRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            stmt = (
                select(BacktestExecutionPartialFillModelRecord)
                .where(BacktestExecutionPartialFillModelRecord.run_row_id == run_row.id)
                .order_by(BacktestExecutionPartialFillModelRecord.calibrated_at.asc())
            )
            return list(session.execute(stmt).scalars())

    def broker_policy_versions(
        self,
        *,
        run_id: str,
    ) -> Sequence[BacktestExecutionBrokerPolicyVersionRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            stmt = (
                select(BacktestExecutionBrokerPolicyVersionRecord)
                .where(BacktestExecutionBrokerPolicyVersionRecord.run_row_id == run_row.id)
                .order_by(
                    BacktestExecutionBrokerPolicyVersionRecord.policy_name.asc(),
                    BacktestExecutionBrokerPolicyVersionRecord.policy_version.asc(),
                )
            )
            return list(session.execute(stmt).scalars())

    def policy_comparisons(
        self,
        *,
        run_id: str,
    ) -> Sequence[BacktestExecutionPolicyComparisonRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            stmt = (
                select(BacktestExecutionPolicyComparisonRecord)
                .where(BacktestExecutionPolicyComparisonRecord.run_row_id == run_row.id)
                .order_by(BacktestExecutionPolicyComparisonRecord.event_timestamp.asc())
            )
            return list(session.execute(stmt).scalars())

    def execution_quality_history(
        self,
        *,
        run_id: str,
        symbol: str | None = None,
    ) -> Sequence[BacktestExecutionQualityScoreRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            return BacktestExecutionQualityScoreRepository(session).history(
                run_row_id=run_row.id,
                symbol=symbol,
            )

    def real_vs_simulated_comparisons(
        self,
        *,
        run_id: str,
    ) -> Sequence[BacktestExecutionRealVsSimulatedRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            stmt = (
                select(BacktestExecutionRealVsSimulatedRecord)
                .where(BacktestExecutionRealVsSimulatedRecord.run_row_id == run_row.id)
                .order_by(BacktestExecutionRealVsSimulatedRecord.event_timestamp.asc())
            )
            return list(session.execute(stmt).scalars())

    def validation_runs(
        self,
        *,
        run_id: str,
    ) -> Sequence[BacktestExecutionValidationRunRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            stmt = (
                select(BacktestExecutionValidationRunRecord)
                .where(BacktestExecutionValidationRunRecord.run_row_id == run_row.id)
                .order_by(BacktestExecutionValidationRunRecord.created_at.asc())
            )
            return list(session.execute(stmt).scalars())

    def calibration_drift(
        self,
        *,
        run_id: str,
    ) -> Sequence[BacktestExecutionCalibrationDriftRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            stmt = (
                select(BacktestExecutionCalibrationDriftRecord)
                .where(BacktestExecutionCalibrationDriftRecord.run_row_id == run_row.id)
                .order_by(BacktestExecutionCalibrationDriftRecord.event_timestamp.asc())
            )
            return list(session.execute(stmt).scalars())

    def execution_stress_tests(
        self,
        *,
        run_id: str,
        as_of: datetime | None = None,
    ) -> Sequence[BacktestExecutionStressTestResultRecord]:
        with self.session_manager.session_scope() as session:
            run_row = BacktestRunRepository(session).get_run(run_id)
            if run_row is None:
                return []
            return BacktestExecutionStressTestQueryRepository(session).history(
                run_row_id=run_row.id,
                as_of=as_of,
            )


def deterministic_execution_calibration_checksum(
    *,
    run_id: str,
    datasets: list[BacktestExecutionCalibrationDatasetDTO],
    slippage_models: list[BacktestExecutionSlippageModelDTO],
) -> str:
    payload = {
        "run_id": run_id,
        "datasets": [
            {
                "dataset_id": item.dataset_id,
                "source_type": item.source_type,
                "provider_manifest": item.provider_manifest,
                "broker_policy_version": item.broker_policy_version,
                "sample_count": item.sample_count,
            }
            for item in sorted(datasets, key=lambda row: row.dataset_id)
        ],
        "slippage_models": [
            {
                "model_id": item.model_id,
                "dataset_id": item.dataset_id,
                "model_name": item.model_name,
                "sample_size": item.sample_size,
                "validity_status": item.validity_status,
            }
            for item in sorted(
                slippage_models,
                key=lambda row: (row.dataset_id, row.model_id),
            )
        ],
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()
