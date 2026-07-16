"""Persistence and query services for Sprint 8C strategy management artifacts."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256

from backend.database.dtos import (
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
    StrategyManagementOptimizerContractDTO,
)
from backend.database.repositories.strategy_management import (
    BacktestBasisTransferRepository,
    BacktestConversionAnalyticsV2Repository,
    BacktestConversionExecutionRepository,
    BacktestConversionPlanV2Repository,
    BacktestManagementComparisonV2Repository,
    BacktestPartialRollStateRepository,
    BacktestRollAnalyticsV2Repository,
    BacktestRollCandidateRepository,
    BacktestRollEligibilityV2Repository,
    BacktestRollExecutionV2Repository,
    BacktestRollFillV2Repository,
    BacktestRollReconciliationV2Repository,
    BacktestRollRequestV2Repository,
    BasisHistoryQueryRepository,
    ConversionAnalyticsQueryRepository,
    ConversionHistoryQueryRepository,
    DeprecatedRollPolicyQueryRepository,
    ManagementComparisonQueryRepository,
    PartialRollStateQueryRepository,
    ReplayRollEventQueryRepository,
    RollAnalyticsQueryRepository,
    RollCandidateHistoryQueryRepository,
    RollEligibilityFailureQueryRepository,
    RollExecutionHistoryQueryRepository,
    RollHistoryQueryRepository,
    RollPolicyAliasQueryRepository,
    RollPolicyAliasRepository,
    RollPolicyQueryRepository,
    RollPolicyRegistryRepository,
    StrategyManagementChecksumRepository,
    StrategyManagementOptimizerContractRepository,
    StrategyScopeRollHistoryQueryRepository,
    UnresolvedPartialRollQueryRepository,
)
from backend.database.session import DatabaseSessionManager


class StrategyManagementMutationError(RuntimeError):
    """Raised when strategy management persistence invariants are violated."""


class StrategyManagementPersistenceService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_state(
        self,
        *,
        roll_policies: list[RollPolicyRegistryDTO],
        roll_policy_aliases: list[RollPolicyAliasDTO],
        roll_requests: list[BacktestRollRequestV2DTO],
        roll_candidates: list[BacktestRollCandidateDTO],
        roll_eligibility_results: list[BacktestRollEligibilityV2DTO],
        roll_executions: list[BacktestRollExecutionV2DTO],
        roll_fills: list[BacktestRollFillV2DTO],
        partial_roll_states: list[BacktestPartialRollStateDTO],
        roll_reconciliations: list[BacktestRollReconciliationV2DTO],
        basis_transfers: list[BacktestBasisTransferDTO],
        conversion_plans: list[BacktestConversionPlanV2DTO],
        conversion_executions: list[BacktestConversionExecutionDTO],
        management_comparisons: list[BacktestManagementComparisonV2DTO],
        roll_analytics: list[BacktestRollAnalyticsV2DTO],
        conversion_analytics: list[BacktestConversionAnalyticsV2DTO],
        optimizer_contracts: list[StrategyManagementOptimizerContractDTO],
        checksums: list[StrategyManagementChecksumDTO],
    ) -> None:
        with self.session_manager.session_scope() as session:
            RollPolicyRegistryRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in roll_policies
                ]
            )
            RollPolicyAliasRepository(session).upsert_rows(
                [asdict(item) for item in roll_policy_aliases]
            )
            BacktestRollRequestV2Repository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in roll_requests
                ]
            )
            BacktestRollCandidateRepository(session).upsert_rows(
                [asdict(item) for item in roll_candidates]
            )
            BacktestRollEligibilityV2Repository(session).upsert_rows(
                [asdict(item) for item in roll_eligibility_results]
            )
            BacktestRollExecutionV2Repository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in roll_executions
                ]
            )
            BacktestRollFillV2Repository(session).upsert_rows([asdict(item) for item in roll_fills])
            BacktestPartialRollStateRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in partial_roll_states
                ]
            )
            BacktestRollReconciliationV2Repository(session).upsert_rows(
                [asdict(item) for item in roll_reconciliations]
            )
            BacktestBasisTransferRepository(session).upsert_rows(
                [asdict(item) for item in basis_transfers]
            )
            BacktestConversionPlanV2Repository(session).upsert_rows(
                [asdict(item) for item in conversion_plans]
            )
            BacktestConversionExecutionRepository(session).upsert_rows(
                [asdict(item) for item in conversion_executions]
            )
            BacktestManagementComparisonV2Repository(session).upsert_rows(
                [asdict(item) for item in management_comparisons]
            )
            BacktestRollAnalyticsV2Repository(session).upsert_rows(
                [asdict(item) for item in roll_analytics]
            )
            BacktestConversionAnalyticsV2Repository(session).upsert_rows(
                [asdict(item) for item in conversion_analytics]
            )
            StrategyManagementOptimizerContractRepository(session).upsert_rows(
                [asdict(item) for item in optimizer_contracts]
            )
            StrategyManagementChecksumRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in checksums
                ]
            )


class StrategyManagementQueryService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def roll_policy_catalogue(self) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = RollPolicyQueryRepository(session).list_policies()
            return [
                {
                    "canonical_identifier": row.canonical_identifier,
                    "version": row.version,
                    "default_priority": row.default_priority,
                    "status": row.status,
                    "deprecated": row.deprecated,
                }
                for row in rows
            ]

    def roll_policy_details(self, policy_name: str) -> dict[str, object] | None:
        with self.session_manager.session_scope() as session:
            row = RollPolicyQueryRepository(session).by_identifier(policy_name)
            if row is None:
                alias = RollPolicyAliasQueryRepository(session).resolve(policy_name)
                if alias is None:
                    return None
                row = RollPolicyQueryRepository(session).by_identifier(alias.canonical_identifier)
                if row is None:
                    return None
            return {
                "canonical_identifier": row.canonical_identifier,
                "version": row.version,
                "aliases": row.aliases_json,
                "supported_strategy_families": row.supported_strategy_families,
                "supported_lifecycle_states": row.supported_lifecycle_states,
                "supported_exercise_styles": row.supported_exercise_styles,
                "supported_settlement_types": row.supported_settlement_types,
                "required_market_data": row.required_market_data,
                "required_volatility_data": row.required_volatility_data,
                "parameter_schema": row.parameter_schema_json,
                "status": row.status,
                "deprecated": row.deprecated,
            }

    def roll_history(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = RollHistoryQueryRepository(session).roll_history(run_id)
            return [
                {
                    "request_id": row.request_id,
                    "strategy_identifier": row.strategy_identifier,
                    "requested_timestamp": row.requested_timestamp,
                    "trigger": row.trigger,
                    "reason_code": row.reason_code,
                }
                for row in rows
            ]

    def roll_candidate_history(self, run_id: str, request_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = RollCandidateHistoryQueryRepository(session).by_request(run_id, request_id)
            return [
                {
                    "candidate_id": row.candidate_id,
                    "roll_type": row.roll_type,
                    "estimated_net_credit_or_debit": row.estimated_net_credit_or_debit,
                }
                for row in rows
            ]

    def eligibility_failures(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = RollEligibilityFailureQueryRepository(session).failures(run_id)
            return [
                {
                    "request_id": row.request_id,
                    "candidate_id": row.candidate_id,
                    "rejections": row.rejections_json,
                }
                for row in rows
            ]

    def roll_execution_history(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = RollExecutionHistoryQueryRepository(session).history(run_id)
            return [
                {
                    "execution_id": row.execution_id,
                    "plan_id": row.plan_id,
                    "execution_style": row.execution_style,
                    "all_or_none_research": row.all_or_none_research,
                }
                for row in rows
            ]

    def basis_history(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = BasisHistoryQueryRepository(session).history(run_id)
            return [
                {
                    "basis_transfer_id": row.basis_transfer_id,
                    "plan_id": row.plan_id,
                    "original_basis": row.original_basis,
                    "cumulative_credits": row.cumulative_credits,
                    "cumulative_debits": row.cumulative_debits,
                }
                for row in rows
            ]

    def conversion_history(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = ConversionHistoryQueryRepository(session).history(run_id)
            return [
                {
                    "conversion_id": row.conversion_id,
                    "source_strategy": row.source_strategy,
                    "target_strategy": row.target_strategy,
                    "conversion_cost": row.conversion_cost,
                    "compatible": row.compatible,
                }
                for row in rows
            ]

    def partial_roll_state(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = PartialRollStateQueryRepository(session).history(run_id)
            return [
                {
                    "state_id": row.state_id,
                    "plan_id": row.plan_id,
                    "temporary_naked_exposure": row.temporary_naked_exposure,
                    "residual_quantities": row.residual_quantities_json,
                    "risk_escalated": row.risk_escalated,
                    "timeout_seconds": row.timeout_seconds,
                }
                for row in rows
            ]

    def management_comparisons(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = ManagementComparisonQueryRepository(session).history(run_id)
            return [
                {
                    "comparison_id": row.comparison_id,
                    "strategy_instance_id": row.strategy_instance_id,
                    "selected_action": row.selected_action,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    def roll_analytics(self, run_id: str) -> dict[str, object] | None:
        with self.session_manager.session_scope() as session:
            row = RollAnalyticsQueryRepository(session).latest(run_id)
            if row is None:
                return None
            return {
                "analytics_id": row.analytics_id,
                "roll_metrics": row.roll_metrics_json,
                "created_at": row.created_at,
            }

    def conversion_analytics(self, run_id: str) -> dict[str, object] | None:
        with self.session_manager.session_scope() as session:
            row = ConversionAnalyticsQueryRepository(session).latest(run_id)
            if row is None:
                return None
            return {
                "analytics_id": row.analytics_id,
                "conversion_metrics": row.conversion_metrics_json,
                "created_at": row.created_at,
            }

    def pmcc_roll_history(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyScopeRollHistoryQueryRepository(session).by_strategy(
                run_id,
                "covered.pmcc",
            )
            return [
                {
                    "request_id": row.request_id,
                    "strategy_instance_id": row.strategy_instance_id,
                    "reason_code": row.reason_code,
                }
                for row in rows
            ]

    def calendar_roll_history(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyScopeRollHistoryQueryRepository(session).by_strategy(
                run_id,
                "calendar.call_calendar",
            )
            return [
                {
                    "request_id": row.request_id,
                    "strategy_instance_id": row.strategy_instance_id,
                    "reason_code": row.reason_code,
                }
                for row in rows
            ]

    def diagonal_roll_history(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyScopeRollHistoryQueryRepository(session).by_strategy(
                run_id,
                "diagonal.call_diagonal",
            )
            return [
                {
                    "request_id": row.request_id,
                    "strategy_instance_id": row.strategy_instance_id,
                    "reason_code": row.reason_code,
                }
                for row in rows
            ]

    def unresolved_partial_rolls(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = UnresolvedPartialRollQueryRepository(session).unresolved(run_id)
            return [
                {
                    "state_id": row.state_id,
                    "plan_id": row.plan_id,
                    "residual_quantities": row.residual_quantities_json,
                }
                for row in rows
            ]

    def unresolved_roll_failures(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = UnresolvedPartialRollQueryRepository(session).unresolved(run_id)
            return [
                {
                    "state_id": row.state_id,
                    "plan_id": row.plan_id,
                    "temporary_naked_exposure": row.temporary_naked_exposure,
                    "risk_escalated": row.risk_escalated,
                }
                for row in rows
            ]

    def replay_roll_events(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = ReplayRollEventQueryRepository(session).events(run_id)
            return [
                {
                    "execution_id": row.execution_id,
                    "leg_label": row.leg_label,
                    "fill_timestamp": row.fill_timestamp,
                    "fill_quantity": row.fill_quantity,
                    "fill_price": row.fill_price,
                }
                for row in rows
            ]

    def deprecated_roll_policies(self) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = DeprecatedRollPolicyQueryRepository(session).list_deprecated()
            return [
                {
                    "canonical_identifier": row.canonical_identifier,
                    "replacement_identifier": row.replacement_identifier,
                }
                for row in rows
            ]


def deterministic_strategy_management_checksum(
    *,
    roll_policies: list[RollPolicyRegistryDTO],
    roll_requests: list[BacktestRollRequestV2DTO],
    conversion_plans: list[BacktestConversionPlanV2DTO],
) -> str:
    payload = {
        "roll_policies": [
            {
                "canonical_identifier": item.canonical_identifier,
                "version": item.version,
                "status": item.status,
            }
            for item in sorted(roll_policies, key=lambda row: row.canonical_identifier)
        ],
        "roll_requests": [
            {
                "request_id": item.request_id,
                "strategy_identifier": item.strategy_identifier,
                "reason_code": item.reason_code,
            }
            for item in sorted(roll_requests, key=lambda row: row.request_id)
        ],
        "conversion_plans": [
            {
                "conversion_id": item.conversion_id,
                "source_strategy": item.source_strategy,
                "target_strategy": item.target_strategy,
            }
            for item in sorted(conversion_plans, key=lambda row: row.conversion_id)
        ],
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()
