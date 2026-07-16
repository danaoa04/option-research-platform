from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine

from backend.database import (
    StrategyPolicyAliasDTO,
    StrategyPolicyChecksumDTO,
    StrategyPolicyConflictDTO,
    StrategyPolicyEvaluationDTO,
    StrategyPolicyMutationError,
    StrategyPolicyPersistenceService,
    StrategyPolicyQueryService,
    StrategyPolicyRegistryDTO,
    StrategyPolicySetVersionDTO,
    deterministic_strategy_policy_state_checksum,
)
from backend.database.models import Base
from backend.database.session import DatabaseSessionManager


def test_strategy_policy_persistence_round_trip() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)

    ts = datetime(2027, 2, 1, 14, 0, tzinfo=UTC)

    StrategyPolicyPersistenceService(manager).store_policy_state(
        policies=[
            StrategyPolicyRegistryDTO(
                policy_id="exit.profit_target",
                policy_name="Exit Profit Target",
                policy_family="exit",
                policy_version="8B-v1",
                priority=10,
                parameters_json={"target": 0.4},
                required_data=["pnl_pct"],
                supported_strategies=["covered.pmcc"],
                tags=["exit"],
                deprecated=False,
                replacement_policy_id=None,
                metadata_json={"sprint": "8B"},
                created_at=ts,
            )
        ],
        aliases=[
            StrategyPolicyAliasDTO(
                policy_id="exit.profit_target",
                alias="profit_target",
                created_at=ts,
            )
        ],
        policy_sets=[
            StrategyPolicySetVersionDTO(
                set_id="pmcc_core",
                set_version="8B-v1",
                strategy_identifier="covered.pmcc",
                conflict_mode="priority_ordering",
                entry_policies=["entry.iv_rank_floor"],
                exit_policies=["exit.profit_target"],
                management_policies=["management.roll_dte_window"],
                earnings_policies=["earnings.avoid_near_event"],
                dividend_policies=["dividend.avoid_ex_div_window"],
                roll_policies=["roll.delta_breach"],
                metadata_json={"owner": "test"},
                created_at=ts,
            )
        ],
        evaluations=[
            StrategyPolicyEvaluationDTO(
                run_id="run-1",
                evaluation_id="eval-1",
                strategy_identifier="covered.pmcc",
                policy_set_id="pmcc_core",
                policy_set_version="8B-v1",
                policy_id="exit.profit_target",
                policy_version="8B-v1",
                policy_family="exit",
                passed=True,
                reason_code="profit_target_hit",
                observed_values_json={"pnl_pct": 0.41},
                thresholds_json={"target": 0.4},
                diagnostics_json=[{"key": "pnl_pct", "passed": True}],
                confidence=Decimal("1.0"),
                required_data_present=True,
                data_timestamp=ts,
                event_timestamp=ts,
                metadata_json={"strategy_identifier": "covered.pmcc"},
            )
        ],
        conflicts=[
            StrategyPolicyConflictDTO(
                run_id="run-1",
                conflict_id="conf-1",
                strategy_identifier="covered.pmcc",
                policy_set_id="pmcc_core",
                policy_set_version="8B-v1",
                conflict_mode="priority_ordering",
                winning_policy_id="exit.profit_target",
                matched_signals_json=[{"policy_name": "exit.profit_target", "signal": "pass"}],
                diagnostics=["matched=exit.profit_target:pass:mandatory"],
                event_timestamp=ts,
            )
        ],
        checksums=[
            StrategyPolicyChecksumDTO(
                checksum_key="strategy-policy-library",
                checksum_value="sha256:abc",
                metadata_json={"version": "8B-v1"},
                created_at=ts,
            )
        ],
    )

    query = StrategyPolicyQueryService(manager)
    policies = query.list_policies(family="exit")
    by_id = query.policy_by_identifier("profit_target")
    policy_set = query.policy_set(set_id="pmcc_core", set_version="8B-v1")
    evaluations = query.run_policy_evaluations("run-1")
    conflicts = query.run_policy_conflicts("run-1")

    assert len(policies) == 1
    assert by_id is not None
    assert by_id["policy_id"] == "exit.profit_target"
    assert policy_set is not None
    assert len(evaluations) == 1
    assert len(conflicts) == 1


def test_strategy_policy_checksum_determinism() -> None:
    ts = datetime(2027, 2, 1, 14, 0, tzinfo=UTC)
    policies = [
        StrategyPolicyRegistryDTO(
            policy_id="b",
            policy_name="b",
            policy_family="exit",
            policy_version="1",
            priority=2,
            parameters_json={},
            required_data=[],
            supported_strategies=[],
            tags=[],
            deprecated=False,
            replacement_policy_id=None,
            metadata_json={},
            created_at=ts,
        ),
        StrategyPolicyRegistryDTO(
            policy_id="a",
            policy_name="a",
            policy_family="entry",
            policy_version="1",
            priority=1,
            parameters_json={},
            required_data=[],
            supported_strategies=[],
            tags=[],
            deprecated=False,
            replacement_policy_id=None,
            metadata_json={},
            created_at=ts,
        ),
    ]
    policy_sets = [
        StrategyPolicySetVersionDTO(
            set_id="set-a",
            set_version="1",
            strategy_identifier="covered.pmcc",
            conflict_mode="priority_ordering",
            entry_policies=[],
            exit_policies=[],
            management_policies=[],
            earnings_policies=[],
            dividend_policies=[],
            roll_policies=[],
            metadata_json={},
            created_at=ts,
        )
    ]

    first = deterministic_strategy_policy_state_checksum(
        policies=policies,
        policy_sets=policy_sets,
    )
    second = deterministic_strategy_policy_state_checksum(
        policies=list(reversed(policies)),
        policy_sets=list(reversed(policy_sets)),
    )
    assert first == second


def test_strategy_policy_mutation_error_type_exists() -> None:
    err = StrategyPolicyMutationError("x")
    assert isinstance(err, RuntimeError)
