"""Persistence services for strategy-validation runs."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256

from backend.database.dtos import (
    ValidationCandidateResultDTO,
    ValidationFoldDTO,
    ValidationRunDTO,
)
from backend.database.models import ValidationCandidateResult, ValidationFold, ValidationRun
from backend.database.session import DatabaseSessionManager


class ValidationMutationError(RuntimeError):
    """Raised when validation persistence invariants are violated."""


class StrategyValidationPersistenceService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_run(
        self,
        run: ValidationRunDTO,
        candidate_results: list[ValidationCandidateResultDTO],
        folds: list[ValidationFoldDTO],
    ) -> int:
        with self.session_manager.session_scope() as session:
            run_row = ValidationRun(
                run_id=run.run_id,
                strategy_name=run.strategy_name,
                candidate_ordering=list(run.candidate_ordering),
                validation_configuration=dict(run.validation_configuration),
                cpcv_definition=dict(run.cpcv_definition),
                comparison_json=dict(run.comparison_json),
                checksums=dict(run.checksums),
                warnings=list(run.warnings),
                failures=list(run.failures),
                software_git_commit=run.software_git_commit,
                schema_version=run.schema_version,
                random_seed=run.random_seed,
                metadata_json=dict(run.metadata),
                created_at=run.created_at,
            )
            session.add(run_row)
            session.flush()

            session.add_all(
                [
                    ValidationCandidateResult(
                        run_row_id=run_row.id,
                        candidate_id=item.candidate_id,
                        tier=item.tier,
                        parameters=dict(item.parameters),
                        deflated_sharpe=dict(item.deflated_sharpe),
                        pbo=dict(item.pbo),
                        cpcv=dict(item.cpcv),
                        sensitivity=dict(item.sensitivity),
                        neighborhood=dict(item.neighborhood),
                        degradation=dict(item.degradation),
                        regime_robustness=dict(item.regime_robustness),
                        temporal_stability=dict(item.temporal_stability),
                        stress_test=dict(item.stress_test),
                        bootstrap=dict(item.bootstrap),
                        robustness_score=dict(item.robustness_score),
                        gate_result=dict(item.gate_result),
                        warnings=list(item.warnings),
                        failures=list(item.failures),
                        reproducibility_metadata=dict(item.reproducibility_metadata),
                    )
                    for item in candidate_results
                ]
            )
            session.add_all(
                [
                    ValidationFold(
                        run_row_id=run_row.id,
                        split_id=item.split_id,
                        fold_index=item.fold_index,
                        split_json=dict(item.split_json),
                        selection_json=dict(item.selection_json),
                        result_json=dict(item.result_json),
                        warnings=list(item.warnings),
                    )
                    for item in folds
                ]
            )
            session.flush()
            return run_row.id

    def store_validation_run(
        self,
        run: ValidationRunDTO,
        candidate_results: list[ValidationCandidateResultDTO],
        folds: list[ValidationFoldDTO],
    ) -> int:
        run_payload = asdict(run)
        required_run_keys = {"validation_configuration", "cpcv_definition", "checksums"}
        missing = sorted(key for key in required_run_keys if not run_payload.get(key))
        if missing:
            raise ValidationMutationError(
                f"validation run is missing persistence metadata: missing={missing}"
            )
        return self.store_run(run, candidate_results, folds)


def deterministic_validation_checksum(
    *,
    run: ValidationRunDTO,
    candidate_results: list[ValidationCandidateResultDTO],
    folds: list[ValidationFoldDTO],
) -> str:
    normalized = {
        "run_id": run.run_id,
        "strategy_name": run.strategy_name,
        "candidate_ordering": tuple(run.candidate_ordering),
        "checksums": dict(sorted(run.checksums.items())),
        "candidate_results": sorted(
            (
                item.candidate_id,
                item.tier,
                tuple(sorted(item.robustness_score.items())),
            )
            for item in candidate_results
        ),
        "folds": sorted((item.split_id, item.fold_index) for item in folds),
    }
    return sha256(repr(normalized).encode("utf-8")).hexdigest()
