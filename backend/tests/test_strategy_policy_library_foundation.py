from __future__ import annotations

from datetime import UTC, datetime

from backend.backtesting import (
    PolicyFamily,
    PolicySetEvaluationResult,
    default_strategy_policy_registry,
    deterministic_strategy_policy_checksum,
)
from backend.backtesting.policies import ConflictMode
from backend.backtesting.strategy_policy_library import (
    PolicyEvaluationContext,
    StrategyPolicyLibraryError,
)


def test_default_policy_registry_contains_required_families() -> None:
    registry = default_strategy_policy_registry()
    discovered = registry.discover_policies(include_deprecated=True)
    families = {item.family for item in discovered}

    assert PolicyFamily.ENTRY in families
    assert PolicyFamily.EXIT in families
    assert PolicyFamily.MANAGEMENT in families
    assert PolicyFamily.EARNINGS in families
    assert PolicyFamily.DIVIDEND in families
    assert PolicyFamily.ROLL in families


def test_alias_resolution_and_policy_set_lookup() -> None:
    registry = default_strategy_policy_registry()
    policy = registry.resolve_policy("profit_target")
    policy_set = registry.resolve_policy_set(set_id="pmcc_core", set_version="8B-v1")

    assert policy.policy_id == "exit.profit_target"
    assert policy_set.strategy_identifier == "covered.pmcc"
    assert policy_set.conflict_mode is ConflictMode.PRIORITY_ORDERING


def test_policy_set_evaluation_emits_diagnostics() -> None:
    registry = default_strategy_policy_registry()
    context = PolicyEvaluationContext(
        strategy_identifier="covered.pmcc",
        event_timestamp=datetime(2027, 1, 15, 15, 30, tzinfo=UTC),
        data_timestamp=datetime(2027, 1, 15, 15, 30, tzinfo=UTC),
        underlying_symbol="SPY",
        dte=9,
        pnl_pct=0.41,
        absolute_delta=0.38,
        iv_rank=0.28,
        earnings_within_days=5,
        in_dividend_window=False,
    )

    result = registry.evaluate_policy_set(
        set_id="pmcc_core",
        set_version="8B-v1",
        context=context,
    )

    assert isinstance(result, PolicySetEvaluationResult)
    assert len(result.outcomes) >= 5
    assert result.conflict_resolution.winning_signal is not None


def test_policy_checksum_is_deterministic() -> None:
    registry = default_strategy_policy_registry()
    policies = registry.discover_policies(include_deprecated=True)
    policy_sets = registry.discover_policy_sets()

    first = deterministic_strategy_policy_checksum(
        policies=policies,
        policy_sets=policy_sets,
    )
    second = deterministic_strategy_policy_checksum(
        policies=tuple(reversed(policies)),
        policy_sets=tuple(reversed(policy_sets)),
    )
    assert first == second


def test_unknown_policy_raises() -> None:
    registry = default_strategy_policy_registry()
    try:
        registry.resolve_policy("does.not.exist")
    except StrategyPolicyLibraryError:
        pass
    else:
        raise AssertionError("expected StrategyPolicyLibraryError")
