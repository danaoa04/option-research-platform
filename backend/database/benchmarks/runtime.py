"""Lightweight benchmark runtime for database ingestion and historical query paths."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from time import perf_counter

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.database.ingestion import BulkIngestionService, IngestionConfig
from backend.database.models import Base, DataProvider, DatasetManifest, OptionContract, Underlying
from backend.database.query import HistoricalQueryService
from backend.database.session import DatabaseSessionManager


@dataclass(slots=True, frozen=True)
class BenchmarkResult:
    name: str
    elapsed_seconds: float


def run_database_benchmarks(iterations: int = 100) -> list[BenchmarkResult]:
    return [
        _benchmark_batch_inserts(iterations),
        _benchmark_option_chain_query(iterations),
        _benchmark_quote_range_query(iterations),
    ]


def _benchmark_batch_inserts(iterations: int) -> BenchmarkResult:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)

    with manager.session_scope() as session:
        provider = DataProvider(
            name="bench",
            vendor="bench",
            description="benchmark",
            enabled=False,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        )
        underlying = Underlying(symbol="SPY", name="SPY", currency="USD", active=True)
        session.add_all([provider, underlying])
        session.flush()

        manifest = DatasetManifest(
            provider_id=provider.id,
            dataset_name="options",
            dataset_version="bench",
            schema_version="1.0",
            symbol_scope=["SPY"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            created_timestamp=datetime.now(tz=UTC),
            checksum="bench",
            row_count=iterations,
            source_metadata={"mode": "bench"},
        )
        session.add(manifest)

    service = BulkIngestionService(manager, config=IngestionConfig(batch_size=100))
    contracts = [
        OptionContract(
            provider_id=1,
            provider_contract_id=f"CONTRACT-{idx}",
            underlying_id=1,
            option_root="SPY",
            occ_symbol=None,
            call_put="C",
            strike=Decimal("100") + Decimal(idx),
            expiration=date(2026, 2, 20),
            exercise_style="american",
            settlement_type="physical",
            multiplier=Decimal("100"),
            currency="USD",
            exchange_id=None,
            first_seen_at=datetime.now(tz=UTC),
            last_seen_at=datetime.now(tz=UTC),
            is_active=True,
        )
        for idx in range(iterations)
    ]

    from backend.database.dtos import OptionContractDTO

    dto_payload = [
        OptionContractDTO(
            provider_id=item.provider_id,
            provider_contract_id=item.provider_contract_id,
            underlying_id=item.underlying_id,
            option_root=item.option_root,
            occ_symbol=item.occ_symbol,
            call_put=item.call_put,
            strike=item.strike,
            expiration=item.expiration,
            exercise_style=item.exercise_style,
            settlement_type=item.settlement_type,
            multiplier=item.multiplier,
            currency=item.currency,
            exchange_id=item.exchange_id,
            first_seen_at=item.first_seen_at,
            last_seen_at=item.last_seen_at,
            is_active=item.is_active,
        )
        for item in contracts
    ]

    started = perf_counter()
    service.ingest_contracts(dto_payload)
    elapsed = perf_counter() - started
    Base.metadata.drop_all(engine)
    engine.dispose()
    return BenchmarkResult(name="batch_inserts", elapsed_seconds=elapsed)


def _benchmark_option_chain_query(iterations: int) -> BenchmarkResult:
    session = _seed_query_dataset(iterations)
    query_service = HistoricalQueryService(session)

    started = perf_counter()
    for _ in range(iterations):
        query_service.option_chain_at("SPY", datetime(2026, 1, 10, 10, 0, tzinfo=UTC))
    elapsed = perf_counter() - started

    session.close()
    return BenchmarkResult(name="option_chain_queries", elapsed_seconds=elapsed)


def _benchmark_quote_range_query(iterations: int) -> BenchmarkResult:
    session = _seed_query_dataset(iterations)
    query_service = HistoricalQueryService(session)

    started = perf_counter()
    for _ in range(iterations):
        query_service.quotes_by_contract_and_range(
            contract_id=1,
            start_ts=datetime(2026, 1, 1, 9, 30, tzinfo=UTC),
            end_ts=datetime(2026, 1, 20, 16, 0, tzinfo=UTC),
        )
    elapsed = perf_counter() - started

    session.close()
    return BenchmarkResult(name="quote_range_queries", elapsed_seconds=elapsed)


def _seed_query_dataset(iterations: int) -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = Session(engine)

    provider = DataProvider(
        id=1,
        name="bench",
        vendor="bench",
        description="benchmark",
        enabled=False,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    underlying = Underlying(id=1, symbol="SPY", name="SPY", currency="USD", active=True)
    manifest = DatasetManifest(
        id=1,
        provider_id=1,
        dataset_name="options",
        dataset_version="bench",
        schema_version="1.0",
        symbol_scope=["SPY"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        created_timestamp=datetime.now(tz=UTC),
        checksum="bench",
        row_count=iterations,
        source_metadata={"mode": "bench"},
    )
    contract = OptionContract(
        id=1,
        provider_id=1,
        provider_contract_id="SPY-C-500",
        underlying_id=1,
        option_root="SPY",
        occ_symbol="SPY260120C00500000",
        call_put="C",
        strike=Decimal("500"),
        expiration=date(2026, 1, 20),
        exercise_style="american",
        settlement_type="physical",
        multiplier=Decimal("100"),
        currency="USD",
        exchange_id=None,
        first_seen_at=datetime.now(tz=UTC),
        last_seen_at=datetime.now(tz=UTC),
        is_active=True,
    )
    session.add_all([provider, underlying, manifest, contract])
    session.flush()

    from backend.database.models import OptionQuote

    base_ts = datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    for index in range(iterations):
        quote_ts = base_ts + timedelta(minutes=index)
        session.add(
            OptionQuote(
                id=index + 1,
                contract_id=1,
                quote_timestamp=quote_ts,
                bid=Decimal("1.00"),
                ask=Decimal("1.10"),
                last=Decimal("1.05"),
                bid_size=10,
                ask_size=11,
                volume=100,
                open_interest=1000,
                implied_volatility=Decimal("0.2"),
                delta=Decimal("0.5"),
                gamma=Decimal("0.01"),
                theta=Decimal("-0.02"),
                vega=Decimal("0.15"),
                rho=Decimal("0.03"),
                underlying_price=Decimal("500"),
                provider_id=1,
                manifest_id=1,
            )
        )

    session.commit()
    return session
