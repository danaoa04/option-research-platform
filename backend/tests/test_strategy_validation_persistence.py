from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import create_engine, select

from backend.database import (
    StrategyValidationPersistenceService,
    ValidationCandidateResultDTO,
    ValidationFoldDTO,
    ValidationRunDTO,
    deterministic_validation_checksum,
)
from backend.database.models import Base, ValidationCandidateResult, ValidationFold, ValidationRun
from backend.database.session import DatabaseSessionManager


@pytest.fixture()
def sqlite_manager():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)
    try:
        yield manager
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()



def _sample_run() -> ValidationRunDTO:
    created_at = datetime(2026, 1, 12, 15, 30, tzinfo=UTC)
    return ValidationRunDTO(
        run_id="validation-run-1",
        strategy_name="mean_reversion",
        candidate_ordering=["candidate-b", "candidate-a"],
        validation_configuration={"cpcv_folds": 3},
        cpcv_definition={"embargo": 2},
        comparison_json={"winner": "candidate-a"},
        checksums={"inputs": "abc123"},
        warnings=["review neighborhood coverage"],
        failures=[],
        software_git_commit="deadbeef",
        schema_version="1.0",
        random_seed=7,
        metadata={"source": "fixture"},
        created_at=created_at,
    )



def _sample_candidate_results() -> list[ValidationCandidateResultDTO]:
    base_payload: dict[str, Any] = {
        "deflated_sharpe": {"value": 1.5},
        "pbo": {"probability": 0.1},
        "cpcv": {"median": 0.7},
        "sensitivity": {"slope": 0.05},
        "neighborhood": {"radius": 2},
        "degradation": {"drop": 0.03},
        "regime_robustness": {"score": 0.8},
        "temporal_stability": {"trend": 0.02},
        "stress_test": {"worst_case": -0.12},
        "bootstrap": {"median": 0.9},
        "robustness_score": {"score": 0.77},
        "gate_result": {"passed": True},
        "warnings": [],
        "failures": [],
        "reproducibility_metadata": {"seed": 11},
    }
    return [
        ValidationCandidateResultDTO(
            candidate_id="candidate-a",
            tier="promoted",
            parameters={"window": 5},
            **base_payload,
        ),
        ValidationCandidateResultDTO(
            candidate_id="candidate-b",
            tier="explore",
            parameters={"window": 10},
            **base_payload,
        ),
    ]



def _sample_folds() -> list[ValidationFoldDTO]:
    return [
        ValidationFoldDTO(
            run_id="validation-run-1",
            split_id="fold-1",
            fold_index=0,
            split_json={"train": [1, 2], "test": [3]},
            selection_json={"selected": ["candidate-a"]},
            result_json={"sharpe": 1.2},
            warnings=[],
        ),
        ValidationFoldDTO(
            run_id="validation-run-1",
            split_id="fold-2",
            fold_index=1,
            split_json={"train": [2, 3], "test": [4]},
            selection_json={"selected": ["candidate-b"]},
            result_json={"sharpe": 0.9},
            warnings=["low sample size"],
        ),
    ]



def test_strategy_validation_persistence_round_trip(
    sqlite_manager: DatabaseSessionManager,
) -> None:
    service = StrategyValidationPersistenceService(sqlite_manager)
    run = _sample_run()
    candidate_results = _sample_candidate_results()
    folds = _sample_folds()

    run_row_id = service.store_validation_run(run, candidate_results, folds)

    with sqlite_manager.session_scope() as session:
        stored_run = session.execute(select(ValidationRun)).scalars().one()
        stored_results = session.execute(select(ValidationCandidateResult)).scalars().all()
        stored_folds = session.execute(select(ValidationFold)).scalars().all()

    assert run_row_id == stored_run.id
    assert stored_run.run_id == run.run_id
    assert stored_run.strategy_name == run.strategy_name
    assert [result.candidate_id for result in stored_results] == ["candidate-a", "candidate-b"]
    assert [fold.split_id for fold in stored_folds] == ["fold-1", "fold-2"]
    assert stored_results[0].robustness_score == {"score": 0.77}
    assert stored_folds[1].warnings == ["low sample size"]



def test_validation_checksum_is_order_stable() -> None:
    run = _sample_run()
    candidate_results = _sample_candidate_results()
    folds = _sample_folds()

    checksum_a = deterministic_validation_checksum(
        run=run,
        candidate_results=candidate_results,
        folds=folds,
    )
    checksum_b = deterministic_validation_checksum(
        run=run,
        candidate_results=list(reversed(candidate_results)),
        folds=list(reversed(folds)),
    )

    assert checksum_a == checksum_b
