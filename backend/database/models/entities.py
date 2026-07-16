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


class ValidationRun(Base):
    __tablename__ = "validation_runs"
    __table_args__ = (
        UniqueConstraint("run_id"),
        Index("ix_validation_runs_strategy_ts", "strategy_name", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    candidate_ordering: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    validation_configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    cpcv_definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    comparison_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    checksums: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    failures: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    software_git_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    candidate_results: Mapped[list[ValidationCandidateResult]] = relationship(
        "ValidationCandidateResult",
        back_populates="run",
    )
    folds: Mapped[list[ValidationFold]] = relationship(
        "ValidationFold",
        back_populates="run",
    )


class ValidationCandidateResult(Base):
    __tablename__ = "validation_candidate_results"
    __table_args__ = (
        UniqueConstraint("run_row_id", "candidate_id"),
        Index("ix_validation_candidate_results_run", "run_row_id", "candidate_id"),
        Index("ix_validation_candidate_results_tier", "tier"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("validation_runs.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    deflated_sharpe: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    pbo: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    cpcv: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sensitivity: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    neighborhood: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    degradation: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    regime_robustness: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    temporal_stability: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    stress_test: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    bootstrap: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    robustness_score: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    gate_result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    failures: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reproducibility_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    run: Mapped[ValidationRun] = relationship(back_populates="candidate_results")


class ValidationFold(Base):
    __tablename__ = "validation_folds"
    __table_args__ = (
        UniqueConstraint("run_row_id", "split_id"),
        Index("ix_validation_folds_run", "run_row_id", "split_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("validation_runs.id"), nullable=False)
    split_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fold_index: Mapped[int] = mapped_column(Integer, nullable=False)
    split_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    selection_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    run: Mapped[ValidationRun] = relationship(back_populates="folds")


class PortfolioRun(Base):
    __tablename__ = "portfolio_runs"
    __table_args__ = (
        UniqueConstraint("run_id"),
        Index("ix_portfolio_runs_strategy_ts", "strategy_name", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    problem_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    allocation_problem: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    objectives_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    constraints_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    correlation_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sizing_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rebalance_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    eligible_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    allocation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reserve_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    available_capital: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    checksums: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    software_git_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dataset_manifests: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    failures: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortfolioEligibleCandidateRecord(Base):
    __tablename__ = "portfolio_eligible_candidates"
    __table_args__ = (
        UniqueConstraint("run_row_id", "candidate_id"),
        Index("ix_portfolio_eligible_run", "run_row_id", "candidate_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("portfolio_runs.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    validation_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    exposure_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    stats_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    returns: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    pnl: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)


class PortfolioRejectedCandidateRecord(Base):
    __tablename__ = "portfolio_rejected_candidates"
    __table_args__ = (
        UniqueConstraint("run_row_id", "candidate_id"),
        Index("ix_portfolio_rejected_run", "run_row_id", "candidate_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("portfolio_runs.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rejection_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class PortfolioAllocationRecord(Base):
    __tablename__ = "portfolio_allocations"
    __table_args__ = (
        UniqueConstraint("run_row_id", "candidate_id"),
        Index("ix_portfolio_allocations_run", "run_row_id", "candidate_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("portfolio_runs.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    capital: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    contracts: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)


class PortfolioConstraintRecord(Base):
    __tablename__ = "portfolio_constraint_outcomes"
    __table_args__ = (
        UniqueConstraint("run_row_id", "constraint_name", "candidate_id"),
        Index("ix_portfolio_constraints_run", "run_row_id", "constraint_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("portfolio_runs.id"), nullable=False)
    constraint_name: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    observed: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class PortfolioCorrelationRecord(Base):
    __tablename__ = "portfolio_correlations"
    __table_args__ = (
        UniqueConstraint("run_row_id", "left_id", "right_id", "kind"),
        Index("ix_portfolio_correlations_run", "run_row_id", "kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("portfolio_runs.id"), nullable=False)
    left_id: Mapped[str] = mapped_column(String(128), nullable=False)
    right_id: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    uncertainty: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    effective_sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sparse_warning: Mapped[bool] = mapped_column(Boolean, nullable=False)


class PortfolioClusterRecord(Base):
    __tablename__ = "portfolio_clusters"
    __table_args__ = (
        UniqueConstraint("run_row_id", "candidate_id"),
        Index("ix_portfolio_clusters_run", "run_row_id", "cluster_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("portfolio_runs.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    cluster_id: Mapped[str] = mapped_column(String(256), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class PortfolioRiskContributionRecord(Base):
    __tablename__ = "portfolio_risk_contributions"
    __table_args__ = (
        UniqueConstraint("run_row_id", "candidate_id"),
        Index("ix_portfolio_risk_contrib_run", "run_row_id", "candidate_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("portfolio_runs.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    contribution_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PortfolioScenarioRecord(Base):
    __tablename__ = "portfolio_scenarios"
    __table_args__ = (
        UniqueConstraint("run_row_id", "scenario_name"),
        Index("ix_portfolio_scenarios_run", "run_row_id", "scenario_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("portfolio_runs.id"), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(128), nullable=False)
    portfolio_return: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    portfolio_drawdown: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    expected_shortfall: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class PortfolioRebalancePlanRecord(Base):
    __tablename__ = "portfolio_rebalance_plans"
    __table_args__ = (
        UniqueConstraint("run_row_id", "candidate_id"),
        Index("ix_portfolio_rebalance_run", "run_row_id", "as_of_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("portfolio_runs.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    previous_weight: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    delta_weight: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (
        UniqueConstraint("run_id"),
        Index("ix_backtest_runs_strategy_ts", "strategy_name", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    configuration_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reproducibility_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    checksums: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    software_git_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestEventRecord(Base):
    __tablename__ = "backtest_events"
    __table_args__ = (
        UniqueConstraint("run_row_id", "sequence_number", "event_type"),
        Index("ix_backtest_events_run_ts", "run_row_id", "event_timestamp"),
        Index("ix_backtest_events_type", "event_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manifest_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    software_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checksum_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestOrderIntentRecord(Base):
    __tablename__ = "backtest_order_intents"
    __table_args__ = (
        UniqueConstraint("run_row_id", "intent_id"),
        Index("ix_backtest_order_intents_run_ts", "run_row_id", "requested_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    intent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    price_policy: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestResearchFillRecord(Base):
    __tablename__ = "backtest_research_fills"
    __table_args__ = (
        UniqueConstraint("run_row_id", "intent_id"),
        Index("ix_backtest_research_fills_run_ts", "run_row_id", "fill_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    intent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fill_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    filled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fill_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestPositionRecord(Base):
    __tablename__ = "backtest_positions"
    __table_args__ = (
        UniqueConstraint("run_row_id", "position_id", "as_of_timestamp"),
        Index("ix_backtest_positions_run_ts", "run_row_id", "as_of_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    as_of_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestPositionLegRecord(Base):
    __tablename__ = "backtest_position_legs"
    __table_args__ = (
        UniqueConstraint("run_row_id", "position_id", "leg_id", "as_of_timestamp"),
        Index("ix_backtest_position_legs_run_ts", "run_row_id", "as_of_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    leg_id: Mapped[str] = mapped_column(String(128), nullable=False)
    contract_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    strike: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    expiration: Mapped[date | None] = mapped_column(Date, nullable=True)
    option_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    exercise_style: Mapped[str | None] = mapped_column(String(16), nullable=True)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    implied_volatility: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    realised_volatility: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    capital_usage: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    data_quality_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    as_of_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestValuationRecord(Base):
    __tablename__ = "backtest_valuations"
    __table_args__ = (
        UniqueConstraint("run_row_id", "valuation_timestamp", "position_id", "leg_id"),
        Index("ix_backtest_valuations_run_ts", "run_row_id", "valuation_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    valuation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    leg_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mark_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    market_source: Mapped[str] = mapped_column(String(64), nullable=False)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestCashLedgerEntryRecord(Base):
    __tablename__ = "backtest_cash_ledger_entries"
    __table_args__ = (
        UniqueConstraint("run_row_id", "entry_index"),
        Index("ix_backtest_cash_ledger_run_ts", "run_row_id", "entry_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    entry_index: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestPortfolioSnapshotRecord(Base):
    __tablename__ = "backtest_portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint("run_row_id", "snapshot_timestamp"),
        Index("ix_backtest_snapshots_run_ts", "run_row_id", "snapshot_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    snapshot_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    reserved_capital: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    accrued_fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    dividends: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    portfolio_greeks: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    portfolio_exposure: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    capital_utilization: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)


class BacktestLifecycleTriggerRecord(Base):
    __tablename__ = "backtest_lifecycle_triggers"
    __table_args__ = (
        UniqueConstraint("run_row_id", "trigger_timestamp", "position_id", "trigger"),
        Index("ix_backtest_lifecycle_run_ts", "run_row_id", "trigger_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    trigger_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    information_set: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestRunComparisonRecord(Base):
    __tablename__ = "backtest_run_comparisons"
    __table_args__ = (
        UniqueConstraint("left_run_id", "right_run_id", "comparison_key_checksum"),
        Index("ix_backtest_run_comparisons_pair", "left_run_id", "right_run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    left_run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    right_run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    comparison_key_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    comparison_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    chart_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestScenarioResultRecord(Base):
    __tablename__ = "backtest_scenario_results"
    __table_args__ = (
        UniqueConstraint("run_row_id", "scenario_name"),
        Index("ix_backtest_scenario_results_run", "run_row_id", "scenario_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(128), nullable=False)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class BacktestReproducibilityChecksumRecord(Base):
    __tablename__ = "backtest_reproducibility_checksums"
    __table_args__ = (
        UniqueConstraint("run_row_id", "checksum_key"),
        Index("ix_backtest_repro_checksums_run", "run_row_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    checksum_key: Mapped[str] = mapped_column(String(128), nullable=False)
    checksum_value: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestStrategyDefinitionRecord(Base):
    __tablename__ = "backtest_strategy_definitions"
    __table_args__ = (
        UniqueConstraint("definition_id"),
        Index("ix_backtest_strategy_definitions_name", "strategy_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    definition_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    definition_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    validation_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestStrategyTemplateRecord(Base):
    __tablename__ = "backtest_strategy_templates"
    __table_args__ = (
        UniqueConstraint("run_row_id", "template_name", "strategy_instance_id"),
        Index("ix_backtest_strategy_templates_run", "run_row_id", "template_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    template_name: Mapped[str] = mapped_column(String(128), nullable=False)
    template_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    compiled_definition_id: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class StrategyTemplateRegistryRecord(Base):
    __tablename__ = "strategy_template_registry"
    __table_args__ = (
        UniqueConstraint("canonical_identifier"),
        Index("ix_strategy_template_registry_family", "strategy_family", "strategy_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_family: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(48), nullable=False)
    supported_underlyings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    supported_exercise_styles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    supported_settlement_styles: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    supported_account_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    required_data: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    supported_lifecycle_policies: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    supported_roll_policies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    known_limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    deprecated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    replacement_identifier: Mapped[str | None] = mapped_column(String(160), nullable=True)
    plugin_namespace: Mapped[str | None] = mapped_column(String(160), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyTemplateVersionRecord(Base):
    __tablename__ = "strategy_template_versions"
    __table_args__ = (
        UniqueConstraint("canonical_identifier", "template_version"),
        Index("ix_strategy_template_versions_id", "canonical_identifier", "template_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    template_version: Mapped[str] = mapped_column(String(48), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(48), nullable=False)
    parameter_version: Mapped[str] = mapped_column(String(48), nullable=False)
    definition_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    migration_hook: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyTemplateAliasRecord(Base):
    __tablename__ = "strategy_template_aliases"
    __table_args__ = (
        UniqueConstraint("alias"),
        Index("ix_strategy_template_aliases_identifier", "canonical_identifier", "alias"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    alias: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyParameterSchemaRecord(Base):
    __tablename__ = "strategy_parameter_schemas"
    __table_args__ = (
        UniqueConstraint("canonical_identifier", "template_version"),
        Index(
            "ix_strategy_parameter_schemas_identifier", "canonical_identifier", "template_version"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    template_version: Mapped[str] = mapped_column(String(48), nullable=False)
    schema_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyDefinitionDocumentRecord(Base):
    __tablename__ = "strategy_definition_documents"
    __table_args__ = (
        UniqueConstraint("strategy_definition_id"),
        Index(
            "ix_strategy_definition_documents_template", "canonical_identifier", "template_version"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_definition_id: Mapped[str] = mapped_column(String(160), nullable=False)
    canonical_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    template_version: Mapped[str] = mapped_column(String(48), nullable=False)
    parameters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    reproducibility_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyDefinitionLegRecord(Base):
    __tablename__ = "strategy_definition_legs"
    __table_args__ = (
        UniqueConstraint("strategy_definition_id", "leg_label"),
        Index("ix_strategy_definition_legs_definition", "strategy_definition_id", "leg_label"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_definition_id: Mapped[str] = mapped_column(String(160), nullable=False)
    leg_label: Mapped[str] = mapped_column(String(120), nullable=False)
    leg_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_ratio: Mapped[int] = mapped_column(Integer, nullable=False)
    strike: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    expiration: Mapped[date | None] = mapped_column(Date, nullable=True)
    option_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class StrategyValidationResultRecord(Base):
    __tablename__ = "strategy_validation_results"
    __table_args__ = (
        UniqueConstraint("strategy_definition_id"),
        Index("ix_strategy_validation_results_status", "validation_status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_definition_id: Mapped[str] = mapped_column(String(160), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    errors_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    warnings_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyPayoffSummaryRecord(Base):
    __tablename__ = "strategy_payoff_summaries"
    __table_args__ = (
        UniqueConstraint("strategy_definition_id"),
        Index("ix_strategy_payoff_summaries_definition", "strategy_definition_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_definition_id: Mapped[str] = mapped_column(String(160), nullable=False)
    payoff_grid_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    maximum_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    maximum_loss: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    breakevens_json: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    defined_risk: Mapped[bool] = mapped_column(Boolean, nullable=False)
    capital_at_risk: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    credit_or_debit: Mapped[str] = mapped_column(String(16), nullable=False)
    slope_regions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    discontinuities_json: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=list)
    residual_exposure_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    assignment_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dividend_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False)
    warnings_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyRiskClassificationRecord(Base):
    __tablename__ = "strategy_risk_classifications"
    __table_args__ = (
        UniqueConstraint("canonical_identifier", "template_version"),
        Index(
            "ix_strategy_risk_classifications_identifier",
            "canonical_identifier",
            "template_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    template_version: Mapped[str] = mapped_column(String(48), nullable=False)
    risk_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyCompatibilityMetadataRecord(Base):
    __tablename__ = "strategy_compatibility_metadata"
    __table_args__ = (
        UniqueConstraint("canonical_identifier", "template_version"),
        Index("ix_strategy_compatibility_identifier", "canonical_identifier", "template_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    template_version: Mapped[str] = mapped_column(String(48), nullable=False)
    compatibility_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyOptimizerContractRecord(Base):
    __tablename__ = "strategy_optimizer_contracts"
    __table_args__ = (
        UniqueConstraint("canonical_identifier", "template_version"),
        Index(
            "ix_strategy_optimizer_contracts_identifier", "canonical_identifier", "template_version"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    template_version: Mapped[str] = mapped_column(String(48), nullable=False)
    contract_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyTemplateChecksumRecord(Base):
    __tablename__ = "strategy_template_checksums"
    __table_args__ = (
        UniqueConstraint("checksum_key"),
        Index("ix_strategy_template_checksums_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checksum_key: Mapped[str] = mapped_column(String(160), nullable=False)
    checksum_value: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyPolicyRegistryRecord(Base):
    __tablename__ = "strategy_policy_registry"
    __table_args__ = (
        UniqueConstraint("policy_id"),
        Index("ix_strategy_policy_registry_family", "policy_family", "policy_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(160), nullable=False)
    policy_name: Mapped[str] = mapped_column(String(160), nullable=False)
    policy_family: Mapped[str] = mapped_column(String(48), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(48), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    parameters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    required_data: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    supported_strategies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    deprecated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    replacement_policy_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyPolicyAliasRecord(Base):
    __tablename__ = "strategy_policy_aliases"
    __table_args__ = (
        UniqueConstraint("alias"),
        Index("ix_strategy_policy_aliases_policy", "policy_id", "alias"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(160), nullable=False)
    alias: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyPolicySetVersionRecord(Base):
    __tablename__ = "strategy_policy_set_versions"
    __table_args__ = (
        UniqueConstraint("set_id", "set_version"),
        Index(
            "ix_strategy_policy_set_versions_strategy",
            "strategy_identifier",
            "set_id",
            "set_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    set_id: Mapped[str] = mapped_column(String(160), nullable=False)
    set_version: Mapped[str] = mapped_column(String(48), nullable=False)
    strategy_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    conflict_mode: Mapped[str] = mapped_column(String(48), nullable=False)
    entry_policies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    exit_policies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    management_policies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    earnings_policies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    dividend_policies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    roll_policies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyPolicyEvaluationRecord(Base):
    __tablename__ = "strategy_policy_evaluations"
    __table_args__ = (
        UniqueConstraint("run_id", "evaluation_id"),
        Index("ix_strategy_policy_evaluations_run_ts", "run_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    evaluation_id: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    policy_set_id: Mapped[str] = mapped_column(String(160), nullable=False)
    policy_set_version: Mapped[str] = mapped_column(String(48), nullable=False)
    policy_id: Mapped[str] = mapped_column(String(160), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(48), nullable=False)
    policy_family: Mapped[str] = mapped_column(String(48), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    observed_values_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    thresholds_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    diagnostics_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    required_data_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    data_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class StrategyPolicyConflictRecord(Base):
    __tablename__ = "strategy_policy_conflicts"
    __table_args__ = (
        UniqueConstraint("run_id", "conflict_id"),
        Index("ix_strategy_policy_conflicts_run_ts", "run_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    conflict_id: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    policy_set_id: Mapped[str] = mapped_column(String(160), nullable=False)
    policy_set_version: Mapped[str] = mapped_column(String(48), nullable=False)
    conflict_mode: Mapped[str] = mapped_column(String(48), nullable=False)
    winning_policy_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    matched_signals_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    diagnostics: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyPolicyChecksumRecord(Base):
    __tablename__ = "strategy_policy_checksums"
    __table_args__ = (
        UniqueConstraint("checksum_key"),
        Index("ix_strategy_policy_checksums_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checksum_key: Mapped[str] = mapped_column(String(160), nullable=False)
    checksum_value: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RollPolicyRegistryRecord(Base):
    __tablename__ = "roll_policy_registry"
    __table_args__ = (
        UniqueConstraint("canonical_identifier"),
        Index("ix_roll_policy_registry_family", "default_priority", "canonical_identifier"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(48), nullable=False)
    aliases_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    supported_strategy_families: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    supported_lifecycle_states: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    supported_exercise_styles: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    supported_settlement_types: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    required_market_data: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    required_volatility_data: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    parameter_schema_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    default_priority: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    plugin_namespace: Mapped[str | None] = mapped_column(String(160), nullable=True)
    deprecated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    replacement_identifier: Mapped[str | None] = mapped_column(String(160), nullable=True)
    known_limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RollPolicyAliasRecord(Base):
    __tablename__ = "roll_policy_aliases"
    __table_args__ = (
        UniqueConstraint("alias"),
        Index("ix_roll_policy_aliases_identifier", "canonical_identifier", "alias"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    alias: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestRollRequestRecord(Base):
    __tablename__ = "backtest_roll_requests"
    __table_args__ = (
        UniqueConstraint("run_id", "request_id"),
        Index("ix_backtest_roll_requests_run_ts", "run_id", "requested_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(160), nullable=False)
    position_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    source_legs_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    preserved_legs_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    close_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    target_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    target_expiration_policy: Mapped[str] = mapped_column(String(128), nullable=False)
    target_strike_policy: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trigger: Mapped[str] = mapped_column(String(128), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestRollCandidateRecord(Base):
    __tablename__ = "backtest_roll_candidates"
    __table_args__ = (
        UniqueConstraint("run_id", "candidate_id"),
        Index("ix_backtest_roll_candidates_run", "run_id", "request_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str] = mapped_column(String(160), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(160), nullable=False)
    roll_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_legs_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    estimated_net_credit_or_debit: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
    )
    liquidity_score: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    quality_score: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestRollEligibilityRecord(Base):
    __tablename__ = "backtest_roll_eligibility_results"
    __table_args__ = (
        UniqueConstraint("run_id", "eligibility_id"),
        Index("ix_backtest_roll_eligibility_run", "run_id", "request_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str] = mapped_column(String(160), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(160), nullable=False)
    eligibility_id: Mapped[str] = mapped_column(String(160), nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rejections_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestRollExecutionRecord(Base):
    __tablename__ = "backtest_roll_executions"
    __table_args__ = (
        UniqueConstraint("run_id", "execution_id"),
        Index("ix_backtest_roll_executions_run", "run_id", "plan_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    execution_id: Mapped[str] = mapped_column(String(160), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(160), nullable=False)
    request_id: Mapped[str] = mapped_column(String(160), nullable=False)
    execution_style: Mapped[str] = mapped_column(String(64), nullable=False)
    all_or_none_research: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sequential_legging: Mapped[bool] = mapped_column(Boolean, nullable=False)
    requested_net_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestRollFillRecord(Base):
    __tablename__ = "backtest_roll_fills"
    __table_args__ = (
        UniqueConstraint("run_id", "execution_id", "fill_timestamp", "leg_label"),
        Index("ix_backtest_roll_fills_run_ts", "run_id", "fill_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    execution_id: Mapped[str] = mapped_column(String(160), nullable=False)
    leg_label: Mapped[str] = mapped_column(String(128), nullable=False)
    fill_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fill_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    fill_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    slippage: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestPartialRollStateRecord(Base):
    __tablename__ = "backtest_partial_roll_states"
    __table_args__ = (
        UniqueConstraint("run_id", "state_id"),
        Index("ix_backtest_partial_roll_states_run", "run_id", "plan_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    state_id: Mapped[str] = mapped_column(String(160), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(160), nullable=False)
    temporary_naked_exposure: Mapped[bool] = mapped_column(Boolean, nullable=False)
    residual_quantities_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    risk_escalated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    timeout_seconds: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestRollReconciliationRecord(Base):
    __tablename__ = "backtest_roll_reconciliations"
    __table_args__ = (
        UniqueConstraint("run_id", "reconciliation_id"),
        Index("ix_backtest_roll_reconciliations_run", "run_id", "plan_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reconciliation_id: Mapped[str] = mapped_column(String(160), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    retry_scheduled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cancel_scheduled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fallback_close_scheduled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    state_transition: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_temporary_exposure: Mapped[bool] = mapped_column(Boolean, nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestBasisTransferRecord(Base):
    __tablename__ = "backtest_basis_transfers"
    __table_args__ = (
        UniqueConstraint("run_id", "basis_transfer_id"),
        Index("ix_backtest_basis_transfers_run", "run_id", "plan_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    basis_transfer_id: Mapped[str] = mapped_column(String(160), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(160), nullable=False)
    original_basis: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cumulative_credits: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cumulative_debits: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    basis_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestConversionPlanRecord(Base):
    __tablename__ = "backtest_conversion_plans"
    __table_args__ = (
        UniqueConstraint("run_id", "conversion_id"),
        Index("ix_backtest_conversion_plans_run", "run_id", "strategy_instance_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    conversion_id: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(160), nullable=False)
    source_strategy: Mapped[str] = mapped_column(String(128), nullable=False)
    target_strategy: Mapped[str] = mapped_column(String(128), nullable=False)
    legs_closed_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    legs_preserved_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    legs_opened_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    conversion_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    compatible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    warnings_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reproducibility_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestConversionExecutionRecord(Base):
    __tablename__ = "backtest_conversion_executions"
    __table_args__ = (
        UniqueConstraint("run_id", "execution_id"),
        Index("ix_backtest_conversion_executions_run", "run_id", "conversion_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    execution_id: Mapped[str] = mapped_column(String(160), nullable=False)
    conversion_id: Mapped[str] = mapped_column(String(160), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestManagementComparisonRecord(Base):
    __tablename__ = "backtest_management_comparisons"
    __table_args__ = (
        UniqueConstraint("run_id", "comparison_id"),
        Index("ix_backtest_management_comparisons_run", "run_id", "strategy_instance_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    comparison_id: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(160), nullable=False)
    alternatives_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    selected_action: Mapped[str] = mapped_column(String(64), nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestRollAnalyticsRecord(Base):
    __tablename__ = "backtest_roll_analytics"
    __table_args__ = (
        UniqueConstraint("run_id", "analytics_id"),
        Index("ix_backtest_roll_analytics_run_ts", "run_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    analytics_id: Mapped[str] = mapped_column(String(160), nullable=False)
    roll_metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestConversionAnalyticsRecord(Base):
    __tablename__ = "backtest_conversion_analytics"
    __table_args__ = (
        UniqueConstraint("run_id", "analytics_id"),
        Index("ix_backtest_conversion_analytics_run_ts", "run_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    analytics_id: Mapped[str] = mapped_column(String(160), nullable=False)
    conversion_metrics_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyManagementOptimizerContractRecord(Base):
    __tablename__ = "strategy_management_optimizer_contracts"
    __table_args__ = (
        UniqueConstraint("contract_id"),
        Index("ix_strategy_mgmt_optimizer_contracts_strategy", "strategy_identifier", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    contract_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyManagementChecksumRecord(Base):
    __tablename__ = "strategy_management_checksums"
    __table_args__ = (
        UniqueConstraint("checksum_key"),
        Index("ix_strategy_management_checksums_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checksum_key: Mapped[str] = mapped_column(String(160), nullable=False)
    checksum_value: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskFactorDefinitionRecord(Base):
    __tablename__ = "risk_factor_definitions"
    __table_args__ = (
        UniqueConstraint("factor_id"),
        Index("ix_risk_factor_definitions_factor", "factor_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    factor_id: Mapped[str] = mapped_column(String(160), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    shock_type: Mapped[str] = mapped_column(String(64), nullable=False)
    supported_instruments: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    supported_aggregation: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    transformation_rules: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    validation_rules: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    known_limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskScenarioDefinitionRecord(Base):
    __tablename__ = "risk_scenario_definitions"
    __table_args__ = (
        UniqueConstraint("scenario_id"),
        Index("ix_risk_scenario_definitions_family", "scenario_family", "scenario_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    scenario_family: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(400), nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskScenarioVersionRecord(Base):
    __tablename__ = "risk_scenario_versions"
    __table_args__ = (
        UniqueConstraint("scenario_id", "version"),
        Index("ix_risk_scenario_versions_scenario", "scenario_id", "version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    valuation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_seconds: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    shock_ordering: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    dependencies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    market_regime_assumptions: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    execution_assumptions: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    margin_assumptions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    data_quality_assumptions: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    affected_symbols: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    affected_sectors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    affected_strategy_families: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    probability_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reproducibility_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskScenarioShockRecord(Base):
    __tablename__ = "risk_scenario_shocks"
    __table_args__ = (
        UniqueConstraint("scenario_id", "version", "ordering", "factor_id"),
        Index("ix_risk_scenario_shocks_scenario", "scenario_id", "version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    ordering: Mapped[int] = mapped_column(Integer, nullable=False)
    factor_id: Mapped[str] = mapped_column(String(160), nullable=False)
    shock_type: Mapped[str] = mapped_column(String(64), nullable=False)
    magnitude: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )


class RiskScenarioRunRecord(Base):
    __tablename__ = "risk_scenario_runs"
    __table_args__ = (
        UniqueConstraint("run_id"),
        Index("ix_risk_scenario_runs_ts", "created_at", "scenario_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    portfolio_id: Mapped[str] = mapped_column(String(160), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(160), nullable=False)
    scenario_version: Mapped[str] = mapped_column(String(64), nullable=False)
    as_of_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    software_git_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    failures: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskInstrumentScenarioResultRecord(Base):
    __tablename__ = "risk_instrument_scenario_results"
    __table_args__ = (
        UniqueConstraint("run_id", "instrument_id"),
        Index("ix_risk_instrument_results_run", "run_id", "instrument_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    instrument_id: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(160), nullable=False)
    original_value: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    shocked_value: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    value_change: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    original_greeks: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    shocked_greeks: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    model_used: Mapped[str] = mapped_column(String(128), nullable=False)
    convergence_diagnostics: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    quality_warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class RiskStrategyScenarioResultRecord(Base):
    __tablename__ = "risk_strategy_scenario_results"
    __table_args__ = (
        UniqueConstraint("run_id", "strategy_id"),
        Index("ix_risk_strategy_results_run", "run_id", "strategy_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(160), nullable=False)
    pnl_impact: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    greeks_impact: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    margin_impact: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    buying_power_impact: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    assignment_risk_change: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    exercise_risk_change: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    dividend_risk_change: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    liquidity_impact: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    management_policy_triggers: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    roll_eligibility_changes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    residual_exposure: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RiskPortfolioScenarioResultRecord(Base):
    __tablename__ = "risk_portfolio_scenario_results"
    __table_args__ = (
        UniqueConstraint("run_id", "portfolio_id"),
        Index("ix_risk_portfolio_results_run", "run_id", "portfolio_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    portfolio_id: Mapped[str] = mapped_column(String(160), nullable=False)
    portfolio_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    portfolio_return: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    greeks: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    expected_shortfall: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    margin: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    buying_power: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    concentration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    liquidity: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    assignment_exposure: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    liquidation_requirement: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class RiskScenarioGreeksImpactRecord(Base):
    __tablename__ = "risk_scenario_greeks_impacts"
    __table_args__ = (
        UniqueConstraint("run_id", "scope", "scope_id"),
        Index("ix_risk_greeks_impacts_run", "run_id", "scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(160), nullable=False)
    delta_change: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    gamma_change: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    theta_change: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    vega_change: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    rho_change: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)


class RiskScenarioMarginImpactRecord(Base):
    __tablename__ = "risk_scenario_margin_impacts"
    __table_args__ = (
        UniqueConstraint("run_id", "scope", "scope_id"),
        Index("ix_risk_margin_impacts_run", "run_id", "scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(160), nullable=False)
    pre_margin: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    post_margin: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    excess_liquidity: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    deficit: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    liquidation_requirement: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    candidate_liquidation_plans: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )


class RiskScenarioLiquidityImpactRecord(Base):
    __tablename__ = "risk_scenario_liquidity_impacts"
    __table_args__ = (
        UniqueConstraint("run_id", "scope", "scope_id"),
        Index("ix_risk_liquidity_impacts_run", "run_id", "scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(160), nullable=False)
    spread_multiplier: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    stale_quote_rate: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    no_fill_probability: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RiskScenarioMatrixRecord(Base):
    __tablename__ = "risk_scenario_matrices"
    __table_args__ = (
        UniqueConstraint("run_id", "matrix_id", "row_key", "column_key"),
        Index("ix_risk_scenario_matrices_run", "run_id", "matrix_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    matrix_id: Mapped[str] = mapped_column(String(160), nullable=False)
    row_key: Mapped[str] = mapped_column(String(128), nullable=False)
    column_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class RiskAttributionRecord(Base):
    __tablename__ = "risk_attributions"
    __table_args__ = (
        UniqueConstraint("run_id", "attribution_id"),
        Index("ix_risk_attributions_run", "run_id", "attribution_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    attribution_id: Mapped[str] = mapped_column(String(160), nullable=False)
    components_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    unexplained_residual: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    approximate: Mapped[bool] = mapped_column(Boolean, nullable=False)


class RiskLimitBreachRecord(Base):
    __tablename__ = "risk_limit_breaches"
    __table_args__ = (
        UniqueConstraint("run_id", "metric"),
        Index("ix_risk_limit_breaches_run", "run_id", "severity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    metric: Mapped[str] = mapped_column(String(128), nullable=False)
    observed: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False)
    remediation_candidates: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class RiskManagementComparisonRecord(Base):
    __tablename__ = "risk_management_comparisons"
    __table_args__ = (
        UniqueConstraint("run_id", "comparison_id"),
        Index("ix_risk_management_comparisons_run", "run_id", "comparison_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    comparison_id: Mapped[str] = mapped_column(String(160), nullable=False)
    alternatives_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    selected_action: Mapped[str] = mapped_column(String(64), nullable=False)


class HistoricalScenarioMetadataRecord(Base):
    __tablename__ = "historical_scenario_metadata"
    __table_args__ = (
        UniqueConstraint("scenario_id"),
        Index("ix_historical_scenario_metadata_family", "scenario_family", "scenario_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(160), nullable=False)
    scenario_family: Mapped[str] = mapped_column(String(64), nullable=False)
    fixture_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskQualityDiagnosticRecord(Base):
    __tablename__ = "risk_quality_diagnostics"
    __table_args__ = (
        UniqueConstraint("run_id", "diagnostic_id"),
        Index("ix_risk_quality_diagnostics_run", "run_id", "severity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False)
    diagnostic_id: Mapped[str] = mapped_column(String(160), nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    data_support: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    assumptions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    model_limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_data_warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    calibration_status: Mapped[str] = mapped_column(String(64), nullable=False)


class RiskReproducibilityChecksumRecord(Base):
    __tablename__ = "risk_reproducibility_checksums"
    __table_args__ = (
        UniqueConstraint("checksum_key"),
        Index("ix_risk_reproducibility_checksums_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checksum_key: Mapped[str] = mapped_column(String(160), nullable=False)
    checksum_value: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestStrategyInstanceRecord(Base):
    __tablename__ = "backtest_strategy_instances"
    __table_args__ = (
        UniqueConstraint("run_row_id", "strategy_instance_id", "as_of_timestamp"),
        Index("ix_backtest_strategy_instances_run_ts", "run_row_id", "as_of_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    definition_id: Mapped[str] = mapped_column(String(128), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(64), nullable=False)
    state_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    as_of_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestPositionInstanceRecord(Base):
    __tablename__ = "backtest_position_instances"
    __table_args__ = (
        UniqueConstraint("run_row_id", "position_instance_id", "as_of_timestamp"),
        Index("ix_backtest_position_instances_run_ts", "run_row_id", "as_of_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(64), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    as_of_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestStateTransitionRecord(Base):
    __tablename__ = "backtest_state_transitions"
    __table_args__ = (
        UniqueConstraint("run_row_id", "strategy_instance_id", "sequence_number"),
        Index("ix_backtest_state_transitions_run_ts", "run_row_id", "transition_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    transition_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    prior_state: Mapped[str] = mapped_column(String(64), nullable=False)
    next_state: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger: Mapped[str] = mapped_column(String(128), nullable=False)
    action_plan: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    data_snapshot_reference: Mapped[str] = mapped_column(String(256), nullable=False)
    software_git_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    failures: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    checksum_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestTransitionGuardRecord(Base):
    __tablename__ = "backtest_transition_guards"
    __table_args__ = (
        UniqueConstraint("run_row_id", "transition_row_id", "guard_name"),
        Index("ix_backtest_transition_guards_run", "run_row_id", "guard_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    transition_row_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_state_transitions.id"),
        nullable=False,
    )
    guard_name: Mapped[str] = mapped_column(String(128), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestRollPlanRecord(Base):
    __tablename__ = "backtest_roll_plans"
    __table_args__ = (
        UniqueConstraint("run_row_id", "plan_id"),
        Index("ix_backtest_roll_plans_run_ts", "run_row_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    roll_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_trigger: Mapped[str] = mapped_column(String(128), nullable=False)
    target_specification: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    estimated_credit_or_debit: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestRollRelationshipRecord(Base):
    __tablename__ = "backtest_roll_relationships"
    __table_args__ = (
        UniqueConstraint("run_row_id", "plan_id", "relationship_type", "leg_label"),
        Index("ix_backtest_roll_relationships_run", "run_row_id", "plan_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(128), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    leg_label: Mapped[str] = mapped_column(String(128), nullable=False)
    source_position_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_position_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class BacktestPartialFillRecord(Base):
    __tablename__ = "backtest_partial_fills"
    __table_args__ = (
        UniqueConstraint(
            "run_row_id",
            "strategy_instance_id",
            "position_instance_id",
            "leg_label",
            "fill_timestamp",
        ),
        Index("ix_backtest_partial_fills_run_ts", "run_row_id", "fill_timestamp"),
        CheckConstraint("filled_quantity >= 0", name="backtest_partial_fills_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    leg_label: Mapped[str] = mapped_column(String(128), nullable=False)
    original_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    filled_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    average_entry_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    fill_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestReconciliationEventRecord(Base):
    __tablename__ = "backtest_reconciliation_events"
    __table_args__ = (
        UniqueConstraint(
            "run_row_id",
            "strategy_instance_id",
            "position_instance_id",
            "event_timestamp",
        ),
        Index("ix_backtest_reconciliation_events_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    strategy_fill_ratio: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    retry_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    timed_out: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_escalated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestIntegrityFailureRecord(Base):
    __tablename__ = "backtest_integrity_failures"
    __table_args__ = (
        UniqueConstraint(
            "run_row_id",
            "strategy_instance_id",
            "position_instance_id",
            "failure_timestamp",
            "reason_code",
        ),
        Index("ix_backtest_integrity_failures_run_ts", "run_row_id", "failure_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    failure_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestStrategyHistoryRecord(Base):
    __tablename__ = "backtest_strategy_histories"
    __table_args__ = (
        UniqueConstraint("run_row_id", "strategy_instance_id", "history_timestamp", "history_kind"),
        Index("ix_backtest_strategy_histories_run_ts", "run_row_id", "history_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    history_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    history_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    checksum_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestStrategyAnalyticsRecord(Base):
    __tablename__ = "backtest_strategy_analytics"
    __table_args__ = (
        UniqueConstraint("run_row_id", "strategy_instance_id", "snapshot_timestamp"),
        Index("ix_backtest_strategy_analytics_run_ts", "run_row_id", "snapshot_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    snapshot_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    return_value: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    capital_usage: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cash_usage: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    intrinsic_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    extrinsic_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    greeks: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    implied_volatility: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    realized_volatility: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    iv_rank: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    iv_percentile: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    term_structure_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    liquidity_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    lifecycle_state: Mapped[str] = mapped_column(String(64), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    failures: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class BacktestPortfolioAnalyticsRecord(Base):
    __tablename__ = "backtest_portfolio_analytics"
    __table_args__ = (
        UniqueConstraint("run_row_id", "snapshot_timestamp"),
        Index("ix_backtest_portfolio_analytics_run_ts", "run_row_id", "snapshot_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    snapshot_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    equity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    reserved_capital: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    capital_utilization: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    greeks: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    exposures_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    risk_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestPnLAttributionRecord(Base):
    __tablename__ = "backtest_pnl_attribution"
    __table_args__ = (
        UniqueConstraint("run_row_id", "strategy_instance_id", "snapshot_timestamp"),
        Index("ix_backtest_pnl_attribution_run_ts", "run_row_id", "snapshot_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    snapshot_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    factors_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    approximation: Mapped[bool] = mapped_column(Boolean, nullable=False)


class BacktestGreeksAttributionRecord(Base):
    __tablename__ = "backtest_greeks_attribution"
    __table_args__ = (
        UniqueConstraint("run_row_id", "strategy_instance_id", "snapshot_timestamp"),
        Index("ix_backtest_greeks_attribution_run_ts", "run_row_id", "snapshot_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_instance_id: Mapped[str] = mapped_column(String(128), nullable=False)
    snapshot_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    greek_changes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    attributable_to: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestReconstructedTradeRecord(Base):
    __tablename__ = "backtest_reconstructed_trades"
    __table_args__ = (
        UniqueConstraint("run_row_id", "trade_id"),
        Index("ix_backtest_reconstructed_trades_run", "run_row_id", "strategy_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    trade_id: Mapped[str] = mapped_column(String(256), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    lifecycle_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    cash_movements: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    final_state: Mapped[str] = mapped_column(String(64), nullable=False)
    source_event_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_checksums: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class BacktestStrategyCycleRecord(Base):
    __tablename__ = "backtest_strategy_cycles"
    __table_args__ = (
        UniqueConstraint("run_row_id", "cycle_id"),
        Index("ix_backtest_strategy_cycles_run", "run_row_id", "strategy_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    cycle_id: Mapped[str] = mapped_column(String(256), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    initial_position: Mapped[str] = mapped_column(String(128), nullable=False)
    child_positions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    roll_chain: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    cumulative_debit_credit: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cumulative_fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cumulative_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    maximum_capital_usage: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    total_holding_duration_seconds: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    final_result: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class BacktestReplaySnapshotRecord(Base):
    __tablename__ = "backtest_replay_snapshots"
    __table_args__ = (
        UniqueConstraint("run_row_id", "snapshot_id"),
        Index("ix_backtest_replay_snapshots_run_ts", "run_row_id", "snapshot_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    cursor: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_checksums: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestEventOverlayRecord(Base):
    __tablename__ = "backtest_event_overlays"
    __table_args__ = (
        UniqueConstraint("run_row_id", "event_sequence_number"),
        Index("ix_backtest_event_overlays_run", "run_row_id", "event_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    event_sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    overlay_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestArbitrationDecisionRecord(Base):
    __tablename__ = "backtest_arbitration_decisions"
    __table_args__ = (
        UniqueConstraint("run_row_id", "decision_id"),
        Index("ix_backtest_arbitration_decisions_run_ts", "run_row_id", "decision_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    decision_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    policy: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_actions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    rejected_actions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    diagnostics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestComparisonRunRecord(Base):
    __tablename__ = "backtest_comparison_runs"
    __table_args__ = (
        UniqueConstraint("run_row_id", "comparison_id"),
        Index("ix_backtest_comparison_runs_pair", "left_run_id", "right_run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    comparison_id: Mapped[str] = mapped_column(String(128), nullable=False)
    left_run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    right_run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    comparison_key: Mapped[str] = mapped_column(String(128), nullable=False)
    table_rows: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    chart_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestExportMetadataRecord(Base):
    __tablename__ = "backtest_export_metadata"
    __table_args__ = (
        UniqueConstraint("run_row_id", "export_id"),
        Index("ix_backtest_export_metadata_run_ts", "run_row_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    export_id: Mapped[str] = mapped_column(String(128), nullable=False)
    export_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
    artifact_checksum: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestExecutionRequestRecord(Base):
    __tablename__ = "backtest_execution_requests"
    __table_args__ = (
        UniqueConstraint("run_row_id", "request_id"),
        Index("ix_backtest_execution_requests_run_ts", "run_row_id", "requested_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    leg_id: Mapped[str] = mapped_column(String(128), nullable=False)
    contract_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    effect: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    order_type: Mapped[str] = mapped_column(String(32), nullable=False)
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    mark_price_policy: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_delay_policy: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    fill_model_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    slippage_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    commission_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    exchange_fee_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    minimum_fill_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    all_or_none_research: Mapped[bool] = mapped_column(Boolean, nullable=False)
    maximum_legging_delay_seconds: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    lifecycle_trigger: Mapped[str] = mapped_column(String(128), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_manifest: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestQuoteSelectionRecord(Base):
    __tablename__ = "backtest_quote_selections"
    __table_args__ = (
        UniqueConstraint("run_row_id", "request_id"),
        Index("ix_backtest_quote_selections_run", "run_row_id", "selected_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    selected_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    quote_age_seconds: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    spread_width: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    selected_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    quality_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    stale_data: Mapped[bool] = mapped_column(Boolean, nullable=False)
    crossed_market: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_manifest: Mapped[str | None] = mapped_column(String(256), nullable=True)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestFillAttemptRecord(Base):
    __tablename__ = "backtest_fill_attempts"
    __table_args__ = (
        UniqueConstraint("run_row_id", "request_id", "attempt_timestamp"),
        Index("ix_backtest_fill_attempts_run", "run_row_id", "attempt_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    attempt_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fill_model: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    filled_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    fill_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    slippage: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    spread_capture: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    quote_quality: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)


class BacktestExecutionFillRecord(Base):
    __tablename__ = "backtest_execution_fills"
    __table_args__ = (
        UniqueConstraint("run_row_id", "request_id", "fill_timestamp"),
        Index("ix_backtest_execution_fills_run", "run_row_id", "fill_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fill_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fill_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    fill_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestFeeItemRecord(Base):
    __tablename__ = "backtest_fee_items"
    __table_args__ = (
        UniqueConstraint("run_row_id", "request_id", "event_timestamp", "fee_type"),
        Index("ix_backtest_fee_items_run", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fee_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestExerciseDecisionRecord(Base):
    __tablename__ = "backtest_exercise_decisions"
    __table_args__ = (
        UniqueConstraint("run_row_id", "request_id", "decision_timestamp"),
        Index("ix_backtest_exercise_decisions_run", "run_row_id", "decision_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    rationale: Mapped[str] = mapped_column(String(256), nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestAssignmentDecisionRecord(Base):
    __tablename__ = "backtest_assignment_decisions"
    __table_args__ = (
        UniqueConstraint("run_row_id", "request_id", "decision_timestamp"),
        Index("ix_backtest_assignment_decisions_run", "run_row_id", "decision_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    partial_assignment: Mapped[bool] = mapped_column(Boolean, nullable=False)
    assignment_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str] = mapped_column(String(256), nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestExpirationEventRecord(Base):
    __tablename__ = "backtest_expiration_events"
    __table_args__ = (
        UniqueConstraint("run_row_id", "request_id", "expiration_timestamp"),
        Index("ix_backtest_expiration_events_run", "run_row_id", "expiration_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    expiration_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    intrinsic_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    in_the_money: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cash_settled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    physically_settled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestPhysicalSettlementRecord(Base):
    __tablename__ = "backtest_physical_settlements"
    __table_args__ = (
        UniqueConstraint("run_row_id", "request_id", "settlement_timestamp"),
        Index("ix_backtest_physical_settlements_run", "run_row_id", "settlement_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    settlement_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stock_position_change: Mapped[int] = mapped_column(Integer, nullable=False)
    strike_cash_movement: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestCashSettlementRecord(Base):
    __tablename__ = "backtest_cash_settlements"
    __table_args__ = (
        UniqueConstraint("run_row_id", "request_id", "settlement_timestamp"),
        Index("ix_backtest_cash_settlements_run", "run_row_id", "settlement_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    settlement_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cash_movement: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestDividendSettlementRecord(Base):
    __tablename__ = "backtest_dividend_settlements"
    __table_args__ = (
        UniqueConstraint("run_row_id", "strategy_id", "position_id", "ex_date"),
        Index("ix_backtest_dividend_settlements_run", "run_row_id", "ex_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ex_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    record_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payable_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    special_dividend: Mapped[bool] = mapped_column(Boolean, nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestStockPositionRecord(Base):
    __tablename__ = "backtest_stock_positions"
    __table_args__ = (
        UniqueConstraint("run_row_id", "symbol", "strategy_id", "position_id", "as_of_timestamp"),
        Index("ix_backtest_stock_positions_run", "run_row_id", "as_of_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    as_of_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestCostBasisRecord(Base):
    __tablename__ = "backtest_cost_basis_records"
    __table_args__ = (
        UniqueConstraint("run_row_id", "strategy_cycle_id", "as_of_timestamp"),
        Index("ix_backtest_cost_basis_records_run", "run_row_id", "as_of_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_cycle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    option_cost_basis: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    stock_cost_basis: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cumulative_debits: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cumulative_credits: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cumulative_fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    as_of_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestLedgerPostingRecord(Base):
    __tablename__ = "backtest_ledger_postings"
    __table_args__ = (
        UniqueConstraint("run_row_id", "posting_id"),
        Index("ix_backtest_ledger_postings_run", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    posting_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    posting_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestPinRiskDiagnosticRecord(Base):
    __tablename__ = "backtest_pin_risk_diagnostics"
    __table_args__ = (
        UniqueConstraint("run_row_id", "request_id", "event_timestamp"),
        Index("ix_backtest_pin_risk_diagnostics_run", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    at_risk: Mapped[bool] = mapped_column(Boolean, nullable=False)
    within_band: Mapped[bool] = mapped_column(Boolean, nullable=False)
    warning_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestSettlementReconciliationRecord(Base):
    __tablename__ = "backtest_settlement_reconciliation"
    __table_args__ = (
        UniqueConstraint("run_row_id", "strategy_id", "position_id", "event_timestamp"),
        Index("ix_backtest_settlement_reconciliation_run", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reconciled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestExecutionReproducibilityChecksumRecord(Base):
    __tablename__ = "backtest_execution_reproducibility_checksums"
    __table_args__ = (
        UniqueConstraint("run_row_id", "checksum_key"),
        Index("ix_backtest_execution_repro_checksums_run", "run_row_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    checksum_key: Mapped[str] = mapped_column(String(128), nullable=False)
    checksum_value: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class ReplaySessionRecord(Base):
    __tablename__ = "replay_sessions"
    __table_args__ = (
        UniqueConstraint("session_id"),
        Index("ix_replay_sessions_run", "run_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    timeline_id: Mapped[str] = mapped_column(String(128), nullable=False)
    base_branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReplayBranchRecord(Base):
    __tablename__ = "replay_branches"
    __table_args__ = (
        UniqueConstraint("session_id", "branch_id"),
        Index("ix_replay_branches_session", "session_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_branch_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    root_snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_delta_json: Mapped[dict[str, Any]] = mapped_column(
        "decision_delta",
        JSON,
        nullable=False,
        default=dict,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReplayCheckpointRecord(Base):
    __tablename__ = "replay_checkpoints"
    __table_args__ = (
        UniqueConstraint("session_id", "checkpoint_id"),
        Index("ix_replay_checkpoints_session", "session_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    checkpoint_id: Mapped[str] = mapped_column(String(128), nullable=False)
    branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReplayBookmarkRecord(Base):
    __tablename__ = "replay_bookmarks"
    __table_args__ = (
        UniqueConstraint("session_id", "bookmark_id"),
        Index("ix_replay_bookmarks_session", "session_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    bookmark_id: Mapped[str] = mapped_column(String(128), nullable=False)
    branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReplayEventRecord(Base):
    __tablename__ = "replay_events"
    __table_args__ = (
        UniqueConstraint("session_id", "branch_id", "event_sequence"),
        Index("ix_replay_events_session_branch", "session_id", "branch_id", "event_sequence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    optimizer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    event_checksum: Mapped[str] = mapped_column(String(256), nullable=False)


class ReplayAnnotationRecord(Base):
    __tablename__ = "replay_annotations"
    __table_args__ = (
        UniqueConstraint("session_id", "annotation_id"),
        Index("ix_replay_annotations_session", "session_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    annotation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    note_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReplayFilterRecord(Base):
    __tablename__ = "replay_filters"
    __table_args__ = (
        UniqueConstraint("session_id", "filter_id"),
        Index("ix_replay_filters_session", "session_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    filter_id: Mapped[str] = mapped_column(String(128), nullable=False)
    branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    filter_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReplayComparisonRecord(Base):
    __tablename__ = "replay_comparisons"
    __table_args__ = (
        UniqueConstraint("session_id", "comparison_id"),
        Index("ix_replay_comparisons_session", "session_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    comparison_id: Mapped[str] = mapped_column(String(128), nullable=False)
    left_branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    right_branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    comparison_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReplayDiagnosticRecord(Base):
    __tablename__ = "replay_diagnostics"
    __table_args__ = (
        UniqueConstraint("session_id", "diagnostic_id"),
        Index("ix_replay_diagnostics_session", "session_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    diagnostic_id: Mapped[str] = mapped_column(String(128), nullable=False)
    branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    diagnostic_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReplayReproducibilityReportRecord(Base):
    __tablename__ = "replay_reproducibility_reports"
    __table_args__ = (
        UniqueConstraint("session_id", "report_id"),
        Index("ix_replay_repro_reports_session", "session_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    report_id: Mapped[str] = mapped_column(String(128), nullable=False)
    left_run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    right_run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    report_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DecisionExplanationRecord(Base):
    __tablename__ = "decision_explanations"
    __table_args__ = (
        UniqueConstraint("session_id", "explanation_id"),
        Index("ix_decision_explanations_session", "session_id", "event_sequence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    explanation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    branch_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    explanation_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExperimentRecord(Base):
    __tablename__ = "experiments"
    __table_args__ = (
        UniqueConstraint("experiment_id"),
        Index("ix_experiments_created", "created_at", "version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    configuration_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    dataset_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    strategy_set: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    optimization_set: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    scenario_set: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    replay_set: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExperimentComparisonRecord(Base):
    __tablename__ = "experiment_comparisons"
    __table_args__ = (
        UniqueConstraint("comparison_id"),
        Index(
            "ix_experiment_comparisons_pair",
            "left_experiment_id",
            "right_experiment_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comparison_id: Mapped[str] = mapped_column(String(128), nullable=False)
    left_experiment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    right_experiment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    comparison_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkspaceMetadataRecord(Base):
    __tablename__ = "workspace_metadata"
    __table_args__ = (
        UniqueConstraint("workspace_key"),
        Index("ix_workspace_metadata_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_key: Mapped[str] = mapped_column(String(160), nullable=False)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InstitutionalResearchArtifactRecord(Base):
    """Immutable, versioned payloads for analytics, reports, and validation views."""

    __tablename__ = "institutional_research_artifacts"
    __table_args__ = (
        UniqueConstraint("artifact_id"),
        Index("ix_institutional_artifacts_experiment", "experiment_id", "artifact_kind"),
        Index("ix_institutional_artifacts_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String(128), nullable=False)
    experiment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    replay_links: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestAccountConfigurationRecord(Base):
    __tablename__ = "backtest_account_configurations"
    __table_args__ = (
        UniqueConstraint("run_row_id", "account_id"),
        Index("ix_backtest_account_configs_run", "run_row_id", "account_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_type: Mapped[str] = mapped_column(String(64), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(16), nullable=False)
    starting_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    reserve_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    settled_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unsettled_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    interest_policy_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    margin_policy_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    borrow_policy_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    commission_fee_policy_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    house_margin_overlay_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    risk_limits_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    liquidation_policy_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestMarginPolicyRecord(Base):
    __tablename__ = "backtest_margin_policies"
    __table_args__ = (
        UniqueConstraint("run_row_id", "account_id", "policy_name", "policy_version"),
        Index("ix_backtest_margin_policies_run", "run_row_id", "account_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    supported_account_types: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    supported_instrument_types: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestMarginCalculationRecord(Base):
    __tablename__ = "backtest_margin_calculations"
    __table_args__ = (
        UniqueConstraint("run_row_id", "calculation_id"),
        Index("ix_backtest_margin_calculations_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    calculation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    position_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    initial_requirement: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    maintenance_requirement: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    option_buying_power_effect: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    stock_buying_power_effect: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    pending_order_reservation: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    assignment_reservation: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    exercise_reservation: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    settlement_reservation: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    concentration_add_ons: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    event_risk_add_ons: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    house_margin_add_ons: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    post_trade_buying_power: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    excess_liquidity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cushion: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestBuyingPowerSnapshotRecord(Base):
    __tablename__ = "backtest_buying_power_snapshots"
    __table_args__ = (
        UniqueConstraint("run_row_id", "account_id", "event_timestamp"),
        Index("ix_backtest_buying_power_snapshots_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_buying_power: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    initial_requirement: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    maintenance_requirement: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    excess_liquidity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cushion: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    free_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    settled_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unsettled_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    reserved_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    collateral_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestCollateralRecord(Base):
    __tablename__ = "backtest_collateral_records"
    __table_args__ = (
        UniqueConstraint(
            "run_row_id",
            "account_id",
            "event_timestamp",
            "position_id",
            "collateral_type",
        ),
        Index("ix_backtest_collateral_records_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    strategy_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    position_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    collateral_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    covered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestCashBalanceRecord(Base):
    __tablename__ = "backtest_cash_balances"
    __table_args__ = (
        UniqueConstraint("run_row_id", "account_id", "event_timestamp"),
        Index("ix_backtest_cash_balances_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    settled_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unsettled_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    reserved_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    collateral_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    free_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    net_cash: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestCashSettlementFlowRecord(Base):
    __tablename__ = "backtest_cash_settlement_flows"
    __table_args__ = (
        UniqueConstraint("run_row_id", "posting_id"),
        Index("ix_backtest_cash_settlement_flows_run_ts", "run_row_id", "settlement_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    posting_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    trade_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    settlement_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    settled_delta: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unsettled_delta: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    reserved_delta: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    collateral_delta: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    strategy_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    position_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestInterestAccrualRecord(Base):
    __tablename__ = "backtest_interest_accruals"
    __table_args__ = (
        UniqueConstraint("run_row_id", "accrual_id"),
        Index("ix_backtest_interest_accruals_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    accrual_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    balance_basis: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    accrued_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    is_debit: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_curve: Mapped[str] = mapped_column(String(128), nullable=False)
    assumptions_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestBorrowRecord(Base):
    __tablename__ = "backtest_borrow_records"
    __table_args__ = (
        UniqueConstraint("run_row_id", "borrow_id"),
        Index("ix_backtest_borrow_records_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    borrow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    annualized_rate: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    hard_to_borrow: Mapped[bool] = mapped_column(Boolean, nullable=False)
    locate_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    buy_in_risk: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    recall_risk: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestBorrowAccrualRecord(Base):
    __tablename__ = "backtest_borrow_accruals"
    __table_args__ = (
        UniqueConstraint("run_row_id", "accrual_id"),
        Index("ix_backtest_borrow_accruals_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    accrual_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    share_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    annualized_rate: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    accrued_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    hard_to_borrow: Mapped[bool] = mapped_column(Boolean, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestMarginCallEventRecord(Base):
    __tablename__ = "backtest_margin_call_events"
    __table_args__ = (
        UniqueConstraint("run_row_id", "call_id"),
        Index("ix_backtest_margin_call_events_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    call_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_required: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    deadline_placeholder: Mapped[str] = mapped_column(String(64), nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class BacktestLiquidationPlanRecord(Base):
    __tablename__ = "backtest_liquidation_plans"
    __table_args__ = (
        UniqueConstraint("run_row_id", "plan_id"),
        Index("ix_backtest_liquidation_plans_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    policy: Mapped[str] = mapped_column(String(128), nullable=False)
    deficit_to_resolve: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    strategy_preserving: Mapped[bool] = mapped_column(Boolean, nullable=False)
    solved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestLiquidationStepRecord(Base):
    __tablename__ = "backtest_liquidation_steps"
    __table_args__ = (
        UniqueConstraint("run_row_id", "step_id"),
        Index("ix_backtest_liquidation_steps_run", "run_row_id", "plan_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(128), nullable=False)
    step_id: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    position_id: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity_fraction: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    expected_margin_relief: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    expected_cash_impact: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    expected_realized_loss: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    remaining_deficit: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestLiquidationOutcomeRecord(Base):
    __tablename__ = "backtest_liquidation_outcomes"
    __table_args__ = (
        UniqueConstraint("run_row_id", "plan_id", "event_timestamp"),
        Index("ix_backtest_liquidation_outcomes_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    realized_loss: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    residual_margin_deficit: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    residual_buying_power: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    residual_excess_liquidity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    residual_stock_exposure: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    residual_strategy_breakage: Mapped[bool] = mapped_column(Boolean, nullable=False)
    residual_greeks_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestBrokerPolicyComparisonRecord(Base):
    __tablename__ = "backtest_broker_policy_comparisons"
    __table_args__ = (
        UniqueConstraint("run_row_id", "comparison_id"),
        Index("ix_backtest_policy_comparisons_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    comparison_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    left_policy: Mapped[str] = mapped_column(String(128), nullable=False)
    right_policy: Mapped[str] = mapped_column(String(128), nullable=False)
    initial_requirement_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    maintenance_requirement_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    buying_power_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    ambiguity_warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestExecutionCalibrationDatasetRecord(Base):
    __tablename__ = "backtest_execution_calibration_datasets"
    __table_args__ = (
        UniqueConstraint("run_row_id", "dataset_id"),
        Index("ix_backtest_exec_cal_datasets_run_ts", "run_row_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_manifest: Mapped[str] = mapped_column(String(256), nullable=False)
    broker_policy_version: Mapped[str] = mapped_column(String(128), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestExecutionFillQualityObservationRecord(Base):
    __tablename__ = "backtest_execution_fill_quality_observations"
    __table_args__ = (
        UniqueConstraint("run_row_id", "observation_id"),
        Index("ix_backtest_exec_fill_quality_run_ts", "run_row_id", "event_timestamp"),
        Index("ix_backtest_exec_fill_quality_symbol", "symbol", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    observation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    contract_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    market_regime: Mapped[str] = mapped_column(String(32), nullable=False)
    liquidity_regime: Mapped[str] = mapped_column(String(32), nullable=False)
    volatility_regime: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy_family: Mapped[str] = mapped_column(String(64), nullable=False)
    fill_ratio: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price_improvement: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price_disimprovement: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    effective_spread: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    realized_spread: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    quoted_spread: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    spread_capture: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    slippage_vs_midpoint: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    slippage_vs_arrival: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    implementation_shortfall: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    cancellation_rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    timeout_rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    partial_fill_rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    delay_to_fill_seconds: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    residual_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    legging_cost: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    opportunity_cost: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    execution_cost_bps: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    execution_cost_dollars: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestExecutionSlippageModelRecord(Base):
    __tablename__ = "backtest_execution_slippage_models"
    __table_args__ = (
        UniqueConstraint("run_row_id", "model_id"),
        Index("ix_backtest_exec_slippage_models_run", "run_row_id", "calibrated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    calibrated_parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    confidence_intervals: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    fit_diagnostics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    residual_analysis: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    regime_coverage: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    validity_status: Mapped[str] = mapped_column(String(32), nullable=False)
    calibrated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestExecutionSpreadCaptureModelRecord(Base):
    __tablename__ = "backtest_execution_spread_capture_models"
    __table_args__ = (
        UniqueConstraint("run_row_id", "model_id"),
        Index("ix_backtest_exec_spread_models_run", "run_row_id", "calibrated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    calibrated_parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    confidence_intervals: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    fit_diagnostics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    residual_analysis: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    regime_coverage: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    validity_status: Mapped[str] = mapped_column(String(32), nullable=False)
    calibrated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestExecutionPartialFillModelRecord(Base):
    __tablename__ = "backtest_execution_partial_fill_models"
    __table_args__ = (
        UniqueConstraint("run_row_id", "model_id"),
        Index("ix_backtest_exec_partial_models_run", "run_row_id", "calibrated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fill_probability: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    expected_fill_ratio: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cancellation_probability: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    timeout_probability: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    retry_probability: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    expected_residual_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    multi_leg_completion_probability: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )
    legging_exposure_duration_seconds: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )
    conditioned_on: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    calibrated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestExecutionTransactionCostPolicyRecord(Base):
    __tablename__ = "backtest_execution_transaction_cost_policies"
    __table_args__ = (
        UniqueConstraint("run_row_id", "policy_id"),
        Index("ix_backtest_exec_cost_policies_run", "run_row_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    policy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestExecutionBrokerPolicyVersionRecord(Base):
    __tablename__ = "backtest_execution_broker_policy_versions"
    __table_args__ = (
        UniqueConstraint("run_row_id", "policy_name", "policy_version"),
        Index("ix_backtest_exec_policy_versions_run", "run_row_id", "effective_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    assumptions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    supported_instruments: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    unsupported_instruments: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    known_differences_from_official: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    deprecated_versions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class BacktestExecutionPolicyComparisonRecord(Base):
    __tablename__ = "backtest_execution_policy_comparisons"
    __table_args__ = (
        UniqueConstraint("run_row_id", "comparison_id"),
        Index("ix_backtest_exec_policy_comp_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    comparison_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    left_policy: Mapped[str] = mapped_column(String(128), nullable=False)
    right_policy: Mapped[str] = mapped_column(String(128), nullable=False)
    commissions_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    exchange_fees_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    exercise_assignment_fees_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    buying_power_effect_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    maintenance_requirement_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    interest_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    borrow_cost_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    total_transaction_cost_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    total_return_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    cagr_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    drawdown_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    rejected_trades_diff: Mapped[int] = mapped_column(Integer, nullable=False)
    margin_breaches_diff: Mapped[int] = mapped_column(Integer, nullable=False)
    liquidations_diff: Mapped[int] = mapped_column(Integer, nullable=False)
    net_performance_diff: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    ambiguity_warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class BacktestExecutionQualityScoreRecord(Base):
    __tablename__ = "backtest_execution_quality_scores"
    __table_args__ = (
        UniqueConstraint("run_row_id", "score_id"),
        Index("ix_backtest_exec_quality_scores_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    score_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    contract_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    total_score: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    component_scores: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    component_weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class BacktestExecutionRealVsSimulatedRecord(Base):
    __tablename__ = "backtest_execution_real_vs_simulated"
    __table_args__ = (
        UniqueConstraint("run_row_id", "comparison_id"),
        Index("ix_backtest_exec_real_vs_sim_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    comparison_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    contract_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    simulated_fill_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    real_fill_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    expected_fill_distribution: Mapped[list[float]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    price_error: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    cost_error: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    timing_error_seconds: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    partial_fill_error: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fee_error: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    policy_mismatch: Mapped[bool] = mapped_column(Boolean, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class BacktestExecutionValidationRunRecord(Base):
    __tablename__ = "backtest_execution_validation_runs"
    __table_args__ = (
        UniqueConstraint("run_row_id", "validation_run_id"),
        Index("ix_backtest_exec_validation_runs_run", "run_row_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    validation_run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    split_type: Mapped[str] = mapped_column(String(64), nullable=False)
    train_size: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_size: Mapped[int] = mapped_column(Integer, nullable=False)
    error_distribution: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    calibration_drift: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    parameter_drift: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    out_of_sample_cost_error: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    overconfidence_score: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestExecutionCalibrationDriftRecord(Base):
    __tablename__ = "backtest_execution_calibration_drift"
    __table_args__ = (
        UniqueConstraint("run_row_id", "drift_id"),
        Index("ix_backtest_exec_cal_drift_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    drift_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    calibration_drift: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    parameter_drift: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestExecutionStressTestResultRecord(Base):
    __tablename__ = "backtest_execution_stress_test_results"
    __table_args__ = (
        UniqueConstraint("run_row_id", "scenario_name", "event_timestamp"),
        Index("ix_backtest_exec_stress_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_cost_delta: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    avg_fill_ratio: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    avg_delay_seconds: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestExecutionCalibrationChecksumRecord(Base):
    __tablename__ = "backtest_execution_calibration_checksums"
    __table_args__ = (
        UniqueConstraint("run_row_id", "checksum_key"),
        Index("ix_backtest_exec_cal_checksums_run", "run_row_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    checksum_key: Mapped[str] = mapped_column(String(128), nullable=False)
    checksum_value: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


class BacktestMarginReconciliationRecord(Base):
    __tablename__ = "backtest_margin_reconciliations"
    __table_args__ = (
        UniqueConstraint("run_row_id", "reconciliation_id"),
        Index("ix_backtest_margin_reconciliations_run_ts", "run_row_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    reconciliation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reconciled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BacktestMarginReproducibilityChecksumRecord(Base):
    __tablename__ = "backtest_margin_reproducibility_checksums"
    __table_args__ = (
        UniqueConstraint("run_row_id", "checksum_key"),
        Index("ix_backtest_margin_repro_checksums_run", "run_row_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_row_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    checksum_key: Mapped[str] = mapped_column(String(128), nullable=False)
    checksum_value: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )


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
