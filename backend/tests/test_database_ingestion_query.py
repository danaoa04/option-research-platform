from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select

from backend.database.dtos import (
    CorporateActionDTO,
    DatasetManifestDTO,
    DividendDTO,
    EarningsEventDTO,
    InterestRateCurveDTO,
    OptionContractDTO,
    OptionQuoteDTO,
    UnderlyingPriceDTO,
)
from backend.database.ingestion import BulkIngestionService, IngestionConfig, UpsertPolicy
from backend.database.models import Base, DataProvider, DatasetManifest, OptionContract, Underlying
from backend.database.query import HistoricalQueryService
from backend.database.session import DatabaseSessionManager


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
def seeded_ids(sqlite_manager: DatabaseSessionManager) -> tuple[int, int, int]:
    with sqlite_manager.session_scope() as session:
        now = datetime.now(tz=UTC)
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
        return provider.id, underlying.id, manifest.id


def test_batch_ingestion_and_upsert(
    sqlite_manager: DatabaseSessionManager,
    seeded_ids: tuple[int, int, int],
) -> None:
    provider_id, underlying_id, _ = seeded_ids
    service = BulkIngestionService(sqlite_manager, config=IngestionConfig(batch_size=1))

    payload = [
        OptionContractDTO(
            provider_id=provider_id,
            provider_contract_id="SPY-C-500",
            underlying_id=underlying_id,
            option_root="SPY",
            occ_symbol="SPY260117C00500000",
            call_put="C",
            strike=Decimal("500"),
            expiration=date(2026, 1, 17),
            exercise_style="american",
            settlement_type="physical",
            multiplier=Decimal("100"),
            currency="USD",
            exchange_id=None,
            first_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
            last_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
            is_active=True,
        ),
        OptionContractDTO(
            provider_id=provider_id,
            provider_contract_id="SPY-C-500",
            underlying_id=underlying_id,
            option_root="SPY",
            occ_symbol="SPY260117C00500000",
            call_put="C",
            strike=Decimal("505"),
            expiration=date(2026, 1, 17),
            exercise_style="american",
            settlement_type="physical",
            multiplier=Decimal("100"),
            currency="USD",
            exchange_id=None,
            first_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
            last_seen_at=datetime(2026, 1, 2, tzinfo=UTC),
            is_active=True,
        ),
    ]

    result = service.ingest_contracts(payload)

    assert result.requested == 2
    assert result.duplicates_dropped == 1
    assert result.inserted_or_updated == 1

    with sqlite_manager.session_scope() as session:
        row = session.query(OptionContract).filter_by(provider_contract_id="SPY-C-500").one()
        assert row.strike == Decimal("505")


def test_insert_only_policy_ignores_existing_duplicates(
    sqlite_manager: DatabaseSessionManager,
    seeded_ids: tuple[int, int, int],
) -> None:
    provider_id, underlying_id, _ = seeded_ids
    service = BulkIngestionService(
        sqlite_manager,
        config=IngestionConfig(contract_policy=UpsertPolicy.INSERT_ONLY),
    )

    dto = OptionContractDTO(
        provider_id=provider_id,
        provider_contract_id="SPY-C-510",
        underlying_id=underlying_id,
        option_root="SPY",
        occ_symbol="SPY260117C00510000",
        call_put="C",
        strike=Decimal("510"),
        expiration=date(2026, 1, 17),
        exercise_style="american",
        settlement_type="physical",
        multiplier=Decimal("100"),
        currency="USD",
        exchange_id=None,
        first_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
        last_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
        is_active=True,
    )

    service.ingest_contracts([dto])
    service.ingest_contracts([dto])

    with sqlite_manager.session_scope() as session:
        count = session.query(OptionContract).filter_by(provider_contract_id="SPY-C-510").count()
        assert count == 1


def test_quote_validation_and_rollback(
    sqlite_manager: DatabaseSessionManager,
    seeded_ids: tuple[int, int, int],
) -> None:
    provider_id, underlying_id, manifest_id = seeded_ids
    service = BulkIngestionService(sqlite_manager)

    service.ingest_contracts(
        [
            OptionContractDTO(
                provider_id=provider_id,
                provider_contract_id="SPY-P-490",
                underlying_id=underlying_id,
                option_root="SPY",
                occ_symbol="SPY260117P00490000",
                call_put="P",
                strike=Decimal("490"),
                expiration=date(2026, 1, 17),
                exercise_style="american",
                settlement_type="physical",
                multiplier=Decimal("100"),
                currency="USD",
                exchange_id=None,
                first_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
                last_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
                is_active=True,
            )
        ]
    )

    with sqlite_manager.session_scope() as session:
        contract_id = session.execute(
            select(OptionContract.id).where(OptionContract.provider_contract_id == "SPY-P-490")
        ).scalar_one()

    bad_quote = OptionQuoteDTO(
        id=1,
        contract_id=contract_id,
        quote_timestamp=datetime(2026, 1, 10, 10, 0, tzinfo=UTC),
        bid=Decimal("2.0"),
        ask=Decimal("1.0"),
        last=None,
        bid_size=None,
        ask_size=None,
        volume=None,
        open_interest=None,
        implied_volatility=None,
        delta=None,
        gamma=None,
        theta=None,
        vega=None,
        rho=None,
        underlying_price=None,
        provider_id=provider_id,
        manifest_id=manifest_id,
    )

    result = service.ingest_quotes([bad_quote])

    assert result.failed == 1
    assert any(issue.code == "crossed_market" for issue in result.validation_issues)

    with sqlite_manager.session_scope() as session:
        assert session.query(OptionContract).count() == 1


def test_as_of_queries_no_lookahead_and_stale_age(
    sqlite_manager: DatabaseSessionManager,
    seeded_ids: tuple[int, int, int],
) -> None:
    provider_id, underlying_id, manifest_id = seeded_ids
    service = BulkIngestionService(sqlite_manager)

    service.ingest_contracts(
        [
            OptionContractDTO(
                provider_id=provider_id,
                provider_contract_id="SPY-C-495",
                underlying_id=underlying_id,
                option_root="SPY",
                occ_symbol="SPY260117C00495000",
                call_put="C",
                strike=Decimal("495"),
                expiration=date(2026, 1, 17),
                exercise_style="american",
                settlement_type="physical",
                multiplier=Decimal("100"),
                currency="USD",
                exchange_id=None,
                first_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
                last_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
                is_active=True,
            )
        ]
    )

    with sqlite_manager.session_scope() as session:
        contract_id = session.execute(
            select(OptionContract.id).where(OptionContract.provider_contract_id == "SPY-C-495")
        ).scalar_one()

    t0 = datetime(2026, 1, 10, 10, 0, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=5)
    t2 = t0 + timedelta(minutes=20)

    service.ingest_quotes(
        [
            OptionQuoteDTO(
                id=100,
                contract_id=contract_id,
                quote_timestamp=t0,
                bid=Decimal("1.0"),
                ask=Decimal("1.2"),
                last=Decimal("1.1"),
                bid_size=10,
                ask_size=12,
                volume=100,
                open_interest=200,
                implied_volatility=Decimal("0.2"),
                delta=None,
                gamma=None,
                theta=None,
                vega=None,
                rho=None,
                underlying_price=Decimal("500"),
                provider_id=provider_id,
                manifest_id=manifest_id,
            ),
            OptionQuoteDTO(
                id=101,
                contract_id=contract_id,
                quote_timestamp=t2,
                bid=Decimal("1.3"),
                ask=Decimal("1.4"),
                last=Decimal("1.35"),
                bid_size=11,
                ask_size=13,
                volume=110,
                open_interest=210,
                implied_volatility=Decimal("0.21"),
                delta=None,
                gamma=None,
                theta=None,
                vega=None,
                rho=None,
                underlying_price=Decimal("501"),
                provider_id=provider_id,
                manifest_id=manifest_id,
            ),
        ]
    )

    with sqlite_manager.session_scope() as session:
        query = HistoricalQueryService(session)

        nearest = query.nearest_quote(contract_id=contract_id, as_of=t1, exact_match=False)
        assert nearest.record is not None
        assert nearest.record.quote_timestamp.replace(tzinfo=UTC) == t0
        assert nearest.stale_age_seconds == 300.0

        exact = query.nearest_quote(contract_id=contract_id, as_of=t1, exact_match=True)
        assert exact.record is None

        chain = query.option_chain_at("SPY", t1, nearest_prior=True)
        assert chain
        assert all(item.quote_timestamp.replace(tzinfo=UTC) <= t1 for item in chain)


def test_manifest_ingestion_validation_failure_on_duplicate_identifier(
    sqlite_manager: DatabaseSessionManager,
    seeded_ids: tuple[int, int, int],
) -> None:
    provider_id, _, _ = seeded_ids
    service = BulkIngestionService(sqlite_manager)

    t = datetime(2026, 1, 1, tzinfo=UTC)
    manifests = [
        DatasetManifestDTO(
            provider_id=provider_id,
            dataset_name="quotes",
            dataset_version="v1",
            schema_version="1.0",
            symbol_scope=["SPY"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 2),
            created_timestamp=t,
            checksum="a",
            row_count=1,
            source_metadata={"source": "a"},
        ),
        DatasetManifestDTO(
            provider_id=provider_id,
            dataset_name="quotes",
            dataset_version="v1",
            schema_version="1.0",
            symbol_scope=["SPY"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 2),
            created_timestamp=t,
            checksum="b",
            row_count=2,
            source_metadata={"source": "b"},
        ),
    ]

    result = service.ingest_manifests(manifests)

    assert result.failed == 0
    assert result.duplicates_dropped == 1
    assert any(issue.code == "duplicate_manifest_identifier" for issue in result.validation_issues)


def test_historical_range_queries_for_underlying_events_and_rates(
    sqlite_manager: DatabaseSessionManager,
    seeded_ids: tuple[int, int, int],
) -> None:
    provider_id, underlying_id, manifest_id = seeded_ids
    service = BulkIngestionService(sqlite_manager)

    service.ingest_underlying_prices(
        [
            UnderlyingPriceDTO(
                id=1,
                underlying_id=underlying_id,
                price_timestamp=datetime(2026, 1, 3, 10, 0, tzinfo=UTC),
                price=Decimal("500"),
                provider_id=provider_id,
                manifest_id=manifest_id,
            )
        ]
    )
    service.ingest_dividends(
        [
            DividendDTO(
                underlying_id=underlying_id,
                ex_date=date(2026, 2, 1),
                pay_date=date(2026, 2, 15),
                amount=Decimal("1.2"),
                currency="USD",
                provider_id=provider_id,
                manifest_id=manifest_id,
            )
        ]
    )
    service.ingest_earnings(
        [
            EarningsEventDTO(
                underlying_id=underlying_id,
                event_date=date(2026, 2, 5),
                event_timestamp=datetime(2026, 2, 5, 21, 0, tzinfo=UTC),
                fiscal_period="Q1",
                provider_id=provider_id,
                manifest_id=manifest_id,
            )
        ]
    )
    service.ingest_corporate_actions(
        [
            CorporateActionDTO(
                underlying_id=underlying_id,
                action_date=date(2026, 2, 7),
                action_type="split",
                ratio=Decimal("2"),
                description="2-for-1",
                provider_id=provider_id,
                manifest_id=manifest_id,
            )
        ]
    )
    service.ingest_interest_rate_curves(
        [
            InterestRateCurveDTO(
                provider_id=provider_id,
                manifest_id=manifest_id,
                as_of_date=date(2026, 2, 4),
                tenor_days=30,
                rate=Decimal("0.04"),
            )
        ]
    )

    with sqlite_manager.session_scope() as session:
        query = HistoricalQueryService(session)
        prices = query.underlying_price_history(
            underlying_id=underlying_id,
            start_ts=datetime(2026, 1, 1, tzinfo=UTC),
            end_ts=datetime(2026, 1, 31, tzinfo=UTC),
        )
        dividends = query.dividends_by_range(
            underlying_id=underlying_id,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
        )
        earnings = query.earnings_by_range(
            underlying_id=underlying_id,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
        )
        actions = query.corporate_actions_by_symbol("SPY")
        rates_exact = query.interest_rate_curve_by_date(date(2026, 2, 4), nearest_prior=False)
        rates_prior = query.interest_rate_curve_by_date(date(2026, 2, 6), nearest_prior=True)

        assert len(prices) == 1
        assert len(dividends) == 1
        assert len(earnings) == 1
        assert len(actions) == 1
        assert len(rates_exact) == 1
        assert len(rates_prior) == 1
