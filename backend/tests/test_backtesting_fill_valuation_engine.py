from __future__ import annotations

from datetime import UTC, date, datetime

from backend.backtesting.engine import BacktestingEngine
from backend.backtesting.fills import BaselineResearchFillModel, FillModelConfig
from backend.backtesting.guards import NoLookAheadGuard
from backend.backtesting.models import (
    BacktestConfiguration,
    DeterministicEvent,
    EventContext,
    EventType,
    FillPricePolicy,
    LegAssetType,
    LifecycleDecision,
    LifecycleStatus,
    MarkPricePolicy,
    OrderAction,
    OrderIntent,
    OrderSide,
    PositionLegState,
    PositionState,
    QuoteSnapshot,
)
from backend.backtesting.valuation import ValuationService


class _Strategy:
    strategy_id = "s1"

    def initialize(self, *, configuration: BacktestConfiguration) -> None:
        self._configuration = configuration

    def evaluate_entry(self, *, context: EventContext) -> LifecycleDecision:
        if (
            context.event.event_type is EventType.LIFECYCLE_EVALUATION
            and not context.open_positions
        ):
            return LifecycleDecision(should_open=True, reason_code="entry")
        return LifecycleDecision()

    def create_position(self, *, context: EventContext) -> PositionState | None:
        leg = PositionLegState(
            leg_id="leg-1",
            contract_identifier="SPY-20260717C00500000",
            asset_type=LegAssetType.CALL,
            quantity=1,
            strike=500,
            expiration=date(2026, 7, 17),
            option_type="call",
            exercise_style="american",
            entry_price=5.0,
            current_price=5.0,
            intrinsic_value=0.0,
            extrinsic_value=5.0,
            delta=0.3,
            gamma=0.02,
            theta=-0.01,
            vega=0.12,
            rho=0.01,
        )
        return PositionState(
            position_id="p-1",
            strategy_id=self.strategy_id,
            lifecycle_status=LifecycleStatus.OPEN,
            opened_at=context.event.timestamp,
            closed_at=None,
            legs=(leg,),
        )

    def mark_position(self, *, context: EventContext, position: PositionState) -> PositionState:
        return position

    def evaluate_management_rules(
        self, *, context: EventContext, position: PositionState
    ) -> LifecycleDecision:
        return LifecycleDecision()

    def evaluate_exit(self, *, context: EventContext, position: PositionState) -> LifecycleDecision:
        if context.event.event_type is EventType.SESSION_CLOSE:
            return LifecycleDecision(should_close=True, reason_code="session_close")
        return LifecycleDecision()

    def evaluate_roll_eligibility(
        self, *, context: EventContext, position: PositionState
    ) -> LifecycleDecision:
        return LifecycleDecision()

    def process_expiration(
        self, *, context: EventContext, position: PositionState
    ) -> PositionState:
        return position

    def finalize(self, *, result) -> None:
        self._result = result


class _FailingStrategy(_Strategy):
    def evaluate_entry(self, *, context: EventContext) -> LifecycleDecision:
        raise RuntimeError("intentional failure")


def test_baseline_fill_and_valuation() -> None:
    fill = BaselineResearchFillModel(config=FillModelConfig(percent_through_spread=0.5))
    quote = QuoteSnapshot(
        contract_identifier="SPY-20260717C00500000",
        timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
        bid=4.9,
        ask=5.1,
        last=5.0,
    )
    intent = OrderIntent(
        intent_id="i-1",
        side=OrderSide.BUY,
        action=OrderAction.OPEN,
        asset_type=LegAssetType.CALL,
        quantity=1,
        contract_identifier=quote.contract_identifier,
        requested_timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
        strategy_id="s1",
        position_id="p-1",
        price_policy=FillPricePolicy.MIDPOINT,
        reason_code="entry",
        lifecycle_trigger="entry",
    )
    result = fill.fill(intent=intent, quote=quote)
    assert result.filled is True
    assert result.fill_price == 5.0

    missing_quote = fill.fill(intent=intent, quote=None)
    assert missing_quote.filled is False
    assert missing_quote.diagnostics.reason_code == "missing_quote"

    stale_quote = QuoteSnapshot(
        contract_identifier=quote.contract_identifier,
        timestamp=datetime(2026, 6, 1, 14, 50, tzinfo=UTC),
        bid=4.8,
        ask=5.0,
        last=4.9,
    )
    stale_result = fill.fill(intent=intent, quote=stale_quote)
    assert stale_result.filled is False
    assert stale_result.diagnostics.reason_code == "stale_quote"

    leg = PositionLegState(
        leg_id="leg-1",
        contract_identifier=quote.contract_identifier,
        asset_type=LegAssetType.CALL,
        quantity=1,
        strike=500,
        expiration=date(2026, 7, 17),
        option_type="call",
        exercise_style="american",
        entry_price=4.0,
        current_price=4.0,
        intrinsic_value=0.0,
        extrinsic_value=4.0,
        delta=0.2,
        gamma=0.01,
        theta=-0.02,
        vega=0.1,
        rho=0.01,
    )
    service = ValuationService(mark_policy=MarkPricePolicy.MIDPOINT)
    leg_value = service.value_leg(
        as_of=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
        leg=leg,
        quote=quote,
    )
    assert leg_value.mark_price == 5.0


def test_event_loop_runs_deterministically() -> None:
    engine = BacktestingEngine(guard=NoLookAheadGuard())
    strategy = _Strategy()
    config = BacktestConfiguration(
        strategy_definition={"name": "calendar"},
        symbol_universe=("SPY",),
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 1),
        dataset_manifests=("m1",),
        bar_frequency="1m",
        timezone="UTC",
        market_calendar="XNYS",
        valuation_policy=MarkPricePolicy.MIDPOINT,
        fill_model_config={"policy": "midpoint"},
        lifecycle_policies={"profit_target": 0.2},
        position_sizing_policy={"contracts": 1},
        initial_capital=100000,
        reserve_cash=10000,
        commission_policy={"type": "placeholder"},
        slippage_policy={"type": "placeholder"},
        execution_delay_policy={"quotes": 0},
        dividend_policy={"source": "historical"},
        corporate_action_policy={"source": "historical"},
        expiration_policy={"mode": "pending_events"},
        exercise_style_metadata_policy={"source": "contract"},
        random_seed=11,
        software_git_commit="deadbeef",
        schema_version="6.0",
        metadata={"pricing_models": {"default": "router"}},
    )
    events = (
        DeterministicEvent(
            event_id="1",
            timestamp=datetime(2026, 6, 1, 14, 30, tzinfo=UTC),
            event_type=EventType.LIFECYCLE_EVALUATION,
            priority=10,
            sequence_number=1,
            payload={"manifest": "m1"},
        ),
        DeterministicEvent(
            event_id="2",
            timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
            event_type=EventType.VALUATION,
            priority=20,
            sequence_number=2,
            payload={"manifest": "m1"},
        ),
        DeterministicEvent(
            event_id="3",
            timestamp=datetime(2026, 6, 1, 21, 0, tzinfo=UTC),
            event_type=EventType.SESSION_CLOSE,
            priority=30,
            sequence_number=3,
            payload={"manifest": "m1"},
        ),
    )

    result = engine.run(configuration=config, strategy=strategy, events=events)
    assert result.status.value in {"completed", "failed"}
    assert result.reproducibility.software_git_commit == "deadbeef"
    assert len(result.event_ledger) >= 3


def test_failed_event_isolation() -> None:
    engine = BacktestingEngine(guard=NoLookAheadGuard())
    strategy = _FailingStrategy()
    config = BacktestConfiguration(
        strategy_definition={"name": "calendar"},
        symbol_universe=("SPY",),
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 1),
        dataset_manifests=("m1",),
        bar_frequency="1m",
        timezone="UTC",
        market_calendar="XNYS",
        valuation_policy=MarkPricePolicy.MIDPOINT,
        fill_model_config={"policy": "midpoint"},
        lifecycle_policies={"profit_target": 0.2},
        position_sizing_policy={"contracts": 1},
        initial_capital=100000,
        reserve_cash=10000,
        commission_policy={"type": "placeholder"},
        slippage_policy={"type": "placeholder"},
        execution_delay_policy={"quotes": 0},
        dividend_policy={"source": "historical"},
        corporate_action_policy={"source": "historical"},
        expiration_policy={"mode": "pending_events"},
        exercise_style_metadata_policy={"source": "contract"},
        random_seed=11,
        software_git_commit="deadbeef",
        schema_version="6.0",
        metadata={},
    )
    events = (
        DeterministicEvent(
            event_id="1",
            timestamp=datetime(2026, 6, 1, 14, 30, tzinfo=UTC),
            event_type=EventType.LIFECYCLE_EVALUATION,
            priority=10,
            sequence_number=1,
            payload={"manifest": "m1"},
        ),
        DeterministicEvent(
            event_id="2",
            timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
            event_type=EventType.VALUATION,
            priority=20,
            sequence_number=2,
            payload={"manifest": "m1"},
        ),
    )
    result = engine.run(configuration=config, strategy=strategy, events=events)
    assert len(result.failed_events) == 1
    assert len(result.event_ledger) >= 2
