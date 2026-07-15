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
    announcement_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_action_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    cash_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    multiplier_after: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    deliverable_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
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


class VolatilityObservation(Base):
    __tablename__ = "volatility_observations"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "valuation_timestamp",
            "expiration",
            "strike",
            "option_type",
            "quote_source",
            "pricing_model",
            "manifest_id",
        ),
        CheckConstraint("strike >= 0", name="vol_obs_strike_non_negative"),
        CheckConstraint(
            "implied_volatility >= 0",
            name="vol_obs_iv_non_negative",
        ),
        CheckConstraint("moneyness >= 0", name="vol_obs_moneyness_non_negative"),
        Index(
            "ix_vol_obs_symbol_ts_exp",
            "symbol",
            "valuation_timestamp",
            "expiration",
        ),
        Index("ix_vol_obs_symbol_quality", "symbol", "quality_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    valuation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expiration: Mapped[date] = mapped_column(Date, nullable=False)
    strike: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    option_type: Mapped[str] = mapped_column(String(8), nullable=False)
    moneyness: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    forward_moneyness: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    delta: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    implied_volatility: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    quote_source: Mapped[str] = mapped_column(String(16), nullable=False)
    pricing_model: Mapped[str] = mapped_column(String(64), nullable=False)
    solver_method: Mapped[str] = mapped_column(String(32), nullable=False)
    solver_status: Mapped[str] = mapped_column(String(32), nullable=False)
    pricing_error: Mapped[Decimal | None] = mapped_column(Numeric(20, 12), nullable=True)
    bid: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    ask: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    midpoint: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    spread_width: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    open_interest: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stale_age_seconds: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    vega: Mapped[Decimal | None] = mapped_column(Numeric(20, 12), nullable=True)
    tree_sensitivity: Mapped[Decimal | None] = mapped_column(Numeric(20, 12), nullable=True)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    quality_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    contract_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    solver_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    manifest_id: Mapped[int] = mapped_column(ForeignKey("dataset_manifests.id"), nullable=False)

    manifest: Mapped[DatasetManifest] = relationship()


class VolatilityTimeSlice(Base):
    __tablename__ = "volatility_time_slices"
    __table_args__ = (
        UniqueConstraint("slice_id"),
        Index("ix_vol_slices_symbol_ts", "symbol", "valuation_timestamp"),
        Index("ix_vol_slices_kind_status", "slice_kind", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slice_id: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    valuation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    slice_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    input_manifests: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    solver_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    filtering_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    interpolation_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    tree_step_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    quality_thresholds: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False)
    excluded_observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    checksums: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    git_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parent_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_snapshots.id"),
        nullable=True,
    )


class VolatilityTimeSliceNode(Base):
    __tablename__ = "volatility_time_slice_nodes"
    __table_args__ = (
        UniqueConstraint("slice_id", "tenor_days", "x", "node_kind"),
        Index("ix_vol_slice_nodes_slice", "slice_id", "node_kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slice_id: Mapped[int] = mapped_column(ForeignKey("volatility_time_slices.id"), nullable=False)
    tenor_days: Mapped[int] = mapped_column(Integer, nullable=False)
    x: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    implied_volatility: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    node_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    slice: Mapped[VolatilityTimeSlice] = relationship()


class ResearchRun(Base):
    __tablename__ = "research_runs"
    __table_args__ = (
        UniqueConstraint("run_id"),
        Index("ix_research_runs_symbol_ts", "symbol", "run_timestamp"),
        Index("ix_research_runs_quality", "quality_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(48), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    exit_date: Mapped[date] = mapped_column(Date, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    software_version: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_id: Mapped[int] = mapped_column(ForeignKey("dataset_manifests.id"), nullable=False)
    run_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checksums: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    summary_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata_json",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    manifest: Mapped[DatasetManifest] = relationship()


class ResearchOpportunity(Base):
    __tablename__ = "research_opportunities"
    __table_args__ = (
        UniqueConstraint("run_row_id", "as_of_timestamp"),
        Index("ix_research_opportunities_score", "opportunity_score"),
        Index("ix_research_opportunities_asof", "as_of_timestamp"),
        Index("ix_research_opportunities_regime", "term_structure_regime"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("research_runs.id"), nullable=False)
    as_of_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opportunity_score: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    historical_pop: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    expected_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    theta_capture: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    term_structure_regime: Mapped[str | None] = mapped_column(String(32), nullable=True)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    run: Mapped[ResearchRun] = relationship()


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"
    __table_args__ = (
        UniqueConstraint("run_id"),
        Index("ix_optimization_runs_problem_ts", "problem_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    problem_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(48), nullable=False)
    symbol_universe: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    historical_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    historical_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    optimization_problem: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    parameter_space: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    objective_definitions: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    candidate_ordering: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    pareto_front_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    winner_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    dataset_manifests: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    volatility_surface_snapshots: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    lifecycle_policies: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    pricing_model_policies: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    software_git_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    checksums: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    runtime_seconds: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    candidate_results: Mapped[list[OptimizationCandidateResult]] = relationship(
        "OptimizationCandidateResult",
        back_populates="run",
    )


class OptimizationCandidateResult(Base):
    __tablename__ = "optimization_candidate_results"
    __table_args__ = (
        UniqueConstraint("run_row_id", "candidate_id"),
        Index("ix_opt_candidate_results_run", "run_row_id", "candidate_id"),
        Index("ix_opt_candidate_results_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("optimization_runs.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    objective_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    constraint_results: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    lifecycle_outcomes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    regime_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    calibration_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    data_quality_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    runtime_seconds: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    lexicographic_tuple: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    dominated_by: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reproducibility_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    run: Mapped[OptimizationRun] = relationship(back_populates="candidate_results")


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


class RawVendorRecord(Base):
    __tablename__ = "raw_vendor_records"
    __table_args__ = (
        UniqueConstraint("provider_id", "entity_type", "provider_record_id", "checksum"),
        Index("ix_raw_vendor_records_provider_entity", "provider_id", "entity_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class NormalizedCorporateAction(Base):
    __tablename__ = "normalized_corporate_actions"
    __table_args__ = (
        UniqueConstraint("provider_id", "provider_action_id"),
        Index(
            "ix_normalized_corp_actions_underlying_effective",
            "underlying_id",
            "effective_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_record_id: Mapped[int] = mapped_column(ForeignKey("raw_vendor_records.id"), nullable=False)
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    manifest_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataset_manifests.id"),
        nullable=True,
    )
    underlying_id: Mapped[int] = mapped_column(ForeignKey("underlyings.id"), nullable=False)
    provider_action_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    announcement_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    cash_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    multiplier_after: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    deliverable_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    normalized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SymbolHistory(Base):
    __tablename__ = "symbol_history"
    __table_args__ = (
        UniqueConstraint("underlying_id", "old_symbol", "new_symbol", "effective_date"),
        Index("ix_symbol_history_old_symbol", "old_symbol"),
        Index("ix_symbol_history_new_symbol", "new_symbol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    underlying_id: Mapped[int] = mapped_column(ForeignKey("underlyings.id"), nullable=False)
    old_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    new_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    announcement_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    source_action_id: Mapped[int | None] = mapped_column(
        ForeignKey("normalized_corporate_actions.id"),
        nullable=True,
    )
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class AdjustedUnderlyingPriceView(Base):
    __tablename__ = "adjusted_underlying_price_views"
    __table_args__ = (
        UniqueConstraint("underlying_id", "price_timestamp", "view_name", "policy_name"),
        CheckConstraint("base_price >= 0", name="adjusted_view_base_price_non_negative"),
        CheckConstraint("adjusted_price >= 0", name="adjusted_view_adjusted_price_non_negative"),
        Index(
            "ix_adjusted_underlying_views_lookup",
            "underlying_id",
            "view_name",
            "price_timestamp",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    underlying_id: Mapped[int] = mapped_column(ForeignKey("underlyings.id"), nullable=False)
    source_price_id: Mapped[int | None] = mapped_column(
        ForeignKey("underlying_prices.id"),
        nullable=True,
    )
    source_action_id: Mapped[int | None] = mapped_column(
        ForeignKey("normalized_corporate_actions.id"),
        nullable=True,
    )
    view_name: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    price_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    adjusted_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    adjustment_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class AdjustedOptionContractView(Base):
    __tablename__ = "adjusted_option_contract_views"
    __table_args__ = (
        UniqueConstraint("contract_id", "as_of_date", "view_name", "policy_name"),
        CheckConstraint(
            "adjusted_multiplier > 0",
            name="adjusted_contract_multiplier_positive",
        ),
        CheckConstraint("adjusted_strike >= 0", name="adjusted_contract_strike_non_negative"),
        Index("ix_adjusted_option_views_contract", "contract_id", "as_of_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("option_contracts.id"), nullable=False)
    source_action_id: Mapped[int | None] = mapped_column(
        ForeignKey("normalized_corporate_actions.id"),
        nullable=True,
    )
    view_name: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    adjusted_strike: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    adjusted_multiplier: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    deliverable_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    adjustment_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class DatasetSnapshot(Base):
    __tablename__ = "dataset_snapshots"
    __table_args__ = (
        Index("ix_dataset_snapshots_manifest", "manifest_id"),
        Index("ix_dataset_snapshots_provider_created", "provider_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    manifest_id: Mapped[int] = mapped_column(ForeignKey("dataset_manifests.id"), nullable=False)
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    git_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    date_start: Mapped[date] = mapped_column(Date, nullable=False)
    date_end: Mapped[date] = mapped_column(Date, nullable=False)
    symbol_scope: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    row_counts: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    checksums: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    transformation_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    validation_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parent_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_snapshots.id"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")


class SnapshotSourceManifest(Base):
    __tablename__ = "snapshot_source_manifests"
    __table_args__ = (UniqueConstraint("snapshot_id", "source_manifest_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("dataset_snapshots.id"), nullable=False)
    source_manifest_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_manifests.id"),
        nullable=False,
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_type_ts", "event_type", "event_timestamp"),
        Index("ix_audit_events_snapshot", "snapshot_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("data_providers.id"), nullable=True)
    manifest_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataset_manifests.id"),
        nullable=True,
    )
    snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_snapshots.id"),
        nullable=True,
    )
    correlation_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
