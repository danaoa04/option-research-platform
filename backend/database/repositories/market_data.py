"""Repository implementations for core market-data entities."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import (
    CorporateAction,
    DataLineageRecord,
    DatasetManifest,
    Dividend,
    EarningsEvent,
    InterestRateCurve,
    OptionContract,
    OptionQuote,
    UnderlyingPrice,
)

from .base import RepositoryBase


class ContractsRepository(RepositoryBase[OptionContract]):
    """Data access for option contracts with transaction-safe upserts."""

    def batch_upsert(self, contracts: Sequence[dict[str, object]]) -> None:
        if not contracts:
            return
        stmt = sqlite_insert(OptionContract).values(list(contracts))
        update_cols = {
            "underlying_id": stmt.excluded.underlying_id,
            "option_root": stmt.excluded.option_root,
            "occ_symbol": stmt.excluded.occ_symbol,
            "call_put": stmt.excluded.call_put,
            "strike": stmt.excluded.strike,
            "expiration": stmt.excluded.expiration,
            "exercise_style": stmt.excluded.exercise_style,
            "settlement_type": stmt.excluded.settlement_type,
            "multiplier": stmt.excluded.multiplier,
            "currency": stmt.excluded.currency,
            "exchange_id": stmt.excluded.exchange_id,
            "first_seen_at": stmt.excluded.first_seen_at,
            "last_seen_at": stmt.excluded.last_seen_at,
            "is_active": stmt.excluded.is_active,
        }
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[OptionContract.provider_id, OptionContract.provider_contract_id],
                set_=update_cols,
            )
        )

    def batch_insert_only(self, contracts: Sequence[dict[str, object]]) -> None:
        if not contracts:
            return
        stmt = sqlite_insert(OptionContract).values(list(contracts))
        self.session.execute(
            stmt.on_conflict_do_nothing(
                index_elements=[OptionContract.provider_id, OptionContract.provider_contract_id]
            )
        )

    def lookup_by_provider_contract(
        self, provider_id: int, provider_contract_id: str
    ) -> OptionContract | None:
        stmt: Select[tuple[OptionContract]] = select(OptionContract).where(
            OptionContract.provider_id == provider_id,
            OptionContract.provider_contract_id == provider_contract_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def query_by_expiration(
        self,
        underlying_id: int,
        start_date: date,
        end_date: date,
    ) -> list[OptionContract]:
        stmt: Select[tuple[OptionContract]] = select(OptionContract).where(
            OptionContract.underlying_id == underlying_id,
            OptionContract.expiration >= start_date,
            OptionContract.expiration <= end_date,
        )
        return list(self.session.execute(stmt).scalars())


class QuotesRepository(RepositoryBase[OptionQuote]):
    """Data access for option quotes with deterministic upsert behavior."""

    def batch_upsert(self, quotes: Sequence[dict[str, object]]) -> None:
        if not quotes:
            return
        stmt = sqlite_insert(OptionQuote).values(list(quotes))
        update_cols = {
            "bid": stmt.excluded.bid,
            "ask": stmt.excluded.ask,
            "last": stmt.excluded.last,
            "bid_size": stmt.excluded.bid_size,
            "ask_size": stmt.excluded.ask_size,
            "volume": stmt.excluded.volume,
            "open_interest": stmt.excluded.open_interest,
            "implied_volatility": stmt.excluded.implied_volatility,
            "delta": stmt.excluded.delta,
            "gamma": stmt.excluded.gamma,
            "theta": stmt.excluded.theta,
            "vega": stmt.excluded.vega,
            "rho": stmt.excluded.rho,
            "underlying_price": stmt.excluded.underlying_price,
        }
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    OptionQuote.contract_id,
                    OptionQuote.quote_timestamp,
                    OptionQuote.provider_id,
                    OptionQuote.manifest_id,
                ],
                set_=update_cols,
            )
        )

    def batch_insert_only(self, quotes: Sequence[dict[str, object]]) -> None:
        if not quotes:
            return
        stmt = sqlite_insert(OptionQuote).values(list(quotes))
        self.session.execute(
            stmt.on_conflict_do_nothing(
                index_elements=[
                    OptionQuote.contract_id,
                    OptionQuote.quote_timestamp,
                    OptionQuote.provider_id,
                    OptionQuote.manifest_id,
                ]
            )
        )

    def query_range(
        self,
        contract_id: int,
        start_ts: datetime,
        end_ts: datetime,
    ) -> list[OptionQuote]:
        stmt: Select[tuple[OptionQuote]] = select(OptionQuote).where(
            OptionQuote.contract_id == contract_id,
            OptionQuote.quote_timestamp >= start_ts,
            OptionQuote.quote_timestamp <= end_ts,
        )
        return list(self.session.execute(stmt).scalars())

    def nearest_prior(self, contract_id: int, as_of: datetime) -> OptionQuote | None:
        stmt: Select[tuple[OptionQuote]] = (
            select(OptionQuote)
            .where(
                OptionQuote.contract_id == contract_id,
                OptionQuote.quote_timestamp <= as_of,
            )
            .order_by(OptionQuote.quote_timestamp.desc())
        )
        return self.session.execute(stmt).scalars().first()


class UnderlyingPricesRepository(RepositoryBase[UnderlyingPrice]):
    """Repository for underlying price observations."""

    def batch_upsert(self, prices: Sequence[dict[str, object]]) -> None:
        if not prices:
            return
        stmt = sqlite_insert(UnderlyingPrice).values(list(prices))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    UnderlyingPrice.underlying_id,
                    UnderlyingPrice.price_timestamp,
                    UnderlyingPrice.provider_id,
                    UnderlyingPrice.manifest_id,
                ],
                set_={"price": stmt.excluded.price},
            )
        )

    def query_range(
        self,
        underlying_id: int,
        start_ts: datetime,
        end_ts: datetime,
    ) -> list[UnderlyingPrice]:
        stmt: Select[tuple[UnderlyingPrice]] = select(UnderlyingPrice).where(
            UnderlyingPrice.underlying_id == underlying_id,
            UnderlyingPrice.price_timestamp >= start_ts,
            UnderlyingPrice.price_timestamp <= end_ts,
        )
        return list(self.session.execute(stmt).scalars())

    def nearest_prior(self, underlying_id: int, as_of: datetime) -> UnderlyingPrice | None:
        stmt: Select[tuple[UnderlyingPrice]] = (
            select(UnderlyingPrice)
            .where(
                UnderlyingPrice.underlying_id == underlying_id,
                UnderlyingPrice.price_timestamp <= as_of,
            )
            .order_by(UnderlyingPrice.price_timestamp.desc())
        )
        return self.session.execute(stmt).scalars().first()


class DividendsRepository(RepositoryBase[Dividend]):
    """Repository for dividend events."""

    def batch_upsert(self, dividends: Sequence[dict[str, object]]) -> None:
        if not dividends:
            return
        stmt = sqlite_insert(Dividend).values(list(dividends))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    Dividend.underlying_id,
                    Dividend.ex_date,
                    Dividend.provider_id,
                    Dividend.manifest_id,
                ],
                set_={
                    "pay_date": stmt.excluded.pay_date,
                    "amount": stmt.excluded.amount,
                    "currency": stmt.excluded.currency,
                },
            )
        )

    def query_range(
        self,
        underlying_id: int,
        start_date: date,
        end_date: date,
    ) -> list[Dividend]:
        stmt: Select[tuple[Dividend]] = select(Dividend).where(
            Dividend.underlying_id == underlying_id,
            Dividend.ex_date >= start_date,
            Dividend.ex_date <= end_date,
        )
        return list(self.session.execute(stmt).scalars())


class EarningsRepository(RepositoryBase[EarningsEvent]):
    """Repository for earnings events."""

    def batch_upsert(self, events: Sequence[dict[str, object]]) -> None:
        if not events:
            return
        stmt = sqlite_insert(EarningsEvent).values(list(events))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    EarningsEvent.underlying_id,
                    EarningsEvent.event_date,
                    EarningsEvent.provider_id,
                    EarningsEvent.manifest_id,
                ],
                set_={
                    "event_timestamp": stmt.excluded.event_timestamp,
                    "fiscal_period": stmt.excluded.fiscal_period,
                },
            )
        )

    def query_range(
        self,
        underlying_id: int,
        start_date: date,
        end_date: date,
    ) -> list[EarningsEvent]:
        stmt: Select[tuple[EarningsEvent]] = select(EarningsEvent).where(
            EarningsEvent.underlying_id == underlying_id,
            EarningsEvent.event_date >= start_date,
            EarningsEvent.event_date <= end_date,
        )
        return list(self.session.execute(stmt).scalars())


class CorporateActionsRepository(RepositoryBase[CorporateAction]):
    """Repository for corporate actions."""

    def batch_upsert(self, actions: Sequence[dict[str, object]]) -> None:
        if not actions:
            return
        stmt = sqlite_insert(CorporateAction).values(list(actions))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    CorporateAction.underlying_id,
                    CorporateAction.action_date,
                    CorporateAction.action_type,
                    CorporateAction.provider_id,
                    CorporateAction.manifest_id,
                ],
                set_={
                    "announcement_timestamp": stmt.excluded.announcement_timestamp,
                    "provider_action_id": stmt.excluded.provider_action_id,
                    "ratio": stmt.excluded.ratio,
                    "cash_amount": stmt.excluded.cash_amount,
                    "multiplier_after": stmt.excluded.multiplier_after,
                    "deliverable_after": stmt.excluded.deliverable_after,
                    "description": stmt.excluded.description,
                    "source_metadata": stmt.excluded.source_metadata,
                },
            )
        )

    def by_underlying(self, underlying_id: int) -> list[CorporateAction]:
        stmt: Select[tuple[CorporateAction]] = select(CorporateAction).where(
            CorporateAction.underlying_id == underlying_id
        )
        return list(self.session.execute(stmt).scalars())


class InterestRatesRepository(RepositoryBase[InterestRateCurve]):
    """Repository for interest rate curves."""

    def batch_upsert(self, rates: Sequence[dict[str, object]]) -> None:
        if not rates:
            return
        stmt = sqlite_insert(InterestRateCurve).values(list(rates))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    InterestRateCurve.provider_id,
                    InterestRateCurve.manifest_id,
                    InterestRateCurve.as_of_date,
                    InterestRateCurve.tenor_days,
                ],
                set_={"rate": stmt.excluded.rate},
            )
        )

    def query_by_date(self, as_of_date: date) -> list[InterestRateCurve]:
        stmt: Select[tuple[InterestRateCurve]] = select(InterestRateCurve).where(
            InterestRateCurve.as_of_date == as_of_date
        )
        return list(self.session.execute(stmt).scalars())


class ManifestsLineageRepository(RepositoryBase[DatasetManifest]):
    """Repository for manifests and lineage records."""

    def batch_upsert_manifests(self, manifests: Sequence[dict[str, object]]) -> None:
        if not manifests:
            return
        stmt = sqlite_insert(DatasetManifest).values(list(manifests))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    DatasetManifest.provider_id,
                    DatasetManifest.dataset_name,
                    DatasetManifest.dataset_version,
                ],
                set_={
                    "schema_version": stmt.excluded.schema_version,
                    "symbol_scope": stmt.excluded.symbol_scope,
                    "start_date": stmt.excluded.start_date,
                    "end_date": stmt.excluded.end_date,
                    "created_timestamp": stmt.excluded.created_timestamp,
                    "checksum": stmt.excluded.checksum,
                    "row_count": stmt.excluded.row_count,
                    "source_metadata": stmt.excluded.source_metadata,
                },
            )
        )

    def batch_insert_only_manifests(self, manifests: Sequence[dict[str, object]]) -> None:
        if not manifests:
            return
        stmt = sqlite_insert(DatasetManifest).values(list(manifests))
        self.session.execute(
            stmt.on_conflict_do_nothing(
                index_elements=[
                    DatasetManifest.provider_id,
                    DatasetManifest.dataset_name,
                    DatasetManifest.dataset_version,
                ]
            )
        )

    def insert_lineage(self, lineage_records: Sequence[dict[str, object]]) -> None:
        if not lineage_records:
            return
        stmt = sqlite_insert(DataLineageRecord).values(list(lineage_records))
        self.session.execute(stmt)

    def lookup_manifest(
        self,
        provider_id: int,
        dataset_name: str,
        dataset_version: str,
    ) -> DatasetManifest | None:
        stmt: Select[tuple[DatasetManifest]] = select(DatasetManifest).where(
            DatasetManifest.provider_id == provider_id,
            DatasetManifest.dataset_name == dataset_name,
            DatasetManifest.dataset_version == dataset_version,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def lineage_for_manifest(self, manifest_id: int) -> list[DataLineageRecord]:
        stmt: Select[tuple[DataLineageRecord]] = select(DataLineageRecord).where(
            DataLineageRecord.manifest_id == manifest_id
        )
        return list(self.session.execute(stmt).scalars())


def decimal_or_none(value: str | None) -> Decimal | None:
    """Helper used by tests and loaders for optional decimals."""
    if value is None:
        return None
    return Decimal(value)
