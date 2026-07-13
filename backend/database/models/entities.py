"""Core SQLAlchemy ORM models for historical options database foundation."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class DataProvider(Base):
    __tablename__ = "data_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    vendor: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DatasetManifest(Base):
    __tablename__ = "dataset_manifests"
    __table_args__ = (
        UniqueConstraint("provider_id", "dataset_name", "dataset_version"),
        Index("ix_dataset_manifests_provider_version", "provider_id", "dataset_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol_scope: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    provider: Mapped[DataProvider] = relationship()


class Underlying(Base):
    __tablename__ = "underlyings"
    __table_args__ = (Index("ix_underlyings_symbol", "symbol"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Exchange(Base):
    __tablename__ = "exchanges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")


class TradingCalendar(Base):
    __tablename__ = "trading_calendar"
    __table_args__ = (
        UniqueConstraint("exchange_id", "trade_date"),
        Index("ix_trading_calendar_exchange_date", "exchange_id", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_trading_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    market_open_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    market_close_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    exchange: Mapped[Exchange] = relationship()


class OptionContract(Base):
    __tablename__ = "option_contracts"
    __table_args__ = (
        UniqueConstraint("provider_id", "provider_contract_id"),
        CheckConstraint("strike >= 0", name="option_contract_strike_non_negative"),
        CheckConstraint("multiplier > 0", name="option_contract_multiplier_positive"),
        Index("ix_option_contracts_occ_symbol", "occ_symbol"),
        Index("ix_option_contracts_underlying_expiration", "underlying_id", "expiration"),
        Index("ix_option_contracts_provider_contract", "provider_id", "provider_contract_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    provider_contract_id: Mapped[str] = mapped_column(String(128), nullable=False)
    underlying_id: Mapped[int] = mapped_column(ForeignKey("underlyings.id"), nullable=False)
    option_root: Mapped[str] = mapped_column(String(32), nullable=False)
    occ_symbol: Mapped[str | None] = mapped_column(String(64), nullable=True)
    call_put: Mapped[str] = mapped_column(String(4), nullable=False)
    strike: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    expiration: Mapped[date] = mapped_column(Date, nullable=False)
    exercise_style: Mapped[str] = mapped_column(String(16), nullable=False)
    settlement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    multiplier: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), nullable=False, default=Decimal("100")
    )
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    exchange_id: Mapped[int | None] = mapped_column(ForeignKey("exchanges.id"), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    provider: Mapped[DataProvider] = relationship()
    underlying: Mapped[Underlying] = relationship()
    exchange: Mapped[Exchange | None] = relationship()


class OptionQuote(Base):
    __tablename__ = "option_quotes"
    __table_args__ = (
        UniqueConstraint("contract_id", "quote_timestamp", "provider_id", "manifest_id"),
        CheckConstraint("bid >= 0", name="option_quote_bid_non_negative"),
        CheckConstraint("ask >= 0", name="option_quote_ask_non_negative"),
        CheckConstraint("last >= 0", name="option_quote_last_non_negative"),
        CheckConstraint(
            "bid IS NULL OR ask IS NULL OR bid <= ask",
            name="option_quote_bid_lte_ask",
        ),
        CheckConstraint("bid_size >= 0", name="option_quote_bid_size_non_negative"),
        CheckConstraint("ask_size >= 0", name="option_quote_ask_size_non_negative"),
        CheckConstraint("volume >= 0", name="option_quote_volume_non_negative"),
        CheckConstraint("open_interest >= 0", name="option_quote_open_interest_non_negative"),
        CheckConstraint(
            "implied_volatility IS NULL OR implied_volatility >= 0",
            name="option_quote_iv_non_negative",
        ),
        CheckConstraint(
            "underlying_price IS NULL OR underlying_price >= 0",
            name="option_quote_underlying_price_non_negative",
        ),
        Index("ix_option_quotes_contract_timestamp", "contract_id", "quote_timestamp"),
        Index("ix_option_quotes_provider_timestamp", "provider_id", "quote_timestamp"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("option_contracts.id"), nullable=False)
    quote_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bid: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    ask: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    last: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    bid_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ask_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    open_interest: Mapped[int | None] = mapped_column(Integer, nullable=True)
    implied_volatility: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    delta: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    gamma: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    theta: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    vega: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    rho: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    underlying_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    manifest_id: Mapped[int] = mapped_column(ForeignKey("dataset_manifests.id"), nullable=False)

    contract: Mapped[OptionContract] = relationship()
    provider: Mapped[DataProvider] = relationship()
    manifest: Mapped[DatasetManifest] = relationship()


class UnderlyingPrice(Base):
    __tablename__ = "underlying_prices"
    __table_args__ = (
        UniqueConstraint("underlying_id", "price_timestamp", "provider_id", "manifest_id"),
        CheckConstraint("price >= 0", name="underlying_price_non_negative"),
        Index("ix_underlying_prices_symbol_timestamp", "underlying_id", "price_timestamp"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    underlying_id: Mapped[int] = mapped_column(ForeignKey("underlyings.id"), nullable=False)
    price_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    manifest_id: Mapped[int] = mapped_column(ForeignKey("dataset_manifests.id"), nullable=False)


class Dividend(Base):
    __tablename__ = "dividends"
    __table_args__ = (
        UniqueConstraint("underlying_id", "ex_date", "provider_id", "manifest_id"),
        CheckConstraint("amount >= 0", name="dividend_amount_non_negative"),
        Index("ix_dividends_underlying_ex_date", "underlying_id", "ex_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    underlying_id: Mapped[int] = mapped_column(ForeignKey("underlyings.id"), nullable=False)
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    pay_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    manifest_id: Mapped[int] = mapped_column(ForeignKey("dataset_manifests.id"), nullable=False)


class EarningsEvent(Base):
    __tablename__ = "earnings_events"
    __table_args__ = (
        UniqueConstraint("underlying_id", "event_date", "provider_id", "manifest_id"),
        Index("ix_earnings_events_underlying_event_date", "underlying_id", "event_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    underlying_id: Mapped[int] = mapped_column(ForeignKey("underlyings.id"), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fiscal_period: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    manifest_id: Mapped[int] = mapped_column(ForeignKey("dataset_manifests.id"), nullable=False)


class CorporateAction(Base):
    __tablename__ = "corporate_actions"
    __table_args__ = (
        UniqueConstraint(
            "underlying_id",
            "action_date",
            "action_type",
            "provider_id",
            "manifest_id",
        ),
        Index("ix_corporate_actions_underlying_action_date", "underlying_id", "action_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    underlying_id: Mapped[int] = mapped_column(ForeignKey("underlyings.id"), nullable=False)
    action_date: Mapped[date] = mapped_column(Date, nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    manifest_id: Mapped[int] = mapped_column(ForeignKey("dataset_manifests.id"), nullable=False)


class InterestRateCurve(Base):
    __tablename__ = "interest_rate_curves"
    __table_args__ = (
        UniqueConstraint("provider_id", "manifest_id", "as_of_date", "tenor_days"),
        CheckConstraint("tenor_days >= 0", name="interest_rate_curve_tenor_non_negative"),
        Index("ix_interest_rate_curves_as_of_date", "as_of_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    manifest_id: Mapped[int] = mapped_column(ForeignKey("dataset_manifests.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    tenor_days: Mapped[int] = mapped_column(Integer, nullable=False)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)


class DataLineageRecord(Base):
    __tablename__ = "data_lineage_records"
    __table_args__ = (
        Index("ix_data_lineage_manifest", "manifest_id"),
        Index("ix_data_lineage_provider_imported", "provider_id", "imported_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    manifest_id: Mapped[int] = mapped_column(ForeignKey("dataset_manifests.id"), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    transformation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    software_version: Mapped[str] = mapped_column(String(64), nullable=False)

    provider: Mapped[DataProvider] = relationship()
    manifest: Mapped[DatasetManifest] = relationship()
