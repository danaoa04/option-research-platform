from __future__ import annotations

from datetime import date

from backend.backtesting.strategies import (
    STRATEGY_TEMPLATE_NAMES,
    LegSelectionCandidate,
    LegSelectionEngine,
    LegSelectionPolicy,
    SelectionPolicyType,
    compile_template,
)


def test_all_strategy_templates_compile() -> None:
    compiled = [compile_template(template_name=name) for name in STRATEGY_TEMPLATE_NAMES]
    assert len(compiled) == 18
    assert all(item.legs for item in compiled)


def test_leg_selection_engine_exact_and_target_delta() -> None:
    candidates = (
        LegSelectionCandidate(
            contract_identifier="A",
            strike=500,
            expiration=date(2026, 7, 17),
            delta=0.35,
            moneyness=1.01,
            premium=4.1,
            dte=45,
            is_weekly=False,
            liquidity_score=0.8,
            quality_score=0.95,
        ),
        LegSelectionCandidate(
            contract_identifier="B",
            strike=505,
            expiration=date(2026, 7, 17),
            delta=0.28,
            moneyness=1.02,
            premium=3.2,
            dte=45,
            is_weekly=False,
            liquidity_score=0.75,
            quality_score=0.9,
        ),
    )
    engine = LegSelectionEngine()

    exact = engine.select_leg(
        candidates=candidates,
        policies=(
            LegSelectionPolicy(
                policy_type=SelectionPolicyType.EXACT_STRIKE,
                parameters={"strike": 505},
            ),
        ),
    )
    assert exact.candidate is not None
    assert exact.candidate.contract_identifier == "B"

    by_delta = engine.select_leg(
        candidates=candidates,
        policies=(
            LegSelectionPolicy(
                policy_type=SelectionPolicyType.TARGET_DELTA,
                parameters={"delta": 0.3},
            ),
        ),
    )
    assert by_delta.candidate is not None
    assert by_delta.candidate.contract_identifier == "B"


def test_leg_selection_diagnostics_when_no_match() -> None:
    candidates = (
        LegSelectionCandidate(
            contract_identifier="A",
            strike=500,
            expiration=date(2026, 7, 17),
            delta=0.35,
            moneyness=1.01,
            premium=4.1,
            dte=45,
            is_weekly=False,
            liquidity_score=0.8,
            quality_score=0.95,
        ),
    )
    engine = LegSelectionEngine()
    result = engine.select_leg(
        candidates=candidates,
        policies=(
            LegSelectionPolicy(
                policy_type=SelectionPolicyType.EXACT_STRIKE,
                parameters={"strike": 1000},
            ),
        ),
    )
    assert result.candidate is None
    assert result.diagnostics
