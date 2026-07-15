from __future__ import annotations

from collections.abc import Generator
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import create_engine

from backend.database import SnapshotService, VolatilityPersistenceService
from backend.database.dtos import DatasetSnapshotDTO
from backend.database.models import Base, DataProvider, DatasetManifest, Underlying
from backend.database.query import HistoricalQueryService
from backend.database.session import DatabaseSessionManager
from backend.implied_volatility import (
    AnnualizationConvention,
    ExtrapolationPolicy,
    HistoricalVolatilityCalculator,
    HistoricalVolatilityConfig,
    HistoricalVolEstimator,
    InMemoryVolatilitySliceStore,
    InterpolationMethod,
    IVSolverStatus,
    MarketPriceSource,
    ObservationQualityScorer,
    OHLCBar,
    RegimeClassificationConfig,
    RegimeClassifier,
    SliceKind,
    SmileAxis,
    SmileBuildConfig,
    SmileBuilder,
    SolverConfig,
    SolverMethod,
    SurfaceBuildConfig,
    SurfaceBuilder,
    SurfaceNode,
    SurfaceNodeKind,
    TermStructureBuilder,
    TermStructureConfig,
    VolatilityObservationRecord,
    VolatilityTimeSliceMetadata,
)
from backend.implied_volatility.construction import compute_forward_volatility
from backend.implied_volatility.persistence import (
    DatabaseVolatilityWriter,
    VolatilitySliceAssembler,
)
from backend.implied_volatility.tree_policy import TreeResolutionPolicy
from backend.pricing import (
    ExerciseStyle,
    OptionType,
    PricingEngine,
    PricingModelName,
    PricingRequest,
)


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
def seeded_manifest(sqlite_manager: DatabaseSessionManager) -> tuple[int, int]:
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
        return provider.id, manifest.id


def _sample_bars() -> list[OHLCBar]:
    start = datetime(2026, 1, 1, 16, 0)
    bars: list[OHLCBar] = []
    for i in range(30):
        base = 100.0 + float(i)
        bars.append(
            OHLCBar(
                timestamp=start + timedelta(days=i),
                open=base,
                high=base + 1.5,
                low=base - 1.2,
                close=base + 0.3,
                split_adjusted=True,
            )
        )
    return bars


def _observation(
    *,
    ts: datetime,
    expiry: date,
    strike: float,
    iv: float,
    confidence: float,
    solver_status: IVSolverStatus = IVSolverStatus.SUCCESS,
) -> VolatilityObservationRecord:
    return VolatilityObservationRecord(
        symbol="SPY",
        valuation_timestamp=ts,
        expiration=expiry,
        strike=strike,
        option_type="call",
        moneyness=strike / 100.0,
        forward_moneyness=(strike + 1.0) / 100.0,
        delta=0.5,
        implied_volatility=iv,
        quote_source=MarketPriceSource.MID,
        pricing_model=PricingModelName.BLACK_SCHOLES,
        solver_method=SolverMethod.NEWTON_RAPHSON,
        solver_status=solver_status,
        pricing_error=1e-5,
        bid=1.0,
        ask=1.1,
        midpoint=1.05,
        spread_width=0.1,
        volume=100,
        open_interest=200,
        stale_age_seconds=5.0,
        contract_metadata={"exercise_style": "european"},
        dataset_manifest={"manifest": 1},
        quality_flags=(),
        vega=0.2,
        tree_sensitivity=0.0,
        confidence_score=confidence,
        observation_id=f"obs-{ts.isoformat()}-{strike}",
    )


def test_all_historical_estimators_return_deterministic_results() -> None:
    bars = _sample_bars()
    calc = HistoricalVolatilityCalculator()

    for estimator in (
        HistoricalVolEstimator.CLOSE_TO_CLOSE,
        HistoricalVolEstimator.PARKINSON,
        HistoricalVolEstimator.GARMAN_KLASS,
        HistoricalVolEstimator.ROGERS_SATCHELL,
        HistoricalVolEstimator.YANG_ZHANG,
    ):
        cfg = HistoricalVolatilityConfig(
            estimator=estimator,
            lookback_window=20,
            annualization=AnnualizationConvention.TRADING_DAYS_252,
        )
        first = calc.calculate(bars, cfg)
        second = calc.calculate(bars, cfg)
        assert first.annualized_volatility is not None
        assert first.annualized_volatility == pytest.approx(second.annualized_volatility, abs=1e-12)


def test_historical_estimator_warns_on_insufficient_data() -> None:
    calc = HistoricalVolatilityCalculator()
    result = calc.calculate(
        _sample_bars()[:3],
        HistoricalVolatilityConfig(
            estimator=HistoricalVolEstimator.CLOSE_TO_CLOSE,
            lookback_window=10,
        ),
    )
    assert result.annualized_volatility is None
    assert any("insufficient data" in warning for warning in result.warnings)


def test_quality_scoring_flags_crossed_stale_wide_and_low_vega() -> None:
    scorer = ObservationQualityScorer()
    obs = _observation(
        ts=datetime(2026, 1, 1, 15, 30),
        expiry=date(2026, 2, 15),
        strike=100.0,
        iv=0.2,
        confidence=0.9,
        solver_status=IVSolverStatus.APPROXIMATE,
    )
    stressed = replace(
        obs,
        bid=1.2,
        ask=1.0,
        spread_width=0.8,
        midpoint=1.0,
        stale_age_seconds=5000.0,
        vega=1e-12,
    )
    result = scorer.score(stressed, neighbor_iv_jump=0.3, duplicate_contract=True)
    assert result.exclusion_recommendation is True
    assert len(result.reason_codes) >= 4


def test_tree_step_escalation_policy_reports_diagnostics() -> None:
    pricing_engine = PricingEngine()
    request = PricingRequest(
        spot=100.0,
        strike=100.0,
        expiry=date(2027, 1, 1),
        volatility=0.25,
        risk_free_rate=0.05,
        dividend_yield=0.0,
        option_type=OptionType.PUT,
        exercise_style=ExerciseStyle.AMERICAN,
        multiplier=1.0,
        valuation_date=date(2026, 1, 1),
        tree_steps=200,
    )
    policy = TreeResolutionPolicy(pricing_engine=pricing_engine)
    result = policy.evaluate(
        request=request,
        model_name=PricingModelName.COX_ROSS_RUBINSTEIN,
        implied_volatility=0.25,
        config=SolverConfig(
            tree_step_start=100,
            tree_step_max=800,
            tree_step_schedule=(1, 2, 4, 8),
        ),
    )
    assert result.selected_tree_steps <= 800
    assert len(result.diagnostics) >= 2


def test_smile_builder_handles_sparse_and_duplicate_strikes() -> None:
    ts = datetime(2026, 1, 1, 15, 30)
    expiry = date(2026, 2, 15)
    observations = [
        _observation(ts=ts, expiry=expiry, strike=95.0, iv=0.22, confidence=0.8),
        _observation(ts=ts, expiry=expiry, strike=100.0, iv=0.20, confidence=0.9),
        _observation(ts=ts, expiry=expiry, strike=100.0, iv=0.205, confidence=0.95),
        _observation(ts=ts, expiry=expiry, strike=105.0, iv=0.19, confidence=0.85),
    ]
    result = SmileBuilder().build(
        expiration=expiry,
        observations=observations,
        config=SmileBuildConfig(
            axis=SmileAxis.STRIKE,
            interpolation=InterpolationMethod.LINEAR,
            extrapolation=ExtrapolationPolicy.NONE,
            min_points=5,
        ),
    )
    assert any("sparse strikes" in warning for warning in result.warnings)
    assert any("duplicate axis point" in warning for warning in result.warnings)


def test_term_structure_contango_backwardation_and_mixed() -> None:
    builder = TermStructureBuilder()
    ts = date(2026, 1, 1)

    contango_smiles = [
        SmileBuilder().build(
            expiration=ts + timedelta(days=d),
            observations=[
                _observation(
                    ts=datetime(2026, 1, 1, 15, 30),
                    expiry=ts + timedelta(days=d),
                    strike=100.0,
                    iv=iv,
                    confidence=0.9,
                )
            ],
            config=SmileBuildConfig(min_points=1),
        )
        for d, iv in ((30, 0.2), (60, 0.24), (90, 0.26))
    ]
    contango = builder.build(
        contango_smiles,
        valuation_date=ts,
        target_x=100.0,
        config=TermStructureConfig(),
    )
    assert contango.classification == "contango"

    backward_smiles = [
        SmileBuilder().build(
            expiration=ts + timedelta(days=d),
            observations=[
                _observation(
                    ts=datetime(2026, 1, 1, 15, 30),
                    expiry=ts + timedelta(days=d),
                    strike=100.0,
                    iv=iv,
                    confidence=0.9,
                )
            ],
            config=SmileBuildConfig(min_points=1),
        )
        for d, iv in ((30, 0.3), (60, 0.24), (90, 0.2))
    ]
    backward = builder.build(
        backward_smiles,
        valuation_date=ts,
        target_x=100.0,
        config=TermStructureConfig(),
    )
    assert backward.classification == "backwardation"

    mixed_smiles = [
        SmileBuilder().build(
            expiration=ts + timedelta(days=d),
            observations=[
                _observation(
                    ts=datetime(2026, 1, 1, 15, 30),
                    expiry=ts + timedelta(days=d),
                    strike=100.0,
                    iv=iv,
                    confidence=0.9,
                )
            ],
            config=SmileBuildConfig(min_points=1),
        )
        for d, iv in ((30, 0.2), (60, 0.24), (90, 0.21))
    ]
    mixed = builder.build(
        mixed_smiles,
        valuation_date=ts,
        target_x=100.0,
        config=TermStructureConfig(monotonic_tolerance=0.001),
    )
    assert mixed.classification == "mixed"


def test_forward_volatility_negative_variance_is_invalid() -> None:
    diag = compute_forward_volatility(
        start_tenor_days=30,
        end_tenor_days=60,
        start_iv=0.4,
        end_iv=0.2,
    )
    assert diag.valid is False
    assert diag.reason == "negative forward variance"


def test_surface_reconstruction_and_quality_filtered_nodes() -> None:
    ts = datetime(2026, 1, 1, 15, 30)
    observations = [
        _observation(ts=ts, expiry=date(2026, 2, 15), strike=95.0, iv=0.22, confidence=0.9),
        _observation(ts=ts, expiry=date(2026, 2, 15), strike=105.0, iv=0.19, confidence=0.7),
        _observation(ts=ts, expiry=date(2026, 3, 15), strike=95.0, iv=0.24, confidence=0.8),
        _observation(ts=ts, expiry=date(2026, 3, 15), strike=105.0, iv=0.21, confidence=0.4),
    ]
    result = SurfaceBuilder().build(
        symbol="SPY",
        valuation_timestamp=ts,
        observations=observations,
        config=SurfaceBuildConfig(quality_floor=0.6),
    )
    raw_count = len([node for node in result.nodes if node.node_kind == SurfaceNodeKind.RAW])
    cleaned_count = len(
        [node for node in result.nodes if node.node_kind == SurfaceNodeKind.CLEANED]
    )
    assert raw_count == 4
    assert cleaned_count == 3


def test_regime_classifier_outputs_labels_and_confidence() -> None:
    ts = date(2026, 1, 1)
    smiles = [
        SmileBuilder().build(
            expiration=ts + timedelta(days=d),
            observations=[
                _observation(
                    ts=datetime(2026, 1, 1, 15, 30),
                    expiry=ts + timedelta(days=d),
                    strike=100.0,
                    iv=iv,
                    confidence=0.95,
                )
            ],
            config=SmileBuildConfig(min_points=1),
        )
        for d, iv in ((30, 0.28), (60, 0.31))
    ]
    term = TermStructureBuilder().build(
        smiles,
        valuation_date=ts,
        target_x=100.0,
        config=TermStructureConfig(),
    )
    regime = RegimeClassifier().classify(
        term_structure=term,
        realized_volatility=0.2,
        config=RegimeClassificationConfig(),
        prior_atm_iv=0.25,
    )
    assert regime.labels
    assert 0.0 <= regime.confidence <= 1.0


def test_persisted_time_slices_immutable_and_no_lookahead(
    sqlite_manager: DatabaseSessionManager,
    seeded_manifest: tuple[int, int],
) -> None:
    _, manifest_id = seeded_manifest
    persistence = VolatilityPersistenceService(sqlite_manager)
    writer = DatabaseVolatilityWriter(persistence=persistence)

    ts = datetime(2026, 1, 10, 15, 30, tzinfo=UTC)
    observations = [
        _observation(ts=ts, expiry=date(2026, 2, 15), strike=100.0, iv=0.2, confidence=0.9),
        _observation(ts=ts, expiry=date(2026, 3, 15), strike=100.0, iv=0.22, confidence=0.9),
    ]
    writer.persist_observations(observations, manifest_id=manifest_id)

    slice_meta = VolatilityTimeSliceMetadata(
        valuation_timestamp=ts,
        input_manifests=(manifest_id,),
        solver_metadata={"model": "black_scholes"},
        filtering_policy={"quality_floor": 0.6},
        interpolation_policy={"method": "linear"},
        tree_step_policy={"enabled": True},
        quality_thresholds={"min_score": 0.6},
        node_count=1,
        excluded_observation_count=0,
        checksums={},
        git_commit="abc123",
    )
    node = SurfaceNode(
        tenor_days=30,
        x=100.0,
        implied_volatility=0.2,
        node_kind=SurfaceNodeKind.CLEANED,
        quality_score=0.9,
        provenance={"source": "unit_test"},
    )
    writer.persist_slice(
        slice_id="slice-1",
        symbol="SPY",
        kind=SliceKind.SURFACE,
        metadata=slice_meta,
        nodes=[node],
    )
    writer.finalize_slice("slice-1")

    with pytest.raises(Exception):
        writer.finalize_slice("slice-1")

    with sqlite_manager.session_scope() as session:
        query = HistoricalQueryService(session)
        exact = query.surface_by_symbol_timestamp(symbol="SPY", valuation_timestamp=ts)
        assert exact is not None

        prior = query.nearest_prior_valid_surface(symbol="SPY", as_of=ts + timedelta(minutes=15))
        assert prior is not None
        assert prior.slice_id == "slice-1"


def test_in_memory_slice_store_and_assembler() -> None:
    store = InMemoryVolatilitySliceStore()
    assembler = VolatilitySliceAssembler()

    ts = datetime(2026, 1, 1, 15, 30)
    metadata = VolatilityTimeSliceMetadata(
        valuation_timestamp=ts,
        input_manifests=(1,),
        solver_metadata={"a": 1},
        filtering_policy={"q": 0.5},
        interpolation_policy={"method": "linear"},
        tree_step_policy={"enabled": True},
        quality_thresholds={"min": 0.5},
        node_count=0,
        excluded_observation_count=0,
        checksums={"x": "y"},
        git_commit="abc",
    )
    record = assembler.build_slice(
        slice_id="s1",
        symbol="SPY",
        kind=SliceKind.SURFACE,
        metadata=metadata,
        raw_nodes=[],
        cleaned_nodes=[],
        interpolated_nodes=[],
    )
    store.store_slice(record)
    loaded = store.get_slice("s1")
    assert loaded is not None
    assert loaded.symbol == "SPY"


def test_snapshot_immutable_behavior_for_volatility_context(
    sqlite_manager: DatabaseSessionManager,
    seeded_manifest: tuple[int, int],
) -> None:
    provider_id, manifest_id = seeded_manifest
    snapshot_service = SnapshotService(sqlite_manager)
    snapshot = DatasetSnapshotDTO(
        id="snap-vol-1",
        manifest_id=manifest_id,
        provider_id=provider_id,
        schema_version="3.0",
        dataset_version="2026.01",
        git_commit="abc123",
        date_start=date(2026, 1, 1),
        date_end=date(2026, 1, 31),
        symbol_scope=["SPY"],
        row_counts={"volatility_observations": 2},
        checksums={"snapshot_digest": "placeholder"},
        transformation_history=[],
        validation_summary={"ok": True},
        created_at=datetime(2026, 1, 31, tzinfo=UTC),
    )
    snapshot_service.create_snapshot(snapshot)
    with pytest.raises(Exception):
        snapshot_service.reject_snapshot_mutation("snap-vol-1")
