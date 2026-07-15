from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.backtesting.execution import (
    ExecutionAction,
    ExecutionOrderType,
    ExecutionRequest,
    ExecutionSide,
    MultiLegExecutionCoordinator,
    OpenCloseEffect,
)
from backend.backtesting.execution_queries import ExecutionQueryService
from backend.backtesting.fees import ItemizedFeeModel
from backend.backtesting.fill_models import FillModelRequest, ResearchFillModelEngine
from backend.backtesting.guards import NoLookAheadGuard
from backend.backtesting.quote_selection import (
    QuotePriceSelection,
    QuoteSelectionPolicy,
    QuoteSelectionResult,
    QuoteSelector,
)
from backend.backtesting.settlement import SettlementEngine


def _request(
    *,
    leg_id: str = "L1",
    contract_identifier: str = "SPY-202701C500",
    quantity: int = 10,
    requested_timestamp: datetime | None = None,
    all_or_none: bool = False,
    fill_policy: dict[str, object] | None = None,
) -> ExecutionRequest:
    ts = requested_timestamp or datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    return ExecutionRequest(
        strategy_id="strategy-1",
        position_id="position-1",
        leg_id=leg_id,
        contract_identifier=contract_identifier,
        action=ExecutionAction.OPEN,
        side=ExecutionSide.BUY,
        effect=OpenCloseEffect.OPEN,
        quantity=quantity,
        requested_timestamp=ts,
        order_type=ExecutionOrderType.LIMIT,
        limit_price=2.0,
        mark_price_policy="midpoint",
        execution_delay_policy={"seconds": 0.0},
        fill_model_policy=fill_policy or {"mode": "baseline", "fill_ratio": 0.5},
        slippage_policy={"fixed_per_contract": 0.01},
        commission_policy={"per_contract": 0.65},
        exchange_fee_policy={"per_contract": 0.02},
        minimum_fill_quantity=1,
        all_or_none_research=all_or_none,
        maximum_legging_delay_seconds=3.0,
        lifecycle_trigger="entry",
        reason_code="entry_signal",
        dataset_manifest="m1",
        metadata={},
    )


def _selection(price: float, ts: datetime) -> QuoteSelectionResult:
    return QuoteSelectionResult(
        selected_quote={"timestamp": ts, "bid": price - 0.1, "ask": price + 0.1},
        selected_price=price,
        quote_age_seconds=0.0,
        spread_width=0.2,
        quality_flags=(),
        stale_data=False,
        crossed_market=False,
        source_manifest="m1",
        diagnostics={},
    )


def test_quote_selector_nearest_prior_and_fallback() -> None:
    selector = QuoteSelector(stale_quote_seconds=90.0)
    request_ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    quotes = (
        {
            "timestamp": request_ts - timedelta(seconds=60),
            "bid": 1.0,
            "ask": 1.2,
            "manifest": "m1",
        },
        {
            "timestamp": request_ts + timedelta(seconds=60),
            "bid": 2.0,
            "ask": 2.2,
            "manifest": "m1",
        },
    )
    nearest = selector.select(
        request_timestamp=request_ts,
        quotes=quotes,
        policy=QuoteSelectionPolicy(
            mode="nearest_prior",
            price_selection=QuotePriceSelection.MIDPOINT,
        ),
        delay_seconds=0.0,
    )
    assert nearest.selected_price == 1.1
    assert nearest.quote_age_seconds == 60.0
    assert nearest.stale_data is False

    fallback = selector.select(
        request_timestamp=request_ts,
        quotes=(),
        policy=QuoteSelectionPolicy(
            mode="exact",
            price_selection=QuotePriceSelection.MIDPOINT,
            theoretical_fallback_enabled=True,
        ),
        delay_seconds=1.0,
    )
    assert fallback.source_manifest == "theoretical_fallback"
    assert "theoretical_fallback" in fallback.quality_flags


def test_fill_engine_partial_all_or_none_and_no_fill_mode() -> None:
    engine = ResearchFillModelEngine()
    request_ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    req = _request(quantity=10, requested_timestamp=request_ts)
    quote = {
        "timestamp": request_ts,
        "bid": 1.9,
        "ask": 2.1,
        "iv": 0.25,
        "liquidity_score": 0.9,
    }
    result = engine.fill(
        FillModelRequest(
            request=req,
            quote=quote,
            diagnostics=_selection(2.0, request_ts),
            policy_name="baseline",
        )
    )
    assert result.filled_quantity == 5
    assert result.remaining_quantity == 5

    aon_request = _request(
        quantity=10,
        requested_timestamp=request_ts,
        all_or_none=True,
        fill_policy={"mode": "baseline", "fill_ratio": 0.5},
    )
    aon_result = engine.fill(
        FillModelRequest(
            request=aon_request,
            quote=quote,
            diagnostics=_selection(2.0, request_ts),
            policy_name="baseline",
        )
    )
    assert aon_result.filled_quantity == 0
    assert aon_result.failure_reason == "insufficient_liquidity"

    no_fill_request = _request(
        quantity=10,
        requested_timestamp=request_ts,
        fill_policy={"mode": "no_fill", "fill_ratio": 1.0},
    )
    no_fill = engine.fill(
        FillModelRequest(
            request=no_fill_request,
            quote=quote,
            diagnostics=_selection(2.0, request_ts),
            policy_name="baseline",
        )
    )
    assert no_fill.filled_quantity == 0
    assert no_fill.failure_reason == "policy_no_fill"


def test_multileg_execution_cancel_on_timeout_when_ratio_too_low() -> None:
    now = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    coordinator = MultiLegExecutionCoordinator(
        quote_selector=QuoteSelector(),
        fill_engine=ResearchFillModelEngine(),
        fee_engine=ItemizedFeeModel(),
    )
    req1 = _request(
        leg_id="L1",
        contract_identifier="C1",
        quantity=1,
        requested_timestamp=now,
        fill_policy={"mode": "baseline", "fill_ratio": 1.0},
    )
    req2 = _request(leg_id="L2", contract_identifier="C2", quantity=1, requested_timestamp=now)

    result = coordinator.execute(
        requests=(req1, req2),
        quotes_by_contract={
            "C1": ({"timestamp": now, "bid": 1.0, "ask": 1.2, "manifest": "m1"},),
            "C2": (),
        },
        quote_policy=QuoteSelectionPolicy(
            mode="nearest_prior",
            price_selection=QuotePriceSelection.MIDPOINT,
        ),
        leg_priority=("L1", "L2"),
        minimum_aggregate_fill_ratio=0.8,
        timeout_seconds=0.0,
        started_at=now,
        now=now,
        maximum_legging_exposure=1.0,
    )

    assert result.request_count == 2
    assert result.filled_ratio == 0.5
    assert result.timed_out is True
    assert result.cancelled is True
    assert result.retry_eligible is False


def test_settlement_engine_assignment_cash_settlement_and_reconciliation_filters() -> None:
    engine = SettlementEngine()
    ts = datetime(2027, 1, 15, 21, 0, tzinfo=UTC)
    expiration = engine.expiration_decision(
        timestamp=ts,
        contract_metadata={"option_type": "call", "settlement_type": "cash"},
        underlying_price=105.0,
        strike=100.0,
        quantity=2,
        exercise_threshold=0.01,
        pin_risk_band=0.25,
    )
    assignment = engine.short_assignment_decision(
        timestamp=ts,
        contract_metadata={"option_type": "call", "settlement_type": "cash"},
        underlying_price=105.0,
        strike=100.0,
        quantity=2,
        remaining_extrinsic=0.01,
        dividend_amount=0.5,
        seeded_policy=7,
    )
    settlement = engine.settle(
        timestamp=ts,
        contract_metadata={"option_type": "call", "settlement_type": "cash"},
        underlying_price=105.0,
        strike=100.0,
        quantity=2,
        multiplier=100.0,
        is_long=False,
        expiration=expiration,
        exercise=None,
        assignment=assignment,
        fees=1.0,
    )

    assert any(post.posting_type == "cash_settlement" for post in settlement.postings)
    assert settlement.reconciled is True

    pin = engine.pin_risk(
        timestamp=ts,
        underlying_price=100.1,
        strike=100.0,
        pin_risk_band=0.25,
        has_partial_assignment=assignment.partial_assignment,
        settlement_complete=settlement.reconciled,
    )
    assert pin.at_risk is True

    query = ExecutionQueryService(guard=NoLookAheadGuard(strict=True))
    as_of = datetime(2027, 1, 15, 16, 0, tzinfo=UTC)
    stock_as_of = query.stock_positions_as_of(
        as_of=as_of,
        symbol="SPY",
        rows=(
            {"symbol": "SPY", "as_of_timestamp": as_of - timedelta(minutes=5), "quantity": 10},
            {"symbol": "SPY", "as_of_timestamp": as_of - timedelta(minutes=1), "quantity": 15},
            {"symbol": "SPY", "as_of_timestamp": as_of + timedelta(minutes=1), "quantity": 99},
        ),
    )
    assert stock_as_of.value is not None
    assert stock_as_of.value["quantity"] == 15

    failures = query.reconciliation_failures(
        rows=(
            {"reconciled": True, "id": "ok"},
            {"reconciled": False, "id": "bad"},
        )
    )
    assert len(failures) == 1
    assert failures[0]["id"] == "bad"
