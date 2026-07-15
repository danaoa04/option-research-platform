"""Historical query services with strict as-of no-look-ahead rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from backend.database.models import (
    CorporateAction,
    Dividend,
    EarningsEvent,
    InterestRateCurve,
    OptionContract,
    OptionQuote,
    Underlying,
    UnderlyingPrice,
    VolatilityObservation,
    VolatilityTimeSlice,
    VolatilityTimeSliceNode,
)


@dataclass(slots=True, frozen=True)
class AsOfQueryResult[T]:
    record: T | None
    exact_match: bool
    stale_age_seconds: float | None


class HistoricalQueryService:
    """Read-only query service for historical option and underlying data."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def option_chain_at(
        self,
        symbol: str,
        as_of: datetime,
        *,
        nearest_prior: bool = True,
    ) -> list[OptionQuote]:
        condition = (
            OptionQuote.quote_timestamp <= as_of
            if nearest_prior
            else OptionQuote.quote_timestamp == as_of
        )
        stmt: Select[tuple[OptionQuote]] = (
            select(OptionQuote)
            .join(OptionContract, OptionQuote.contract_id == OptionContract.id)
            .join(Underlying, OptionContract.underlying_id == Underlying.id)
            .where(Underlying.symbol == symbol, condition)
            .order_by(OptionQuote.quote_timestamp.desc())
        )
        quotes = list(self.session.execute(stmt).scalars())
        if not nearest_prior:
            return quotes

        # For nearest-prior mode, keep only records from the latest timestamp <= as_of.
        if not quotes:
            return []
        latest_ts = quotes[0].quote_timestamp
        return [quote for quote in quotes if quote.quote_timestamp == latest_ts]

    def contracts_by_symbol_and_expiration(
        self,
        symbol: str,
        expiration_start: date,
        expiration_end: date,
    ) -> list[OptionContract]:
        stmt: Select[tuple[OptionContract]] = (
            select(OptionContract)
            .join(Underlying, OptionContract.underlying_id == Underlying.id)
            .where(
                Underlying.symbol == symbol,
                OptionContract.expiration >= expiration_start,
                OptionContract.expiration <= expiration_end,
            )
            .order_by(OptionContract.expiration.asc(), OptionContract.strike.asc())
        )
        return list(self.session.execute(stmt).scalars())

    def quotes_by_contract_and_range(
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

    def nearest_quote(
        self,
        contract_id: int,
        as_of: datetime,
        *,
        exact_match: bool = False,
    ) -> AsOfQueryResult[OptionQuote]:
        condition = (
            OptionQuote.quote_timestamp == as_of
            if exact_match
            else OptionQuote.quote_timestamp <= as_of
        )
        stmt: Select[tuple[OptionQuote]] = (
            select(OptionQuote)
            .where(OptionQuote.contract_id == contract_id, condition)
            .order_by(OptionQuote.quote_timestamp.desc())
        )
        record = self.session.execute(stmt).scalars().first()
        if record is None:
            return AsOfQueryResult(record=None, exact_match=False, stale_age_seconds=None)

        record_ts = _ensure_timezone_aware(record.quote_timestamp)
        as_of_ts = _ensure_timezone_aware(as_of)

        is_exact = record_ts == as_of_ts
        stale_seconds = None
        if not is_exact:
            stale_seconds = max(0.0, (as_of_ts - record_ts).total_seconds())
        return AsOfQueryResult(record=record, exact_match=is_exact, stale_age_seconds=stale_seconds)

    def underlying_price_history(
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

    def dividends_by_range(
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

    def earnings_by_range(
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

    def corporate_actions_by_symbol(self, symbol: str) -> list[CorporateAction]:
        stmt: Select[tuple[CorporateAction]] = (
            select(CorporateAction)
            .join(Underlying, CorporateAction.underlying_id == Underlying.id)
            .where(Underlying.symbol == symbol)
            .order_by(CorporateAction.action_date.asc())
        )
        return list(self.session.execute(stmt).scalars())

    def interest_rate_curve_by_date(
        self,
        as_of_date: date,
        *,
        nearest_prior: bool = False,
    ) -> list[InterestRateCurve]:
        if nearest_prior:
            nearest_date_stmt: Select[tuple[date]] = (
                select(InterestRateCurve.as_of_date)
                .where(InterestRateCurve.as_of_date <= as_of_date)
                .order_by(InterestRateCurve.as_of_date.desc())
            )
            nearest_date = self.session.execute(nearest_date_stmt).scalars().first()
            if nearest_date is None:
                return []
            query_date = nearest_date
        else:
            query_date = as_of_date

        stmt: Select[tuple[InterestRateCurve]] = select(InterestRateCurve).where(
            InterestRateCurve.as_of_date == query_date
        )
        return list(self.session.execute(stmt).scalars())

    def smile_by_symbol_date_expiration(
        self,
        *,
        symbol: str,
        as_of: datetime,
        expiration: date,
        quality_filtered: bool = False,
        min_quality_score: float = 0.0,
    ) -> list[VolatilityObservation]:
        stmt: Select[tuple[VolatilityObservation]] = (
            select(VolatilityObservation)
            .where(
                VolatilityObservation.symbol == symbol,
                VolatilityObservation.expiration == expiration,
                VolatilityObservation.valuation_timestamp <= as_of,
            )
            .order_by(VolatilityObservation.valuation_timestamp.desc())
        )
        rows = list(self.session.execute(stmt).scalars())
        if not rows:
            return []
        latest_ts = rows[0].valuation_timestamp
        latest = [row for row in rows if row.valuation_timestamp == latest_ts]
        if quality_filtered:
            return [
                row
                for row in latest
                if row.quality_score is not None and float(row.quality_score) >= min_quality_score
            ]
        return latest

    def term_structure_by_symbol_date(
        self,
        *,
        symbol: str,
        as_of: datetime,
        min_quality_score: float | None = None,
    ) -> list[VolatilityObservation]:
        stmt: Select[tuple[VolatilityObservation]] = (
            select(VolatilityObservation)
            .where(
                VolatilityObservation.symbol == symbol,
                VolatilityObservation.valuation_timestamp <= as_of,
            )
            .order_by(
                VolatilityObservation.valuation_timestamp.desc(),
                VolatilityObservation.expiration.asc(),
            )
        )
        rows = list(self.session.execute(stmt).scalars())
        if not rows:
            return []
        latest_ts = rows[0].valuation_timestamp
        latest = [row for row in rows if row.valuation_timestamp == latest_ts]
        if min_quality_score is None:
            return latest
        return [
            row
            for row in latest
            if row.quality_score is not None and float(row.quality_score) >= min_quality_score
        ]

    def surface_by_symbol_timestamp(
        self,
        *,
        symbol: str,
        valuation_timestamp: datetime,
    ) -> VolatilityTimeSlice | None:
        stmt: Select[tuple[VolatilityTimeSlice]] = (
            select(VolatilityTimeSlice)
            .where(
                VolatilityTimeSlice.symbol == symbol,
                VolatilityTimeSlice.valuation_timestamp == valuation_timestamp,
                VolatilityTimeSlice.slice_kind == "surface",
                VolatilityTimeSlice.status == "finalized",
            )
            .order_by(VolatilityTimeSlice.created_at.desc())
        )
        return self.session.execute(stmt).scalars().first()

    def nearest_prior_valid_surface(
        self,
        *,
        symbol: str,
        as_of: datetime,
    ) -> VolatilityTimeSlice | None:
        stmt: Select[tuple[VolatilityTimeSlice]] = (
            select(VolatilityTimeSlice)
            .where(
                VolatilityTimeSlice.symbol == symbol,
                VolatilityTimeSlice.slice_kind == "surface",
                VolatilityTimeSlice.status == "finalized",
                VolatilityTimeSlice.valuation_timestamp <= as_of,
            )
            .order_by(VolatilityTimeSlice.valuation_timestamp.desc())
        )
        return self.session.execute(stmt).scalars().first()

    def historical_term_structure_series(
        self,
        *,
        symbol: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> list[VolatilityTimeSlice]:
        stmt: Select[tuple[VolatilityTimeSlice]] = (
            select(VolatilityTimeSlice)
            .where(
                VolatilityTimeSlice.symbol == symbol,
                VolatilityTimeSlice.slice_kind == "term_structure",
                VolatilityTimeSlice.status == "finalized",
                VolatilityTimeSlice.valuation_timestamp >= start_ts,
                VolatilityTimeSlice.valuation_timestamp <= end_ts,
            )
            .order_by(VolatilityTimeSlice.valuation_timestamp.asc())
        )
        return list(self.session.execute(stmt).scalars())

    def historical_regime_series(
        self,
        *,
        symbol: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> list[VolatilityTimeSlice]:
        stmt: Select[tuple[VolatilityTimeSlice]] = (
            select(VolatilityTimeSlice)
            .where(
                VolatilityTimeSlice.symbol == symbol,
                VolatilityTimeSlice.slice_kind == "regime",
                VolatilityTimeSlice.status == "finalized",
                VolatilityTimeSlice.valuation_timestamp >= start_ts,
                VolatilityTimeSlice.valuation_timestamp <= end_ts,
            )
            .order_by(VolatilityTimeSlice.valuation_timestamp.asc())
        )
        return list(self.session.execute(stmt).scalars())

    def historical_realized_volatility_series(
        self,
        *,
        symbol: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> list[VolatilityTimeSlice]:
        stmt: Select[tuple[VolatilityTimeSlice]] = (
            select(VolatilityTimeSlice)
            .where(
                VolatilityTimeSlice.symbol == symbol,
                VolatilityTimeSlice.slice_kind == "forward_curve",
                VolatilityTimeSlice.status == "finalized",
                VolatilityTimeSlice.valuation_timestamp >= start_ts,
                VolatilityTimeSlice.valuation_timestamp <= end_ts,
            )
            .order_by(VolatilityTimeSlice.valuation_timestamp.asc())
        )
        return list(self.session.execute(stmt).scalars())

    def surface_nodes(
        self,
        *,
        slice_row_id: int,
        node_kind: str | None = None,
    ) -> list[VolatilityTimeSliceNode]:
        stmt: Select[tuple[VolatilityTimeSliceNode]] = select(VolatilityTimeSliceNode).where(
            VolatilityTimeSliceNode.slice_id == slice_row_id
        )
        if node_kind is not None:
            stmt = stmt.where(VolatilityTimeSliceNode.node_kind == node_kind)
        stmt = stmt.order_by(
            VolatilityTimeSliceNode.tenor_days.asc(),
            VolatilityTimeSliceNode.x.asc(),
        )
        return list(self.session.execute(stmt).scalars())


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _ensure_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
