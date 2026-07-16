from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine

from backend.database import (
    BacktestBasisTransferDTO,
    BacktestConversionAnalyticsV2DTO,
    BacktestConversionExecutionDTO,
    BacktestConversionPlanV2DTO,
    BacktestManagementComparisonV2DTO,
    BacktestPartialRollStateDTO,
    BacktestRollAnalyticsV2DTO,
    BacktestRollCandidateDTO,
    BacktestRollEligibilityV2DTO,
    BacktestRollExecutionV2DTO,
    BacktestRollFillV2DTO,
    BacktestRollReconciliationV2DTO,
    BacktestRollRequestV2DTO,
    RollPolicyAliasDTO,
    RollPolicyRegistryDTO,
    StrategyManagementChecksumDTO,
    StrategyManagementMutationError,
    StrategyManagementOptimizerContractDTO,
    StrategyManagementPersistenceService,
    StrategyManagementQueryService,
    deterministic_strategy_management_checksum,
)
from backend.database.models import Base
from backend.database.session import DatabaseSessionManager


def test_strategy_management_persistence_round_trip_queries() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)

    ts = datetime(2027, 3, 1, 14, 0, tzinfo=UTC)
    run_id = "run-8c"

    StrategyManagementPersistenceService(manager).store_state(
        roll_policies=[
            RollPolicyRegistryDTO(
                canonical_identifier="roll.pmcc_short_call_core",
                version="8C-v1",
                aliases_json=["pmcc_short_call"],
                supported_strategy_families=["covered", "diagonal"],
                supported_lifecycle_states=["open"],
                supported_exercise_styles=["american"],
                supported_settlement_types=["physical"],
                required_market_data=["quotes"],
                required_volatility_data=["term_structure"],
                parameter_schema_json={"delta_threshold": 0.4},
                default_priority=10,
                status="mandatory",
                plugin_namespace=None,
                deprecated=False,
                replacement_identifier=None,
                known_limitations=["research_only"],
                metadata_json={"sprint": "8C"},
                created_at=ts,
            )
        ],
        roll_policy_aliases=[
            RollPolicyAliasDTO(
                canonical_identifier="roll.pmcc_short_call_core",
                alias="pmcc_short_call",
                created_at=ts,
            )
        ],
        roll_requests=[
            BacktestRollRequestV2DTO(
                run_id=run_id,
                request_id="req-1",
                strategy_identifier="covered.pmcc",
                strategy_instance_id="sid-1",
                position_identifier="pid-1",
                source_legs_json=[{"leg": "short_call"}],
                preserved_legs_json=[{"leg": "long_call"}],
                close_quantity=1,
                target_quantity=1,
                target_expiration_policy="next_monthly",
                target_strike_policy="same_strike",
                requested_timestamp=ts,
                trigger="profit_target",
                reason_code="edge-test",
                metadata_json={"case": "base"},
            )
        ],
        roll_candidates=[
            BacktestRollCandidateDTO(
                run_id=run_id,
                request_id="req-1",
                candidate_id="cand-1",
                roll_type="roll_out",
                target_legs_json=[{"leg": "short_call_new"}],
                estimated_net_credit_or_debit=Decimal("0.50"),
                liquidity_score=Decimal("0.9"),
                quality_score=Decimal("0.9"),
                diagnostics_json={"quality": "good"},
            )
        ],
        roll_eligibility_results=[
            BacktestRollEligibilityV2DTO(
                run_id=run_id,
                request_id="req-1",
                candidate_id="cand-1",
                eligibility_id="elig-1",
                eligible=False,
                rejections_json=[{"code": "maximum_debit_exceeded"}],
                diagnostics_json={"debit": 0.8},
            )
        ],
        roll_executions=[
            BacktestRollExecutionV2DTO(
                run_id=run_id,
                execution_id="exec-1",
                plan_id="plan-1",
                request_id="req-1",
                execution_style="net_limit",
                all_or_none_research=True,
                sequential_legging=False,
                requested_net_price=Decimal("0.20"),
                metadata_json={"note": "simulated"},
            )
        ],
        roll_fills=[
            BacktestRollFillV2DTO(
                run_id=run_id,
                execution_id="exec-1",
                leg_label="short_call_new",
                fill_timestamp=ts,
                fill_quantity=1,
                fill_price=Decimal("1.25"),
                fees=Decimal("0.03"),
                slippage=Decimal("0.01"),
                diagnostics_json={"source": "research"},
            )
        ],
        partial_roll_states=[
            BacktestPartialRollStateDTO(
                run_id=run_id,
                state_id="state-1",
                plan_id="plan-1",
                temporary_naked_exposure=True,
                residual_quantities_json={"short_call": 1},
                risk_escalated=True,
                timeout_seconds=Decimal("30"),
                metadata_json={"stage": "partial"},
            )
        ],
        roll_reconciliations=[
            BacktestRollReconciliationV2DTO(
                run_id=run_id,
                reconciliation_id="recon-1",
                plan_id="plan-1",
                status="partial",
                retry_scheduled=True,
                cancel_scheduled=False,
                fallback_close_scheduled=False,
                state_transition="risk_escalation",
                recorded_temporary_exposure=True,
                diagnostics_json={"elapsed_seconds": 10},
            )
        ],
        basis_transfers=[
            BacktestBasisTransferDTO(
                run_id=run_id,
                basis_transfer_id="basis-1",
                plan_id="plan-1",
                original_basis=Decimal("2.0"),
                cumulative_credits=Decimal("1.0"),
                cumulative_debits=Decimal("0.7"),
                fees=Decimal("0.1"),
                realized_pnl=Decimal("0.2"),
                unrealized_pnl=Decimal("0.1"),
                basis_json={"preserved_leg_basis": 1.1},
            )
        ],
        conversion_plans=[
            BacktestConversionPlanV2DTO(
                run_id=run_id,
                conversion_id="conv-1",
                strategy_instance_id="sid-1",
                source_strategy="covered.pmcc",
                target_strategy="diagonal.call_diagonal",
                legs_closed_json=[{"leg": "short_call"}],
                legs_preserved_json=[{"leg": "long_call"}],
                legs_opened_json=[{"leg": "short_call_new"}],
                conversion_cost=Decimal("0.4"),
                compatible=True,
                warnings_json=[],
                reproducibility_json={"seed": "deterministic"},
            )
        ],
        conversion_executions=[
            BacktestConversionExecutionDTO(
                run_id=run_id,
                execution_id="conv-exec-1",
                conversion_id="conv-1",
                execution_status="filled",
                execution_json={"fills": 1},
            )
        ],
        management_comparisons=[
            BacktestManagementComparisonV2DTO(
                run_id=run_id,
                comparison_id="cmp-1",
                strategy_instance_id="sid-1",
                alternatives_json=[{"action": "hold"}, {"action": "roll"}],
                selected_action="roll",
                diagnostics_json={"score": 1.2},
                created_at=ts,
            )
        ],
        roll_analytics=[
            BacktestRollAnalyticsV2DTO(
                run_id=run_id,
                analytics_id="roll-an-1",
                roll_metrics_json={"roll_count": 1},
                created_at=ts,
            )
        ],
        conversion_analytics=[
            BacktestConversionAnalyticsV2DTO(
                run_id=run_id,
                analytics_id="conv-an-1",
                conversion_metrics_json={"conversion_count": 1},
                created_at=ts,
            )
        ],
        optimizer_contracts=[
            StrategyManagementOptimizerContractDTO(
                contract_id="opt-1",
                strategy_identifier="covered.pmcc",
                contract_json={"stress_penalty": True},
                created_at=ts,
            )
        ],
        checksums=[
            StrategyManagementChecksumDTO(
                checksum_key="strategy-management-state",
                checksum_value="sha256:abc",
                metadata_json={"version": "8C-v1"},
                created_at=ts,
            )
        ],
    )

    query = StrategyManagementQueryService(manager)
    assert len(query.roll_policy_catalogue()) == 1
    assert query.roll_policy_details("pmcc_short_call") is not None
    assert len(query.roll_history(run_id)) == 1
    assert len(query.roll_candidate_history(run_id, "req-1")) == 1
    assert len(query.eligibility_failures(run_id)) == 1
    assert len(query.partial_roll_state(run_id)) == 1
    assert len(query.basis_history(run_id)) == 1
    assert len(query.conversion_history(run_id)) == 1
    assert len(query.management_comparisons(run_id)) == 1
    assert len(query.pmcc_roll_history(run_id)) == 1
    assert len(query.diagonal_roll_history(run_id)) == 0
    assert len(query.unresolved_roll_failures(run_id)) == 1
    assert len(query.replay_roll_events(run_id)) == 1


def test_strategy_management_checksum_reconciles_deterministically() -> None:
    ts = datetime(2027, 3, 1, 14, 0, tzinfo=UTC)
    policies = [
        RollPolicyRegistryDTO(
            canonical_identifier="roll.b",
            version="1",
            aliases_json=[],
            supported_strategy_families=[],
            supported_lifecycle_states=[],
            supported_exercise_styles=[],
            supported_settlement_types=[],
            required_market_data=[],
            required_volatility_data=[],
            parameter_schema_json={},
            default_priority=2,
            status="advisory",
            plugin_namespace=None,
            deprecated=False,
            replacement_identifier=None,
            known_limitations=[],
            metadata_json={},
            created_at=ts,
        ),
        RollPolicyRegistryDTO(
            canonical_identifier="roll.a",
            version="1",
            aliases_json=[],
            supported_strategy_families=[],
            supported_lifecycle_states=[],
            supported_exercise_styles=[],
            supported_settlement_types=[],
            required_market_data=[],
            required_volatility_data=[],
            parameter_schema_json={},
            default_priority=1,
            status="mandatory",
            plugin_namespace=None,
            deprecated=False,
            replacement_identifier=None,
            known_limitations=[],
            metadata_json={},
            created_at=ts,
        ),
    ]
    requests = [
        BacktestRollRequestV2DTO(
            run_id="run",
            request_id="req-b",
            strategy_identifier="s2",
            strategy_instance_id="sid2",
            position_identifier="pid2",
            source_legs_json=[],
            preserved_legs_json=[],
            close_quantity=1,
            target_quantity=1,
            target_expiration_policy="x",
            target_strike_policy="x",
            requested_timestamp=ts,
            trigger="x",
            reason_code="b",
            metadata_json={},
        ),
        BacktestRollRequestV2DTO(
            run_id="run",
            request_id="req-a",
            strategy_identifier="s1",
            strategy_instance_id="sid1",
            position_identifier="pid1",
            source_legs_json=[],
            preserved_legs_json=[],
            close_quantity=1,
            target_quantity=1,
            target_expiration_policy="x",
            target_strike_policy="x",
            requested_timestamp=ts,
            trigger="x",
            reason_code="a",
            metadata_json={},
        ),
    ]
    conversions = [
        BacktestConversionPlanV2DTO(
            run_id="run",
            conversion_id="conv-b",
            strategy_instance_id="sid2",
            source_strategy="b",
            target_strategy="c",
            legs_closed_json=[],
            legs_preserved_json=[],
            legs_opened_json=[],
            conversion_cost=None,
            compatible=True,
            warnings_json=[],
            reproducibility_json={},
        ),
        BacktestConversionPlanV2DTO(
            run_id="run",
            conversion_id="conv-a",
            strategy_instance_id="sid1",
            source_strategy="a",
            target_strategy="b",
            legs_closed_json=[],
            legs_preserved_json=[],
            legs_opened_json=[],
            conversion_cost=None,
            compatible=True,
            warnings_json=[],
            reproducibility_json={},
        ),
    ]

    first = deterministic_strategy_management_checksum(
        roll_policies=policies,
        roll_requests=requests,
        conversion_plans=conversions,
    )
    second = deterministic_strategy_management_checksum(
        roll_policies=list(reversed(policies)),
        roll_requests=list(reversed(requests)),
        conversion_plans=list(reversed(conversions)),
    )

    assert first == second


def test_strategy_management_mutation_error_type_exists() -> None:
    err = StrategyManagementMutationError("x")
    assert isinstance(err, RuntimeError)
