from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from backend.database import (
    HistoricalQueryService,
    ResearchOpportunityDTO,
    ResearchPersistenceService,
    ResearchRunDTO,
)
from backend.database.models import Base, DataProvider, DatasetManifest, Underlying
from backend.database.session import DatabaseSessionManager
from backend.pricing import (
    ExerciseStyle,
    OptionType,
    PricingEngine,
    PricingModelName,
    UnderlyingType,
)
from backend.research import (
    CalibrationError,
    DeterministicRefinementEngine,
    ExpectedValueEngine,
    HistoricalOutcomeRecord,
    HistoricalProbabilityEngine,
    LifecyclePolicyConfig,
    LifecyclePolicyEngine,
    ModelProbabilityEngine,
    ModelSimulationConfig,
    MultiExpiryStrategy,
    RankingCandidate,
    RegimeConditionedRankingEngine,
    ScoreCalibrationEngine,
    ScoredSweepCase,
    SparseSampleWarningError,
    StrategyLeg,
    StrategyStatePoint,
    StrategyType,
)
from backend.research.models import ParameterSweepCase, ParameterSweepGrid


def _sample_strategy() -> MultiExpiryStrategy:
    return MultiExpiryStrategy(
        strategy_type=StrategyType.CALENDAR_SPREAD,
        symbol="SPY",
        legs=(
            StrategyLeg(
                expiration=date(2026, 2, 20),
                strike=100.0,
                option_type=OptionType.CALL,
                quantity=-1.0,
                metadata={
                    "pricing_model": PricingModelName.BLACK_SCHOLES.value,
                    "exercise_style": ExerciseStyle.EUROPEAN.value,
                },
            ),
            StrategyLeg(
                expiration=date(2026, 3, 20),
                strike=100.0,
                option_type=OptionType.CALL,
                quantity=1.0,
                metadata={
                    "pricing_model": PricingModelName.COX_ROSS_RUBINSTEIN.value,
                    "exercise_style": ExerciseStyle.AMERICAN.value,
                    "underlying_type": UnderlyingType.ETF.value,
                    "tree_steps": 200,
                },
            ),
        ),
        entry_date=date(2026, 1, 10),
        exit_date=date(2026, 2, 10),
        metadata={"type": "research_only"},
    )


def test_historical_probability_outputs_are_labeled_and_confident() -> None:
    engine = HistoricalProbabilityEngine(min_sample_size=3)
    outcomes = [
        HistoricalOutcomeRecord(
            as_of=datetime(2026, 1, 10, tzinfo=UTC),
            manifest_id=1,
            regime_label="contango",
            quality_score=0.9,
            pnl=0.5,
            touched_target=True,
            breached_loss=False,
            expired_profitable=True,
            early_exit_profitable=True,
        ),
        HistoricalOutcomeRecord(
            as_of=datetime(2026, 1, 11, tzinfo=UTC),
            manifest_id=1,
            regime_label="contango",
            quality_score=0.8,
            pnl=-0.3,
            touched_target=False,
            breached_loss=True,
            expired_profitable=False,
            early_exit_profitable=False,
        ),
        HistoricalOutcomeRecord(
            as_of=datetime(2026, 1, 12, tzinfo=UTC),
            manifest_id=2,
            regime_label="backwardation",
            quality_score=0.85,
            pnl=0.2,
            touched_target=True,
            breached_loss=False,
            expired_profitable=True,
            early_exit_profitable=True,
        ),
    ]

    report = engine.evaluate(
        outcomes=outcomes,
        as_of=datetime(2026, 1, 12, tzinfo=UTC),
        regime_filters=("contango", "backwardation"),
        quality_floor=0.7,
    )

    assert report.probability_of_profit.probability_type == "historical_probability_of_profit"
    assert (
        report.target_profit_probability.probability_type
        == "historical_target_profit_probability"
    )
    assert report.probability_of_profit.sample_size == 3
    assert report.probability_of_profit.confidence_interval is not None


def test_sparse_sample_strict_mode_raises() -> None:
    engine = HistoricalProbabilityEngine(min_sample_size=10, strict_sparse_samples=True)
    outcomes = [
        HistoricalOutcomeRecord(
            as_of=datetime(2026, 1, 10, tzinfo=UTC),
            manifest_id=1,
            regime_label="contango",
            quality_score=0.8,
            pnl=0.1,
            touched_target=False,
            breached_loss=False,
            expired_profitable=True,
            early_exit_profitable=True,
        )
    ]

    with pytest.raises(SparseSampleWarningError):
        _ = engine.evaluate(
            outcomes=outcomes,
            as_of=datetime(2026, 1, 12, tzinfo=UTC),
        )


def test_model_probability_seeded_repeatability_and_labels() -> None:
    engine = ModelProbabilityEngine(pricing_engine=PricingEngine())
    strategy = _sample_strategy()
    config = ModelSimulationConfig(path_count=60, seed=42, horizon_days=20)

    a = engine.evaluate(strategy=strategy, config=config, as_of=date(2026, 1, 10))
    b = engine.evaluate(strategy=strategy, config=config, as_of=date(2026, 1, 10))

    assert a.probability_of_profit.probability_type == "model_probability_of_profit"
    assert a.target_profit_probability.probability_type == "model_target_profit_probability"
    assert a.loss_breach_probability.probability_type == "model_loss_threshold_breach_probability"
    assert a.probability_of_profit.probability == b.probability_of_profit.probability
    assert a.reproducibility["seed"] == 42


def test_model_probability_routes_per_leg_models_including_american() -> None:
    engine = ModelProbabilityEngine(pricing_engine=PricingEngine())
    strategy = _sample_strategy()
    report = engine.evaluate(
        strategy=strategy,
        config=ModelSimulationConfig(path_count=20, seed=7, horizon_days=10),
        as_of=date(2026, 1, 10),
    )

    used = {name for outcome in report.outcomes for name in outcome.selected_models}
    assert PricingModelName.BLACK_SCHOLES.value in used
    assert PricingModelName.COX_ROSS_RUBINSTEIN.value in used


def test_expected_value_engine_labels_historical_vs_model() -> None:
    comp = ExpectedValueEngine().compare(
        historical_pnls=[0.3, -0.1, 0.2, -0.2],
        model_pnls=[0.25, -0.05, 0.15, -0.1],
        capital_base=10.0,
    )

    assert comp.historical.label == "historical_expected_value"
    assert comp.model_estimated.label == "model_estimated_expected_value"
    assert comp.historical.tail_loss_percentile_95 <= comp.historical.median_pnl


def test_lifecycle_exit_triggers_capture_reason_and_timestamps() -> None:
    states = [
        StrategyStatePoint(
            timestamp=datetime(2026, 1, 1, 15, 30) + timedelta(days=i),
            implied_volatility=0.2 + (0.01 * i),
            realized_volatility=0.18,
            iv_percentile=0.5,
            iv_rank=0.5,
            theta=0.01,
            gamma=0.02,
            vega=0.1,
            charm=0.001,
            vanna=0.001,
            vomma=0.001,
            pnl=i * 0.2,
            intrinsic_value=0.0,
            extrinsic_value=1.0,
            metadata={
                "dte": 60 - i,
                "delta": 0.1 + (0.05 * i),
                "term_structure_normalized": i == 3,
            },
        )
        for i in range(5)
    ]

    result = LifecyclePolicyEngine().evaluate(
        states=states,
        policy=LifecyclePolicyConfig(profit_target=0.5, term_structure_normalized_exit=True),
    )

    assert result.exited is True
    assert result.events
    assert result.events[0].reason_code in {"profit_target", "term_structure_normalized"}


def test_regime_conditioned_ranking_is_explainable() -> None:
    ranking = RegimeConditionedRankingEngine(
        default_weights={"historical_pop": 1.0, "expected_value": 1.0, "drawdown": -1.0},
        regime_weights={"contango": {"expected_value": 2.0}},
    )
    results = ranking.rank(
        [
            RankingCandidate(
                candidate_id="A",
                regime="contango",
                metrics={
                    "historical_pop": 0.6,
                    "expected_value": 0.15,
                    "drawdown": 0.08,
                    "sample_reliability": 0.8,
                },
            ),
            RankingCandidate(
                candidate_id="B",
                regime="backwardation",
                metrics={
                    "historical_pop": 0.62,
                    "expected_value": 0.12,
                    "drawdown": 0.05,
                    "sample_reliability": 0.8,
                },
            ),
        ]
    )

    assert results[0].component_scores
    assert results[0].weights_used
    assert 0.0 <= results[0].confidence <= 1.0


def test_calibration_metrics_brier_and_buckets() -> None:
    diag = ScoreCalibrationEngine(min_bucket_samples=2).evaluate(
        predicted_probabilities=[0.1, 0.2, 0.8, 0.9, 0.6, 0.7],
        observed_successes=[False, False, True, True, True, False],
        bucket_count=3,
    )
    assert diag.brier_score >= 0.0
    assert diag.reliability_table
    assert diag.calibration_error >= 0.0


def test_calibration_invalid_lengths_raise() -> None:
    with pytest.raises(CalibrationError):
        _ = ScoreCalibrationEngine().evaluate(
            predicted_probabilities=[0.1, 0.2],
            observed_successes=[True],
        )


def test_refinement_coarse_to_fine_pareto_and_constraints() -> None:
    engine = DeterministicRefinementEngine()
    grid = ParameterSweepGrid(parameters={"front_dte": (14, 21, 30), "iv_rank": (0.4, 0.6, 0.8)})
    scored = [
        ScoredSweepCase(
            case=ParameterSweepCase(case_id="case-1", parameters={"front_dte": 14, "iv_rank": 0.4}),
            metrics={"expected_value": 0.10, "pop": 0.55, "drawdown": 0.12},
        ),
        ScoredSweepCase(
            case=ParameterSweepCase(case_id="case-2", parameters={"front_dte": 21, "iv_rank": 0.6}),
            metrics={"expected_value": 0.16, "pop": 0.60, "drawdown": 0.10},
        ),
        ScoredSweepCase(
            case=ParameterSweepCase(case_id="case-3", parameters={"front_dte": 30, "iv_rank": 0.8}),
            metrics={"expected_value": 0.14, "pop": 0.58, "drawdown": 0.08},
        ),
    ]

    refined = engine.coarse_to_fine(grid=grid, scored=scored, objective="expected_value")
    assert refined.parameters

    constrained = engine.constrained_filter(scored=scored, constraints={"drawdown": (None, 0.10)})
    assert len(constrained) == 2

    front = engine.pareto_front(
        scored=scored,
        objectives={"expected_value": True, "drawdown": False},
    )
    assert front

    ranked = engine.deterministic_rank(
        scored=scored,
        objectives={"expected_value": True, "drawdown": False},
    )
    assert ranked[0].case.case_id in {"case-2", "case-3"}


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
def seeded_manifest(sqlite_manager: DatabaseSessionManager) -> int:
    with sqlite_manager.session_scope() as session:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        provider = DataProvider(
            name="csv",
            vendor="local",
            description="fixture",
            enabled=False,
            created_at=now,
            updated_at=now,
        )
        underlying = Underlying(symbol="SPY", name="SPY", currency="USD", active=True)
        session.add_all([provider, underlying])
        session.flush()
        manifest = DatasetManifest(
            provider_id=provider.id,
            dataset_name="options",
            dataset_version="2026.01",
            schema_version="1.0",
            symbol_scope=["SPY"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            created_timestamp=now,
            checksum="seed",
            row_count=0,
            source_metadata={"source": "test"},
        )
        session.add(manifest)
        session.flush()
        return manifest.id


def test_probability_run_persistence_requires_reproducibility_metadata(
    sqlite_manager: DatabaseSessionManager,
    seeded_manifest: int,
) -> None:
    persistence = ResearchPersistenceService(sqlite_manager)
    ts = datetime(2026, 1, 10, 15, 30, tzinfo=UTC)
    run = ResearchRunDTO(
        run_id="prob-run-1",
        strategy_type="calendar_spread",
        symbol="SPY",
        entry_date=date(2026, 1, 10),
        exit_date=date(2026, 2, 10),
        configuration={
            "strategy_definition": {"name": "calendar"},
            "lifecycle_policies": {"profit_target": 1.0},
            "probability_method": "historical+model",
            "simulation_assumptions": {"paths": 100},
            "pricing_models": {"front": "black_scholes", "back": "cox_ross_rubinstein"},
            "tree_step_settings": {"steps": 200},
            "volatility_surface_snapshot": {"id": "surface-1"},
            "regime_classification": {"label": "contango"},
            "data_quality_policy": {"quality_floor": 0.6},
            "dataset_manifests": [seeded_manifest],
            "parameter_set": {"front_dte": 30},
        },
        parameters={"front_dte": 30, "back_dte": 60},
        software_version="0.1.0",
        manifest_id=seeded_manifest,
        run_timestamp=ts,
        checksums={"dataset": "abc"},
        quality_score=Decimal("0.82"),
        summary_metrics={
            "historical_pop": 0.64,
            "model_pop": 0.61,
            "expected_value": 0.12,
            "tail_loss_p95": -0.22,
            "theta_capture": 0.4,
        },
        metadata_json={
            "random_seed": 42,
            "software_git_commit": "abcdef",
            "result_checksums": {"run": "digest"},
            "calibration_metadata": {"brier": 0.16},
        },
        created_at=ts,
    )
    opportunities = [
        ResearchOpportunityDTO(
            as_of_timestamp=datetime(2026, 1, 10, 15, 30, tzinfo=UTC),
            opportunity_score=Decimal("0.70"),
            confidence=Decimal("0.79"),
            historical_pop=Decimal("0.64"),
            expected_value=Decimal("0.12"),
            theta_capture=Decimal("0.35"),
            quality_score=Decimal("0.80"),
            term_structure_regime="contango",
            diagnostics={"score": 0.7},
            warnings=[],
        )
    ]

    row_id = persistence.store_probability_run(run, opportunities)
    assert row_id > 0

    with sqlite_manager.session_scope() as session:
        query = HistoricalQueryService(session)
        model_pop = query.highest_model_pop_runs(as_of=datetime(2026, 1, 11, tzinfo=UTC), limit=10)
        assert len(model_pop) == 1

        tail = query.lowest_tail_loss_runs(as_of=datetime(2026, 1, 11, tzinfo=UTC), limit=10)
        assert len(tail) == 1


def test_no_look_ahead_still_holds_for_probability_queries(
    sqlite_manager: DatabaseSessionManager,
    seeded_manifest: int,
) -> None:
    persistence = ResearchPersistenceService(sqlite_manager)
    run = ResearchRunDTO(
        run_id="prob-run-2",
        strategy_type="calendar_spread",
        symbol="SPY",
        entry_date=date(2026, 1, 11),
        exit_date=date(2026, 2, 11),
        configuration={
            "strategy_definition": {},
            "lifecycle_policies": {},
            "probability_method": "historical",
            "simulation_assumptions": {},
            "pricing_models": {},
            "tree_step_settings": {},
            "volatility_surface_snapshot": {},
            "regime_classification": {},
            "data_quality_policy": {},
            "dataset_manifests": [seeded_manifest],
            "parameter_set": {},
        },
        parameters={},
        software_version="0.1.0",
        manifest_id=seeded_manifest,
        run_timestamp=datetime(2026, 1, 15, tzinfo=UTC),
        checksums={"dataset": "x"},
        quality_score=Decimal("0.7"),
        summary_metrics={
            "historical_pop": 0.5,
            "model_pop": 0.5,
            "expected_value": 0.0,
            "tail_loss_p95": -0.1,
            "theta_capture": 0.1,
        },
        metadata_json={
            "random_seed": 1,
            "software_git_commit": "g",
            "result_checksums": {},
            "calibration_metadata": {},
        },
        created_at=datetime(2026, 1, 15, tzinfo=UTC),
    )
    persistence.store_probability_run(run, opportunities=[])

    with sqlite_manager.session_scope() as session:
        query = HistoricalQueryService(session)
        assert query.highest_model_pop_runs(as_of=datetime(2026, 1, 14, tzinfo=UTC), limit=10) == []
