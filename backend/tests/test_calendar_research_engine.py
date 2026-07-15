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
    deterministic_research_checksum,
)
from backend.database.models import Base, DataProvider, DatasetManifest, Underlying
from backend.database.session import DatabaseSessionManager
from backend.pricing import OptionType
from backend.research import (
    CalendarOpportunityScorer,
    HistoricalAnalyticsEngine,
    HistoricalRegimeEngine,
    OpportunityFeatures,
    ParameterSweepEngine,
    ParameterSweepGrid,
    RegimeClassificationInput,
    StrategyFactory,
    StrategyLeg,
    StrategyStatePoint,
    StrategyType,
)


def test_strategy_framework_exposes_required_fields() -> None:
    factory = StrategyFactory()
    strategy = factory.build(
        strategy_type=StrategyType.CALENDAR_SPREAD,
        symbol="SPY",
        legs=[
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
        ],
        entry_date=date(2026, 1, 10),
        exit_date=date(2026, 2, 10),
        metadata={"note": "research only"},
    )

    assert strategy.legs
    assert strategy.expirations == (date(2026, 2, 20), date(2026, 3, 20))
    assert strategy.strikes == (100.0, 100.0)
    assert strategy.option_types == (OptionType.CALL, OptionType.CALL)
    assert strategy.quantities == (-1.0, 1.0)
    assert strategy.entry_date == date(2026, 1, 10)
    assert strategy.exit_date == date(2026, 2, 10)


def test_regime_engine_classifies_requested_flags() -> None:
    engine = HistoricalRegimeEngine()
    regime = engine.classify(
        RegimeClassificationInput(
            as_of=datetime(2026, 1, 15, tzinfo=UTC),
            symbol="SPY",
            slope=-0.03,
            realized_volatility=0.35,
            earnings_front_elevation=0.07,
            atm_iv=0.32,
            prior_atm_iv=0.28,
        )
    )

    labels = {item.value for item in regime.flags}
    assert "backwardation" in labels
    assert "earnings_distortion" in labels
    assert "iv_expansion" in labels
    assert "high_realized_vol" in labels
    assert 0.0 <= regime.confidence <= 1.0


def test_opportunity_scoring_returns_explainable_components() -> None:
    scorer = CalendarOpportunityScorer()
    result = scorer.score(
        OpportunityFeatures(
            term_structure_slope=0.02,
            forward_volatility=0.25,
            realized_volatility=0.18,
            iv_percentile=0.72,
            iv_rank=0.66,
            smile_skew=-0.03,
            kurtosis=1.8,
            liquidity=0.82,
            spread_width=0.09,
            open_interest=0.76,
            volume=0.68,
            quality_score=0.9,
        )
    )

    assert 0.0 <= result.opportunity_score <= 1.0
    assert 0.0 <= result.confidence <= 1.0
    assert result.components
    assert all(component.details.startswith("normalized=") for component in result.components)


def test_historical_analytics_metrics_are_deterministic() -> None:
    states = [
        StrategyStatePoint(
            timestamp=datetime(2026, 1, 1, 15, 30) + timedelta(days=index),
            implied_volatility=0.2,
            realized_volatility=0.18,
            iv_percentile=0.6,
            iv_rank=0.55,
            theta=0.01,
            gamma=0.02,
            vega=0.12,
            charm=0.004,
            vanna=0.003,
            vomma=0.005,
            pnl=value,
            intrinsic_value=0.4,
            extrinsic_value=0.6,
        )
        for index, value in enumerate([0.1, -0.05, 0.2, -0.1, 0.07], start=1)
    ]
    returns = [point.pnl for point in states]

    summary = HistoricalAnalyticsEngine().summarize(returns=returns, states=states)

    assert summary.historical_pop == 3 / 5
    assert summary.average_winner > 0.0
    assert summary.average_loser < 0.0
    assert summary.max_drawdown >= 0.0
    assert summary.theta_capture > 0.0


def test_parameter_sweep_is_exhaustive_and_deterministic() -> None:
    cases = ParameterSweepEngine().generate_cases(
        ParameterSweepGrid(
            parameters={
                "front_dte": (7, 14),
                "back_dte": (30, 45),
                "iv_rank": (0.4, 0.6),
            }
        )
    )

    assert len(cases) == 8
    assert cases[0].case_id == "case-000001"
    assert set(cases[0].parameters) == {"front_dte", "back_dte", "iv_rank"}
    assert cases[-1].case_id == "case-000008"


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


def test_research_result_persistence_and_no_lookahead_queries(
    sqlite_manager: DatabaseSessionManager,
    seeded_manifest: int,
) -> None:
    persistence = ResearchPersistenceService(sqlite_manager)
    run_timestamp = datetime(2026, 1, 10, 15, 30, tzinfo=UTC)
    run = ResearchRunDTO(
        run_id="run-1",
        strategy_type="calendar_spread",
        symbol="SPY",
        entry_date=date(2026, 1, 10),
        exit_date=date(2026, 2, 10),
        configuration={"dte": [30, 60]},
        parameters={"front_dte": 30, "back_dte": 60},
        software_version="0.1.0",
        manifest_id=seeded_manifest,
        run_timestamp=run_timestamp,
        checksums={"dataset": "abc"},
        quality_score=Decimal("0.82"),
        summary_metrics={"historical_pop": 0.64, "expected_value": 0.12, "theta_capture": 0.4},
        metadata_json={"mode": "offline"},
        created_at=run_timestamp,
    )
    opportunities = [
        ResearchOpportunityDTO(
            as_of_timestamp=datetime(2026, 1, 9, 15, 30, tzinfo=UTC),
            opportunity_score=Decimal("0.71"),
            confidence=Decimal("0.80"),
            historical_pop=Decimal("0.63"),
            expected_value=Decimal("0.10"),
            theta_capture=Decimal("0.35"),
            quality_score=Decimal("0.79"),
            term_structure_regime="contango",
            diagnostics={"slope": 0.02},
            warnings=[],
        ),
        ResearchOpportunityDTO(
            as_of_timestamp=datetime(2026, 1, 12, 15, 30, tzinfo=UTC),
            opportunity_score=Decimal("0.76"),
            confidence=Decimal("0.84"),
            historical_pop=Decimal("0.66"),
            expected_value=Decimal("0.13"),
            theta_capture=Decimal("0.39"),
            quality_score=Decimal("0.83"),
            term_structure_regime="backwardation",
            diagnostics={"slope": -0.03},
            warnings=["wide spread"],
        ),
    ]

    run_row_id = persistence.store_run(run, opportunities)
    assert run_row_id > 0

    checksum_a = deterministic_research_checksum(run=run, opportunities=opportunities)
    checksum_b = deterministic_research_checksum(run=run, opportunities=opportunities)
    assert checksum_a == checksum_b

    with sqlite_manager.session_scope() as session:
        query = HistoricalQueryService(session)

        early = query.best_calendar_opportunities(
            as_of=datetime(2026, 1, 10, 0, 0, tzinfo=UTC),
            limit=10,
        )
        assert len(early) == 1

        full = query.best_calendar_opportunities(
            as_of=datetime(2026, 1, 13, 0, 0, tzinfo=UTC),
            limit=10,
        )
        assert len(full) == 2
        assert float(full[0].opportunity_score) >= float(full[1].opportunity_score)

        assert query.highest_pop_runs(as_of=datetime(2026, 1, 9, tzinfo=UTC), limit=10) == []
        pop_runs = query.highest_pop_runs(as_of=datetime(2026, 1, 12, tzinfo=UTC), limit=10)
        assert len(pop_runs) == 1

        ev_runs = query.highest_ev_runs(as_of=datetime(2026, 1, 12, tzinfo=UTC), limit=10)
        assert len(ev_runs) == 1

        theta_runs = query.best_theta_capture_runs(
            as_of=datetime(2026, 1, 12, tzinfo=UTC),
            limit=10,
        )
        assert len(theta_runs) == 1

        quality_runs = query.highest_quality_research_runs(
            as_of=datetime(2026, 1, 12, tzinfo=UTC),
            limit=10,
        )
        assert len(quality_runs) == 1

        term = query.best_term_structure_opportunities(
            as_of=datetime(2026, 1, 13, tzinfo=UTC),
            regime_label="contango",
            limit=10,
        )
        assert len(term) == 1

        regime = query.best_historical_regime(
            as_of=datetime(2026, 1, 13, tzinfo=UTC),
            regime_label="backwardation",
            limit=10,
        )
        assert len(regime) == 1
