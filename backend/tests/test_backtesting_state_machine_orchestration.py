from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.backtesting.orchestration import EntryMode, LegFillSnapshot, MultiLegOrchestrator
from backend.backtesting.policies import (
    ConflictMode,
    LifecyclePolicySignal,
    PolicyConflictResolver,
    PolicyDisposition,
)
from backend.backtesting.state_machine import (
    ActionName,
    ActionPlan,
    GuardName,
    GuardResult,
    InvalidTransitionError,
    LifecycleState,
    StrategyStateMachine,
    TransitionTrigger,
)
from backend.backtesting.strategies import compile_template
from backend.backtesting.transition_guards import GuardEvaluationRequest, TransitionGuardLibrary


def test_state_machine_valid_and_invalid_transitions() -> None:
    machine = StrategyStateMachine(
        strategy_identifier="strategy-1",
        position_identifier="position-1",
        software_git_commit="deadbeef",
    )
    first = machine.transition(
        next_state=LifecycleState.WAITING_FOR_ENTRY,
        timestamp=datetime(2026, 6, 1, 14, 30, tzinfo=UTC),
        trigger=TransitionTrigger.ENTRY_POLICY,
        guard_results=(
            GuardResult(guard=GuardName.DATA_AVAILABLE, passed=True, reason_code="ok"),
        ),
        action_plan=(
            ActionPlan(action=ActionName.CREATE_ENTRY_PLAN, payload={"mode": "simultaneous"}),
        ),
        data_snapshot_reference="snap-1",
    )
    assert first.sequence_number == 1
    assert first.prior_state is LifecycleState.CONFIGURED

    with pytest.raises(InvalidTransitionError):
        machine.transition(
            next_state=LifecycleState.OPEN,
            timestamp=datetime(2026, 6, 1, 14, 31, tzinfo=UTC),
            trigger=TransitionTrigger.ENTRY_POLICY,
            guard_results=(
                GuardResult(
                    guard=GuardName.DATA_AVAILABLE,
                    passed=True,
                    reason_code="ok",
                ),
            ),
            action_plan=(
                ActionPlan(action=ActionName.ACTIVATE_POSITION),
            ),
            data_snapshot_reference="snap-2",
        )


def test_transition_guards_and_policy_conflicts() -> None:
    guards = TransitionGuardLibrary()
    market = guards.evaluate(
        request=GuardEvaluationRequest(
            guard=GuardName.MARKET_OPEN,
            context={"market_open": True},
        )
    )
    width = guards.evaluate(
        request=GuardEvaluationRequest(
            guard=GuardName.BID_ASK_WIDTH,
            context={"bid_ask_width": 0.35, "maximum_bid_ask_width": 0.20},
        )
    )
    assert market.passed is True
    assert width.passed is False

    resolver = PolicyConflictResolver()
    result = resolver.resolve(
        signals=(
            LifecyclePolicySignal(
                policy_name="profit_target",
                signal="exit",
                disposition=PolicyDisposition.ADVISORY,
                priority=50,
            ),
            LifecyclePolicySignal(
                policy_name="risk_breach",
                signal="exit",
                disposition=PolicyDisposition.MANDATORY,
                priority=5,
            ),
        ),
        mode=ConflictMode.PRIORITY_ORDERING,
    )
    assert result.winning_signal is not None
    assert result.winning_signal.policy_name == "risk_breach"


def test_entry_partial_fill_roll_and_integrity_paths() -> None:
    orchestrator = MultiLegOrchestrator()
    definition = compile_template(template_name="pmcc")

    plan = orchestrator.create_entry_plan(
        strategy_definition=definition,
        strategy_instance_id="instance-1",
        entry_mode=EntryMode.SEQUENTIAL,
        all_or_none_research_intent=False,
        minimum_fill_ratio=0.5,
        maximum_legging_delay_seconds=300,
        leg_priority=("long_deep_itm_call", "short_otm_call"),
        cancellation_on_incomplete_fill=True,
        completion_allowed_after_partial_fill=True,
    )
    assert [item.leg_label for item in plan.intents] == [
        "long_deep_itm_call",
        "short_otm_call",
    ]

    fills = (
        LegFillSnapshot(
            leg_label="long_deep_itm_call",
            original_quantity=1,
            filled_quantity=1,
            remaining_quantity=0,
            average_entry_price=12.5,
            average_exit_price=None,
            current_mark=13.0,
            realized_pnl=0.0,
            unrealized_pnl=0.5,
            accrued_fees=0.1,
            multiplier=100,
            cost_basis=1250,
            intrinsic_value=5.0,
            extrinsic_value=8.0,
            greeks={"delta": 0.82, "theta": -0.03},
            implied_volatility=0.22,
            quote_quality=0.9,
            stale_data_age_seconds=5,
            lifecycle_status="open",
        ),
        LegFillSnapshot(
            leg_label="short_otm_call",
            original_quantity=1,
            filled_quantity=0,
            remaining_quantity=1,
            average_entry_price=None,
            average_exit_price=None,
            current_mark=1.8,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            accrued_fees=0.0,
            multiplier=100,
            cost_basis=0.0,
            intrinsic_value=0.0,
            extrinsic_value=1.8,
            greeks={"delta": -0.22, "theta": 0.04},
            implied_volatility=0.26,
            quote_quality=0.88,
            stale_data_age_seconds=8,
            lifecycle_status="open",
        ),
    )

    recon = orchestrator.reconcile_partial_fills(
        timestamp=datetime(2026, 6, 1, 15, 0, tzinfo=UTC),
        strategy_instance_id="instance-1",
        position_instance_id="position-1",
        leg_fills=fills,
        minimum_fill_ratio=0.75,
        timeout_seconds=60,
        elapsed_seconds=75,
        cancellation_on_incomplete_fill=True,
    )
    assert recon.failure_escalated is True
    assert recon.cancelled is True

    eligibility = orchestrator.evaluate_roll_eligibility(
        liquidity_ok=True,
        target_expiration_valid=True,
        target_strike_valid=True,
        no_conflicting_corporate_action=True,
        unsupported_expiration_imminent=False,
        roll_count=1,
        maximum_roll_count=3,
        cumulative_debit=1.0,
        maximum_cumulative_debit=5.0,
        expected_improvement=0.2,
        minimum_expected_improvement=0.1,
        required_credit=0.0,
        estimated_credit=0.2,
        margin_placeholder_compatible=True,
        quality_score=0.9,
        quality_threshold=0.5,
        data_complete=True,
    )
    assert eligibility.eligible is True

    expiration = orchestrator.orchestrate_expiration(leg_fills=fills)
    assert expiration.residual_exposure_detected is True
    assert expiration.pending_exercise_or_assignment_required is True

    integrity = orchestrator.integrity_failures(
        position_status="closed",
        leg_fills=fills,
        cash_ledger_balance=1000,
        expected_cash_balance=950,
    )
    codes = {item.reason_code for item in integrity}
    assert "position_closed_with_open_legs" in codes
    assert "cash_ledger_not_reconciled" in codes
