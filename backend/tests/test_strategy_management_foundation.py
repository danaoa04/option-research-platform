from __future__ import annotations

from datetime import UTC, datetime

from backend.backtesting import (
    ManagementAction,
    ManagementPathAlternative,
    PartialRollState,
    RollLegSelection,
    RollRequest,
    RollTargetCandidate,
    RollType,
    StrategyManagementPlanner,
    validate_basis_transfer_invariants,
)
from backend.backtesting.guards import NoLookAheadGuard
from backend.backtesting.queries import BacktestAsOfQueryService
from backend.backtesting.strategy_management import BasisTrackingResult, RollEligibilityGuard


def _leg(label: str) -> RollLegSelection:
    return RollLegSelection(
        leg_label=label,
        contract_id=f"{label}-c",
        quantity=1,
        expiration=datetime(2027, 2, 19, tzinfo=UTC),
        strike=100.0,
        delta=0.25,
        premium=1.2,
        bid=1.1,
        ask=1.3,
        liquidity_score=0.9,
        quote_quality=0.9,
    )


def _request(
    *,
    minimum_credit: float | None = None,
    maximum_debit: float | None = None,
) -> RollRequest:
    return RollRequest(
        strategy_identifier="covered.pmcc",
        strategy_instance_id="sid-1",
        position_identifier="pid-1",
        selected_source_legs=(_leg("short_call"),),
        preserved_legs=(_leg("long_call"),),
        close_quantity=1,
        target_quantity=1,
        target_expiration_policy="next_monthly",
        target_strike_policy="same_strike",
        target_delta=0.3,
        target_dte=30,
        target_premium=None,
        credit_or_debit_requirement=None,
        maximum_debit=maximum_debit,
        minimum_credit=minimum_credit,
        maximum_cumulative_roll_debit=2.0,
        minimum_expected_improvement=0.0,
        liquidity_threshold=0.5,
        quote_quality_threshold=0.5,
        margin_policy={"mode": "research-only"},
        execution_policy={"fill_policy": "best_effort"},
        requested_timestamp=datetime(2027, 1, 3, tzinfo=UTC),
        trigger="profit_target",
        reason_code="test",
    )


def _candidate(
    *,
    estimated_net_credit_or_debit: float | None = 0.5,
    expiration: datetime | None = None,
) -> RollTargetCandidate:
    return RollTargetCandidate(
        candidate_id="cand-1",
        target_legs=(_leg("short_call_new"),),
        roll_type=RollType.ROLL_OUT,
        target_expiration=(
            expiration
            if expiration is not None
            else datetime(2027, 3, 19, tzinfo=UTC)
        ),
        target_strike=105.0,
        target_delta=0.3,
        target_dte=45,
        estimated_closing_cost=0.8,
        estimated_opening_proceeds=1.3,
        estimated_net_credit_or_debit=estimated_net_credit_or_debit,
        fees=0.05,
        liquidity_score=0.9,
        quality_score=0.9,
    )


def test_roll_eligibility_edge_case_rejections() -> None:
    guard = RollEligibilityGuard()
    request = _request(minimum_credit=0.3, maximum_debit=0.2)
    candidate = _candidate(estimated_net_credit_or_debit=-0.5)
    candidate = RollTargetCandidate(
        candidate_id=candidate.candidate_id,
        target_legs=candidate.target_legs,
        roll_type=candidate.roll_type,
        target_expiration=None,
        target_strike=candidate.target_strike,
        target_delta=candidate.target_delta,
        target_dte=candidate.target_dte,
        estimated_closing_cost=candidate.estimated_closing_cost,
        estimated_opening_proceeds=candidate.estimated_opening_proceeds,
        estimated_net_credit_or_debit=candidate.estimated_net_credit_or_debit,
        fees=candidate.fees,
        liquidity_score=candidate.liquidity_score,
        quality_score=candidate.quality_score,
        metadata=candidate.metadata,
    )

    result = guard.evaluate(
        request=request,
        candidate=candidate,
        roll_count=3,
        cumulative_debit=3.0,
        max_roll_count=3,
        cooldown_passed=False,
        min_time_since_prior_roll_passed=False,
        target_contract_available=False,
        target_quote_available=False,
        acceptable_quote_age=False,
        acceptable_spread=False,
        acceptable_fill_confidence=False,
        margin_compatible=False,
        buying_power_available=False,
        no_conflicting_corporate_action=True,
        no_unsupported_contract_adjustment=True,
        assignment_risk_compatible=False,
        dividend_risk_compatible=False,
        event_risk_allowed=False,
        no_look_ahead_compliant=True,
    )

    assert not result.eligible
    codes = {item.code for item in result.rejections}
    assert "invalid_target_expiration" in codes
    assert "target_contract_unavailable" in codes
    assert "target_quote_unavailable" in codes
    assert "quote_age_unacceptable" in codes
    assert "minimum_credit_not_met" in codes
    assert "maximum_debit_exceeded" in codes
    assert "maximum_cumulative_debit_exceeded" in codes
    assert "maximum_roll_count_reached" in codes
    assert "assignment_risk_incompatible" in codes
    assert "dividend_risk_incompatible" in codes


def test_partial_roll_reconciliation_states() -> None:
    planner = StrategyManagementPlanner()
    state = PartialRollState(
        state_id="state-1",
        plan_id="plan-1",
        one_source_leg_closed_target_failed=True,
        partial_close=True,
        partial_target_fill=True,
        preserved_legs=("long_call",),
        residual_quantities={"short_call": 1},
        temporary_naked_exposure=True,
        timeout_seconds=30.0,
        risk_escalated=True,
    )

    retry = planner.reconcile_partial_roll(state=state, retry_allowed=True, elapsed_seconds=10.0)
    cancel = planner.reconcile_partial_roll(state=state, retry_allowed=False, elapsed_seconds=31.0)

    assert retry.retry_scheduled
    assert not retry.cancel_scheduled
    assert retry.recorded_temporary_exposure
    assert cancel.cancel_scheduled
    assert cancel.fallback_close_scheduled


def test_basis_transfer_invariants_and_preserved_leg_basis() -> None:
    valid = BasisTrackingResult(
        original_basis=2.0,
        cumulative_credits=1.0,
        cumulative_debits=1.5,
        fees=0.1,
        closing_pnl=0.2,
        target_leg_basis=1.3,
        preserved_leg_basis=1.2,
        new_strategy_cycle_basis=2.5,
        realized_pnl=0.2,
        unrealized_pnl=0.1,
        cost_basis_transfer=0.5,
        cumulative_short_premium_income=0.8,
        cumulative_roll_cost=0.6,
        post_assignment_or_exercise_basis=None,
    )
    ok, violations = validate_basis_transfer_invariants(valid)
    assert ok
    assert violations == ()

    invalid = BasisTrackingResult(
        original_basis=2.0,
        cumulative_credits=1.0,
        cumulative_debits=1.5,
        fees=0.1,
        closing_pnl=0.2,
        target_leg_basis=1.0,
        preserved_leg_basis=1.2,
        new_strategy_cycle_basis=2.5,
        realized_pnl=0.2,
        unrealized_pnl=0.1,
        cost_basis_transfer=0.5,
        cumulative_short_premium_income=0.8,
        cumulative_roll_cost=0.0,
        post_assignment_or_exercise_basis=None,
    )
    ok_invalid, violations_invalid = validate_basis_transfer_invariants(invalid)
    assert not ok_invalid
    assert "new_strategy_cycle_basis_mismatch" in violations_invalid
    assert "cumulative_roll_cost_mismatch" in violations_invalid


def test_conversion_candidate_comparison_and_management_selection() -> None:
    planner = StrategyManagementPlanner()
    comparison = planner.compare_management_paths(
        comparison_id="cmp-1",
        strategy_instance_id="sid-1",
        alternatives=(
            ManagementPathAlternative(
                action=ManagementAction.HOLD,
                immediate_cost=0.0,
                projected_pnl_distribution={"p50": 1.0},
                expected_value=0.5,
                probability_of_profit=0.55,
                greeks={"delta": 0.1},
                margin=1000.0,
                buying_power=1200.0,
                tail_risk=0.25,
                assignment_risk=0.2,
                dividend_risk=0.1,
                liquidity=0.8,
                expected_holding_period_days=7,
                complexity=0.2,
                data_quality=0.9,
                confidence=0.9,
            ),
            ManagementPathAlternative(
                action=ManagementAction.ROLL,
                immediate_cost=0.1,
                projected_pnl_distribution={"p50": 1.4},
                expected_value=0.8,
                probability_of_profit=0.62,
                greeks={"delta": 0.05},
                margin=900.0,
                buying_power=1100.0,
                tail_risk=0.15,
                assignment_risk=0.1,
                dividend_risk=0.08,
                liquidity=0.75,
                expected_holding_period_days=10,
                complexity=0.4,
                data_quality=0.9,
                confidence=0.9,
            ),
        ),
    )

    assert comparison.selected_action is ManagementAction.ROLL


def test_backtesting_as_of_query_no_lookahead_behavior() -> None:
    query = BacktestAsOfQueryService(guard=NoLookAheadGuard())
    as_of = datetime(2027, 1, 2, tzinfo=UTC)
    states = (
        {
            "strategy_instance_id": "sid-1",
            "as_of_timestamp": datetime(2027, 1, 3, tzinfo=UTC),
            "lifecycle_state": "open",
        },
    )

    result = query.strategy_state_as_of(
        as_of=as_of,
        strategy_states=states,
        strategy_instance_id="sid-1",
    )
    assert result.value is None
