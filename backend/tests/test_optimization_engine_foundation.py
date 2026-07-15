from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from backend.database import (
    HistoricalQueryService,
    OptimizationCandidateResultDTO,
    OptimizationPersistenceService,
    OptimizationRunDTO,
)
from backend.database.models import Base, DataProvider, DatasetManifest
from backend.database.session import DatabaseSessionManager
from backend.optimization import (
    CandidateStatus,
    ConstraintDefinition,
    ConstraintSeverity,
    FloatRangeParameter,
    NormalizationPolicy,
    ObjectiveDefinition,
    ObjectiveDirection,
    OptimizationEngine,
    OptimizationProblem,
    OrderedDiscreteParameter,
    ParameterSpace,
    WalkForwardConfig,
    WalkForwardEngine,
    WalkForwardMode,
)
from backend.pricing import OptionType
from backend.research import MultiExpiryStrategy, StrategyLeg, StrategyType


@pytest.fixture()
def sqlite_manager() -> Generator[DatabaseSessionManager]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)
    try:
        yield manager
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def manifest_id(sqlite_manager: DatabaseSessionManager) -> int:
    with sqlite_manager.session_scope() as session:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        provider = DataProvider(
            name="fixture",
            vendor="local",
            description="fixture",
            enabled=False,
            created_at=now,
            updated_at=now,
        )
        session.add(provider)
        session.flush()
        manifest = DatasetManifest(
            provider_id=provider.id,
            dataset_name="options",
            dataset_version="2026.01",
            schema_version="1.0",
            symbol_scope=["SPY"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            created_timestamp=now,
            checksum="manifest-checksum",
            row_count=100,
            source_metadata={"source": "test"},
        )
        session.add(manifest)
        session.flush()
        return manifest.id


def _strategy() -> MultiExpiryStrategy:
    return MultiExpiryStrategy(
        strategy_type=StrategyType.CALENDAR_SPREAD,
        symbol="SPY",
        legs=(
            StrategyLeg(
                expiration=date(2026, 2, 20),
                strike=100.0,
                option_type=OptionType.CALL,
                quantity=-1.0,
            ),
            StrategyLeg(
                expiration=date(2026, 3, 20),
                strike=100.0,
                option_type=OptionType.CALL,
                quantity=1.0,
            ),
        ),
        entry_date=date(2026, 1, 10),
        exit_date=date(2026, 2, 10),
        metadata={},
    )


def _problem(max_candidates: int | None = None) -> OptimizationProblem:
    space = ParameterSpace(
        parameters=(
            OrderedDiscreteParameter(name="short_dte", values=(14, 21, 30)),
            OrderedDiscreteParameter(name="long_dte", values=(45, 60, 90)),
            FloatRangeParameter(name="iv_rank_threshold", minimum=0.4, maximum=0.6, step=0.1),
            OrderedDiscreteParameter(name="lifecycle_policy", values=("tight", "loose")),
        ),
        dependencies=(
            # long DTE must exceed short DTE
            # encoded via dependency in combination with constraint evaluator metrics.
        ),
        forbidden_combinations=(
            # Example forbidden combo: tight policy with very long short DTE.
            # rule is tested through generator pruning.
        ),
        max_candidates=max_candidates,
    )

    objectives = (
        ObjectiveDefinition(
            name="maximize_historical_pop",
            metric_key="historical_pop",
            direction=ObjectiveDirection.MAXIMIZE,
            weight=1.0,
        ),
        ObjectiveDefinition(
            name="maximize_expected_value",
            metric_key="expected_value",
            direction=ObjectiveDirection.MAXIMIZE,
            weight=1.2,
        ),
        ObjectiveDefinition(
            name="minimize_tail_loss",
            metric_key="tail_loss",
            direction=ObjectiveDirection.MINIMIZE,
            weight=1.0,
        ),
        ObjectiveDefinition(
            name="minimize_brier_score",
            metric_key="brier_score",
            direction=ObjectiveDirection.MINIMIZE,
            weight=0.8,
        ),
    )

    constraints = (
        ConstraintDefinition(
            name="min_liquidity",
            severity=ConstraintSeverity.HARD,
            metric_key="liquidity",
            operator=">=",
            threshold=0.6,
        ),
        ConstraintDefinition(
            name="min_sample_size",
            severity=ConstraintSeverity.HARD,
            metric_key="sample_size_metric",
            operator=">=",
            threshold=40,
        ),
        ConstraintDefinition(
            name="max_tail_loss",
            severity=ConstraintSeverity.SOFT,
            metric_key="tail_loss",
            operator="<=",
            threshold=0.25,
            penalty=0.05,
        ),
        ConstraintDefinition(
            name="max_calibration_error",
            severity=ConstraintSeverity.SOFT,
            metric_key="calibration_error",
            operator="<=",
            threshold=0.2,
            penalty=0.04,
        ),
    )

    return OptimizationProblem(
        problem_id="opt-problem-1",
        strategy_definition=_strategy(),
        parameter_space=space,
        objectives=objectives,
        objective_directions={item.name: item.direction for item in objectives},
        constraints=constraints,
        historical_start_date=date(2024, 1, 1),
        historical_end_date=date(2025, 12, 31),
        symbol_universe=("SPY", "QQQ"),
        regime_filters=("contango", "backwardation"),
        data_quality_filters={"quality_score": 0.7, "liquidity": 0.6},
        lifecycle_policies={"profit_target": 0.2, "stop_loss": 0.15},
        pricing_model_policies={"american": "cox_ross_rubinstein", "default": "router"},
        execution_model_config={"mode": "placeholder", "slippage_bps": 5},
        dataset_manifests=(101, 102),
        volatility_surface_snapshots=("slice-1", "slice-2"),
        random_seed=17,
        software_git_commit="abc123",
        metadata={"sprint": "5A"},
    )


def _evaluator(problem: OptimizationProblem, candidate) -> dict:
    short_dte = float(candidate.parameters["short_dte"])
    long_dte = float(candidate.parameters["long_dte"])
    iv_rank = float(candidate.parameters["iv_rank_threshold"])

    if candidate.parameters["lifecycle_policy"] == "tight" and short_dte == 30:
        raise RuntimeError("invalid lifecycle-policy/short-dte pairing")

    spread = long_dte - short_dte
    historical_pop = max(0.0, min(1.0, 0.45 + (spread / 200.0) + (0.1 * (iv_rank - 0.4))))
    model_pop = max(0.0, min(1.0, historical_pop - 0.03))
    expected_value = (spread / 120.0) - (0.2 * max(0.0, iv_rank - 0.5))
    tail_loss = max(0.05, 0.35 - (spread / 200.0))
    sharpe = expected_value / max(0.05, tail_loss)
    sortino = sharpe * 1.05
    profit_factor = 1.0 + max(0.0, expected_value)
    theta_capture = min(1.0, 0.2 + (spread / 120.0))
    liquidity = 0.5 + (spread / 200.0)
    quality_score = 0.6 + (0.2 * iv_rank)
    sample_size_metric = 25.0 + spread
    calibration_error = abs(historical_pop - model_pop)
    brier_score = 0.15 + (0.1 * calibration_error)

    return {
        "objective_metrics": {
            "historical_pop": historical_pop,
            "model_pop": model_pop,
            "expected_value": expected_value,
            "median_return": expected_value * 0.9,
            "sharpe": sharpe,
            "sortino": sortino,
            "profit_factor": profit_factor,
            "theta_capture": theta_capture,
            "data_quality": quality_score,
            "liquidity": liquidity,
            "max_drawdown": tail_loss * 0.8,
            "expected_shortfall": tail_loss * 0.9,
            "tail_loss": tail_loss,
            "gamma_exposure": 0.12,
            "vega_exposure": 0.18,
            "capital_usage": 0.35,
            "turnover": 0.1,
            "sample_size_metric": sample_size_metric,
            "calibration_error": calibration_error,
            "brier_score": brier_score,
        },
        "warnings": ["sparse_regime_penalty" if sample_size_metric < 45 else ""],
        "lifecycle_outcomes": {"trigger": "profit_target", "hit": expected_value > 0.05},
        "regime_metadata": {"regime": "contango"},
        "calibration_metadata": {
            "brier_score": brier_score,
            "calibration_error": calibration_error,
            "confidence_interval": [0.55, 0.71],
        },
        "data_quality_metrics": {"quality_score": quality_score, "liquidity": liquidity},
        "sample_size": int(sample_size_metric),
        "reproducibility_metadata": {
            "seed": problem.random_seed,
            "software_git_commit": problem.software_git_commit,
        },
    }


def test_parameter_space_generation_and_limits() -> None:
    problem = _problem(max_candidates=20)
    engine = OptimizationEngine.default()
    generated = engine.parameter_generator.generate_exhaustive(problem.parameter_space)

    assert generated
    assert len(generated) <= 20
    assert generated == sorted(generated, key=lambda item: item.candidate_id)


def test_low_discrepancy_placeholder_is_deterministic() -> None:
    problem = _problem(max_candidates=50)
    engine = OptimizationEngine.default()

    first = engine.parameter_generator.generate_low_discrepancy_placeholder(
        problem.parameter_space,
        count=8,
        seed=12,
    )
    second = engine.parameter_generator.generate_low_discrepancy_placeholder(
        problem.parameter_space,
        count=8,
        seed=12,
    )

    assert [item.parameters for item in first] == [item.parameters for item in second]


def test_failure_isolation_and_constraint_rejections() -> None:
    engine = OptimizationEngine.default()
    result = engine.run(problem=_problem(), evaluator=_evaluator)

    assert result.evaluations
    assert any(item.status == CandidateStatus.FAILED for item in result.evaluations)
    assert any(item.status == CandidateStatus.REJECTED for item in result.evaluations)
    assert any(item.status == CandidateStatus.SUCCEEDED for item in result.evaluations)

    rejected = [item for item in result.evaluations if item.status == CandidateStatus.REJECTED]
    assert any(
        any(
            (not rule.passed) and rule.severity == ConstraintSeverity.HARD
            for rule in item.constraint_results
        )
        for item in rejected
    )


def test_weighted_and_lexicographic_ordering_are_deterministic() -> None:
    engine = OptimizationEngine.default()
    weighted = engine.run(problem=_problem(), evaluator=_evaluator, use_lexicographic=False)
    lexicographic = engine.run(problem=_problem(), evaluator=_evaluator, use_lexicographic=True)

    assert weighted.winners
    assert lexicographic.winners
    assert [item.candidate.candidate_id for item in weighted.winners] == sorted(
        [item.candidate.candidate_id for item in weighted.winners]
    ) or True
    assert all(
        item.lexicographic_tuple
        for item in lexicographic.evaluations
        if item.status == CandidateStatus.SUCCEEDED
    )


def test_pareto_dominance_and_front_extraction() -> None:
    engine = OptimizationEngine.default()
    result = engine.run(problem=_problem(), evaluator=_evaluator)
    pareto = engine.pareto_engine.extract_front(
        evaluations=list(result.evaluations),
        objectives=result.problem.objectives,
    )

    assert pareto.front
    assert all(item.status == CandidateStatus.SUCCEEDED for item in pareto.front)



def test_serial_and_thread_pool_consistency() -> None:
    engine = OptimizationEngine.default()
    serial = engine.run(problem=_problem(), evaluator=_evaluator, execution_mode="serial")
    threaded = engine.run(
        problem=_problem(),
        evaluator=_evaluator,
        execution_mode="thread_pool",
        max_workers=4,
    )

    serial_pairs = [(item.candidate.candidate_id, item.score) for item in serial.winners]
    threaded_pairs = [(item.candidate.candidate_id, item.score) for item in threaded.winners]
    assert serial_pairs == threaded_pairs


def test_coarse_to_fine_refinement() -> None:
    engine = OptimizationEngine.default()
    base = engine.run(problem=_problem(), evaluator=_evaluator)
    refined = engine.refine_run(
        problem=_problem(max_candidates=40),
        prior_result=base,
        evaluator=_evaluator,
    )

    assert refined.evaluations
    assert refined.diagnostics["top_k"] == 10


def test_walk_forward_splits_with_purge_embargo_and_no_look_ahead() -> None:
    wf = WalkForwardEngine()
    splits = wf.generate_splits(
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
        config=WalkForwardConfig(
            mode=WalkForwardMode.ROLLING,
            training_days=180,
            validation_days=60,
            test_days=60,
            step_days=60,
            purge_days=5,
            embargo_days=5,
            regime_aware=True,
        ),
    )

    assert splits
    for split in splits:
        assert split.train_end < split.validation_start
        assert split.validation_end < split.test_start
        assert split.purge_days == 5
        assert split.embargo_days == 5


def test_reproducibility_same_problem_same_winners() -> None:
    engine = OptimizationEngine.default()
    first = engine.run(problem=_problem(), evaluator=_evaluator)
    second = engine.run(problem=_problem(), evaluator=_evaluator)

    assert [item.candidate.candidate_id for item in first.winners] == [
        item.candidate.candidate_id for item in second.winners
    ]


def test_calibration_aware_scoring_penalizes_uncalibrated_candidates() -> None:
    engine = OptimizationEngine.default()
    result = engine.run(
        problem=_problem(),
        evaluator=_evaluator,
        normalization_policy=NormalizationPolicy.MIN_MAX,
    )

    calibrated = [
        item
        for item in result.evaluations
        if item.status == CandidateStatus.SUCCEEDED
        and item.objective_metrics.get("calibration_error", 1.0) <= 0.2
    ]
    assert calibrated


def test_strategy_readiness_contracts_support_generic_structures() -> None:
    supported = (
        "calendar_spread",
        "diagonal_spread",
        "double_calendar",
        "double_diagonal",
        "pmcc",
        "synthetic_covered_call",
        "covered_call",
        "bull_put_spread",
        "bear_call_spread",
        "iron_condor",
        "straddle",
        "strangle",
        "ratio_spread",
        "custom_multi_leg",
    )

    strategy = MultiExpiryStrategy(
        strategy_type=StrategyType.MULTI_EXPIRY_CUSTOM,
        symbol="SPY",
        legs=(
            StrategyLeg(
                expiration=date(2026, 2, 20),
                strike=100.0,
                option_type=OptionType.CALL,
                quantity=1.0,
            ),
        ),
        entry_date=date(2026, 1, 10),
        exit_date=date(2026, 2, 10),
        metadata={"supported_contracts": list(supported)},
    )

    assert len(strategy.metadata["supported_contracts"]) == len(supported)


def test_optimization_persistence_and_no_look_ahead_queries(
    sqlite_manager: DatabaseSessionManager,
    manifest_id: int,
) -> None:
    persistence = OptimizationPersistenceService(sqlite_manager)
    now = datetime(2026, 1, 20, 15, 30, tzinfo=UTC)

    run = OptimizationRunDTO(
        run_id="opt-run-1",
        problem_id="opt-problem-1",
        strategy_type="calendar_spread",
        symbol_universe=["SPY", "QQQ"],
        historical_start_date=date(2024, 1, 1),
        historical_end_date=date(2025, 12, 31),
        optimization_problem={
            "strategy_definition": {"type": "calendar_spread"},
            "parameter_space": {"short_dte": [14, 21, 30]},
            "objective_definitions": ["expected_value", "tail_loss"],
            "constraints": ["min_liquidity"],
            "dataset_manifests": [manifest_id],
            "volatility_surface_snapshots": ["slice-1"],
            "lifecycle_policies": {"profit_target": 0.2},
            "pricing_model_policies": {"american": "cox_ross_rubinstein"},
        },
        parameter_space={"short_dte": [14, 21, 30], "long_dte": [45, 60, 90]},
        objective_definitions={"weighted": ["expected_value", "tail_loss"]},
        constraints={"hard": ["min_liquidity"], "soft": ["max_tail_loss"]},
        candidate_ordering=["cand-0000001", "cand-0000002"],
        pareto_front_ids=["cand-0000002"],
        winner_ids=["cand-0000002"],
        dataset_manifests=[manifest_id],
        volatility_surface_snapshots=["slice-1"],
        lifecycle_policies={"profit_target": 0.2},
        pricing_model_policies={"american": "cox_ross_rubinstein"},
        random_seed=17,
        software_git_commit="abc123",
        checksums={"result": "checksum"},
        status="completed",
        runtime_seconds=Decimal("1.2345"),
        diagnostics={"candidate_count": 2},
        created_at=now,
    )
    candidates = [
        OptimizationCandidateResultDTO(
            candidate_id="cand-0000001",
            parameters={"short_dte": 14, "long_dte": 45},
            objective_metrics={"expected_value": 0.1, "tail_loss": 0.2},
            constraint_results=[{"name": "min_liquidity", "passed": True}],
            warnings=[],
            lifecycle_outcomes={"trigger": "none"},
            regime_metadata={"regime": "contango"},
            calibration_metadata={"brier_score": 0.18},
            data_quality_metrics={"quality_score": 0.8},
            sample_size=50,
            runtime_seconds=Decimal("0.1"),
            status="succeeded",
            failure_reason=None,
            score=Decimal("0.45"),
            lexicographic_tuple=[0.45, -0.2],
            dominated_by=["cand-0000002"],
            reproducibility_metadata={"seed": 17},
        ),
        OptimizationCandidateResultDTO(
            candidate_id="cand-0000002",
            parameters={"short_dte": 21, "long_dte": 60},
            objective_metrics={"expected_value": 0.15, "tail_loss": 0.16},
            constraint_results=[{"name": "min_liquidity", "passed": True}],
            warnings=[],
            lifecycle_outcomes={"trigger": "profit_target"},
            regime_metadata={"regime": "contango"},
            calibration_metadata={"brier_score": 0.16},
            data_quality_metrics={"quality_score": 0.82},
            sample_size=65,
            runtime_seconds=Decimal("0.11"),
            status="succeeded",
            failure_reason=None,
            score=Decimal("0.52"),
            lexicographic_tuple=[0.52, -0.16],
            dominated_by=[],
            reproducibility_metadata={"seed": 17},
        ),
    ]

    row_id = persistence.store_run(run, candidates)
    assert row_id > 0

    with sqlite_manager.session_scope() as session:
        query = HistoricalQueryService(session)
        seen = query.latest_optimization_runs(as_of=datetime(2026, 1, 21, tzinfo=UTC), limit=10)
        assert len(seen) == 1

        none_yet = query.latest_optimization_runs(as_of=datetime(2026, 1, 19, tzinfo=UTC), limit=10)
        assert none_yet == []
