from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.models import (
    Base,
    CorporateAction,
    DataLineageRecord,
    DataProvider,
    DatasetManifest,
    Dividend,
    EarningsEvent,
    Exchange,
    InterestRateCurve,
    OptionContract,
    OptionQuote,
    TradingCalendar,
    Underlying,
    UnderlyingPrice,
)
from backend.database.repositories import (
    ContractsRepository,
    ManifestsLineageRepository,
    QuotesRepository,
)
from backend.database.session import DatabaseSessionManager


@pytest.fixture()
def sqlite_session() -> Generator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _seed_reference_data(session: Session) -> tuple[int, int, int, int, int]:
    now = datetime.now(tz=UTC)
    provider = DataProvider(
        name="csv",
        vendor="local",
        description="offline fixture",
        enabled=False,
        created_at=now,
        updated_at=now,
    )
    underlying = Underlying(symbol="SPY", name="SPDR S&P 500", currency="USD", active=True)
    exchange = Exchange(code="CBOE", name="CBOE", country="US", timezone="America/Chicago")
    session.add_all([provider, underlying, exchange])
    session.flush()

    calendar = TradingCalendar(
        exchange_id=exchange.id,
        trade_date=date(2026, 1, 2),
        is_trading_day=True,
        market_open_utc=now,
        market_close_utc=now,
    )
    session.add(calendar)

    manifest = DatasetManifest(
        provider_id=provider.id,
        dataset_name="options",
        dataset_version="2026.01",
        schema_version="1.0",
        symbol_scope=["SPY"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        created_timestamp=now,
        checksum="abc123",
        row_count=1,
        source_metadata={"source": "fixture"},
    )
    session.add(manifest)
    session.flush()

    return provider.id, underlying.id, exchange.id, manifest.id, calendar.id


def test_schema_creation_and_relationships(sqlite_session: Session) -> None:
    provider_id, underlying_id, exchange_id, manifest_id, _ = _seed_reference_data(sqlite_session)

    contract = OptionContract(
        provider_id=provider_id,
        provider_contract_id="SPY_20260116C00500000",
        underlying_id=underlying_id,
        option_root="SPY",
        occ_symbol="SPY260116C00500000",
        call_put="C",
        strike=Decimal("500"),
        expiration=date(2026, 1, 16),
        exercise_style="american",
        settlement_type="physical",
        multiplier=Decimal("100"),
        currency="USD",
        exchange_id=exchange_id,
        first_seen_at=datetime.now(tz=UTC),
        last_seen_at=datetime.now(tz=UTC),
        is_active=True,
    )
    sqlite_session.add(contract)
    sqlite_session.flush()

    quote = OptionQuote(
        id=1,
        contract_id=contract.id,
        quote_timestamp=datetime(2026, 1, 5, 15, 30, tzinfo=UTC),
        bid=Decimal("1.00"),
        ask=Decimal("1.25"),
        last=Decimal("1.10"),
        bid_size=10,
        ask_size=12,
        volume=50,
        open_interest=100,
        implied_volatility=Decimal("0.25"),
        delta=None,
        gamma=None,
        theta=None,
        vega=None,
        rho=None,
        underlying_price=Decimal("500.00"),
        provider_id=provider_id,
        manifest_id=manifest_id,
    )
    sqlite_session.add(quote)

    underlying_price = UnderlyingPrice(
        id=1,
        underlying_id=underlying_id,
        price_timestamp=datetime(2026, 1, 5, 15, 30, tzinfo=UTC),
        price=Decimal("500.00"),
        provider_id=provider_id,
        manifest_id=manifest_id,
    )
    dividend = Dividend(
        underlying_id=underlying_id,
        ex_date=date(2026, 2, 1),
        pay_date=date(2026, 2, 15),
        amount=Decimal("1.20"),
        currency="USD",
        provider_id=provider_id,
        manifest_id=manifest_id,
    )
    earnings = EarningsEvent(
        underlying_id=underlying_id,
        event_date=date(2026, 1, 30),
        event_timestamp=datetime(2026, 1, 30, 21, 0, tzinfo=UTC),
        fiscal_period="Q4",
        provider_id=provider_id,
        manifest_id=manifest_id,
    )
    action = CorporateAction(
        underlying_id=underlying_id,
        action_date=date(2026, 3, 1),
        action_type="split",
        ratio=Decimal("2.0"),
        description="2-for-1",
        provider_id=provider_id,
        manifest_id=manifest_id,
    )
    curve = InterestRateCurve(
        provider_id=provider_id,
        manifest_id=manifest_id,
        as_of_date=date(2026, 1, 5),
        tenor_days=30,
        rate=Decimal("0.045"),
    )
    lineage = DataLineageRecord(
        provider_id=provider_id,
        manifest_id=manifest_id,
        imported_at=datetime(2026, 1, 6, 0, 0, tzinfo=UTC),
        transformation_summary="normalize",
        validation_summary={"valid": True},
        source_metadata={"batch": "a"},
        software_version="0.1.0",
    )

    sqlite_session.add_all([underlying_price, dividend, earnings, action, curve, lineage])
    sqlite_session.commit()

    loaded_quote = sqlite_session.execute(select(OptionQuote)).scalar_one()
    assert loaded_quote.contract.provider_contract_id == "SPY_20260116C00500000"
    assert loaded_quote.manifest.dataset_name == "options"


def test_constraints_bid_not_above_ask(sqlite_session: Session) -> None:
    provider_id, underlying_id, exchange_id, manifest_id, _ = _seed_reference_data(sqlite_session)

    contract = OptionContract(
        provider_id=provider_id,
        provider_contract_id="X",
        underlying_id=underlying_id,
        option_root="SPY",
        occ_symbol=None,
        call_put="P",
        strike=Decimal("300"),
        expiration=date(2026, 1, 16),
        exercise_style="american",
        settlement_type="physical",
        multiplier=Decimal("100"),
        currency="USD",
        exchange_id=exchange_id,
        first_seen_at=datetime.now(tz=UTC),
        last_seen_at=datetime.now(tz=UTC),
        is_active=True,
    )
    sqlite_session.add(contract)
    sqlite_session.flush()

    sqlite_session.add(
        OptionQuote(
            id=2,
            contract_id=contract.id,
            quote_timestamp=datetime(2026, 1, 5, 15, 30, tzinfo=UTC),
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
    )

    with pytest.raises(IntegrityError):
        sqlite_session.commit()


def test_repository_upsert_lookup_and_nullable_vendor_values(sqlite_session: Session) -> None:
    provider_id, underlying_id, exchange_id, manifest_id, _ = _seed_reference_data(sqlite_session)
    contracts_repo = ContractsRepository(sqlite_session)
    quotes_repo = QuotesRepository(sqlite_session)

    contracts_repo.batch_upsert(
        [
            {
                "provider_id": provider_id,
                "provider_contract_id": "SPY_A",
                "underlying_id": underlying_id,
                "option_root": "SPY",
                "occ_symbol": "SPY260116C00500000",
                "call_put": "C",
                "strike": Decimal("500"),
                "expiration": date(2026, 1, 16),
                "exercise_style": "american",
                "settlement_type": "physical",
                "multiplier": Decimal("100"),
                "currency": "USD",
                "exchange_id": exchange_id,
                "first_seen_at": datetime(2026, 1, 1, tzinfo=UTC),
                "last_seen_at": datetime(2026, 1, 2, tzinfo=UTC),
                "is_active": True,
            }
        ]
    )
    sqlite_session.flush()

    contract = contracts_repo.lookup_by_provider_contract(provider_id, "SPY_A")
    assert contract is not None

    quotes_repo.batch_upsert(
        [
            {
                "id": 10,
                "contract_id": contract.id,
                "quote_timestamp": datetime(2026, 1, 5, 15, 30, tzinfo=UTC),
                "bid": Decimal("1.00"),
                "ask": Decimal("1.10"),
                "last": None,
                "bid_size": None,
                "ask_size": None,
                "volume": None,
                "open_interest": None,
                "implied_volatility": None,
                "delta": None,
                "gamma": None,
                "theta": None,
                "vega": None,
                "rho": None,
                "underlying_price": None,
                "provider_id": provider_id,
                "manifest_id": manifest_id,
            }
        ]
    )
    sqlite_session.commit()

    rows = quotes_repo.query_range(
        contract.id,
        datetime(2026, 1, 5, 0, 0, tzinfo=UTC),
        datetime(2026, 1, 6, 0, 0, tzinfo=UTC),
    )
    assert len(rows) == 1
    assert rows[0].delta is None
    assert rows[0].implied_volatility is None


def test_manifest_lineage_repository_and_duplicate_handling(sqlite_session: Session) -> None:
    provider_id, _, _, _, _ = _seed_reference_data(sqlite_session)
    repo = ManifestsLineageRepository(sqlite_session)

    manifest_payload = {
        "provider_id": provider_id,
        "dataset_name": "options",
        "dataset_version": "2026.01",
        "schema_version": "1.0",
        "symbol_scope": ["SPY"],
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 1, 31),
        "created_timestamp": datetime(2026, 1, 1, tzinfo=UTC),
        "checksum": "v1",
        "row_count": 100,
        "source_metadata": {"source": "test"},
    }
    repo.batch_upsert_manifests([manifest_payload])
    repo.batch_upsert_manifests([{**manifest_payload, "row_count": 200, "checksum": "v2"}])
    sqlite_session.flush()

    manifest = repo.lookup_manifest(provider_id, "options", "2026.01")
    assert manifest is not None
    assert manifest.row_count == 200
    assert manifest.checksum == "v2"

    repo.insert_lineage(
        [
            {
                "provider_id": provider_id,
                "manifest_id": manifest.id,
                "imported_at": datetime(2026, 1, 2, tzinfo=UTC),
                "transformation_summary": "normalize",
                "validation_summary": {"issues": 0},
                "source_metadata": {"source": "test"},
                "software_version": "0.1.0",
            }
        ]
    )
    sqlite_session.commit()

    lineage = repo.lineage_for_manifest(manifest.id)
    assert len(lineage) == 1


def test_transaction_rolls_back_on_error() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)

    with pytest.raises(Exception):
        with manager.session_scope() as session:
            now = datetime.now(tz=UTC)
            session.add(
                DataProvider(
                    name="csv",
                    vendor="local",
                    description="fixture",
                    enabled=False,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                DataProvider(
                    name="csv",
                    vendor="duplicate",
                    description="fixture",
                    enabled=False,
                    created_at=now,
                    updated_at=now,
                )
            )

    with Session(engine) as verify:
        count = verify.execute(select(DataProvider)).scalars().all()
        assert len(count) == 0

    Base.metadata.drop_all(engine)
    engine.dispose()
