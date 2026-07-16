"""Persistence and query services for Sprint 8B strategy policy artifacts."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256

from backend.database.dtos import (
    StrategyPolicyAliasDTO,
    StrategyPolicyChecksumDTO,
    StrategyPolicyConflictDTO,
    StrategyPolicyEvaluationDTO,
    StrategyPolicyRegistryDTO,
    StrategyPolicySetVersionDTO,
)
from backend.database.repositories.strategy_policy_library import (
    StrategyPolicyAliasQueryRepository,
    StrategyPolicyAliasRepository,
    StrategyPolicyChecksumRepository,
    StrategyPolicyConflictQueryRepository,
    StrategyPolicyConflictRepository,
    StrategyPolicyEvaluationQueryRepository,
    StrategyPolicyEvaluationRepository,
    StrategyPolicyQueryRepository,
    StrategyPolicyRegistryRepository,
    StrategyPolicySetQueryRepository,
    StrategyPolicySetVersionRepository,
)
from backend.database.session import DatabaseSessionManager


class StrategyPolicyMutationError(RuntimeError):
    """Raised when strategy policy persistence invariants are violated."""


class StrategyPolicyPersistenceService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_policy_state(
        self,
        *,
        policies: list[StrategyPolicyRegistryDTO],
        aliases: list[StrategyPolicyAliasDTO],
        policy_sets: list[StrategyPolicySetVersionDTO],
        evaluations: list[StrategyPolicyEvaluationDTO],
        conflicts: list[StrategyPolicyConflictDTO],
        checksums: list[StrategyPolicyChecksumDTO],
    ) -> None:
        with self.session_manager.session_scope() as session:
            StrategyPolicyRegistryRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in policies
                ]
            )
            StrategyPolicyAliasRepository(session).upsert_rows([asdict(item) for item in aliases])
            StrategyPolicySetVersionRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in policy_sets
                ]
            )
            StrategyPolicyEvaluationRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in evaluations
                ]
            )
            StrategyPolicyConflictRepository(session).upsert_rows(
                [asdict(item) for item in conflicts]
            )
            StrategyPolicyChecksumRepository(session).upsert_rows(
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


class StrategyPolicyQueryService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def list_policies(
        self,
        *,
        family: str | None = None,
        include_deprecated: bool = True,
    ) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyPolicyQueryRepository(session).list_policies(
                family=family,
                include_deprecated=include_deprecated,
            )
            return [
                {
                    "policy_id": row.policy_id,
                    "policy_name": row.policy_name,
                    "policy_family": row.policy_family,
                    "policy_version": row.policy_version,
                    "priority": row.priority,
                    "required_data": row.required_data,
                    "supported_strategies": row.supported_strategies,
                    "deprecated": row.deprecated,
                }
                for row in rows
            ]

    def policy_by_identifier(self, policy_name: str) -> dict[str, object] | None:
        with self.session_manager.session_scope() as session:
            row = StrategyPolicyQueryRepository(session).by_policy_id(policy_name)
            if row is None:
                alias = StrategyPolicyAliasQueryRepository(session).resolve(policy_name)
                if alias is None:
                    return None
                row = StrategyPolicyQueryRepository(session).by_policy_id(alias.policy_id)
                if row is None:
                    return None
            return {
                "policy_id": row.policy_id,
                "policy_name": row.policy_name,
                "policy_family": row.policy_family,
                "policy_version": row.policy_version,
                "priority": row.priority,
                "parameters_json": row.parameters_json,
                "required_data": row.required_data,
                "supported_strategies": row.supported_strategies,
                "tags": row.tags,
                "deprecated": row.deprecated,
                "replacement_policy_id": row.replacement_policy_id,
            }

    def policy_set(self, *, set_id: str, set_version: str) -> dict[str, object] | None:
        with self.session_manager.session_scope() as session:
            row = StrategyPolicySetQueryRepository(session).by_key(
                set_id=set_id,
                set_version=set_version,
            )
            if row is None:
                return None
            return {
                "set_id": row.set_id,
                "set_version": row.set_version,
                "strategy_identifier": row.strategy_identifier,
                "conflict_mode": row.conflict_mode,
                "entry_policies": row.entry_policies,
                "exit_policies": row.exit_policies,
                "management_policies": row.management_policies,
                "earnings_policies": row.earnings_policies,
                "dividend_policies": row.dividend_policies,
                "roll_policies": row.roll_policies,
            }

    def strategy_policy_sets(self, strategy_identifier: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyPolicySetQueryRepository(session).by_strategy(strategy_identifier)
            return [
                {
                    "set_id": row.set_id,
                    "set_version": row.set_version,
                    "strategy_identifier": row.strategy_identifier,
                    "conflict_mode": row.conflict_mode,
                }
                for row in rows
            ]

    def run_policy_evaluations(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyPolicyEvaluationQueryRepository(session).by_run(run_id)
            return [
                {
                    "run_id": row.run_id,
                    "evaluation_id": row.evaluation_id,
                    "policy_id": row.policy_id,
                    "passed": row.passed,
                    "reason_code": row.reason_code,
                    "event_timestamp": row.event_timestamp,
                    "confidence": float(row.confidence),
                }
                for row in rows
            ]

    def run_policy_conflicts(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyPolicyConflictQueryRepository(session).by_run(run_id)
            return [
                {
                    "run_id": row.run_id,
                    "conflict_id": row.conflict_id,
                    "winning_policy_id": row.winning_policy_id,
                    "event_timestamp": row.event_timestamp,
                }
                for row in rows
            ]


def deterministic_strategy_policy_state_checksum(
    *,
    policies: list[StrategyPolicyRegistryDTO],
    policy_sets: list[StrategyPolicySetVersionDTO],
) -> str:
    payload = {
        "policies": [
            {
                "policy_id": item.policy_id,
                "policy_version": item.policy_version,
                "policy_family": item.policy_family,
                "priority": item.priority,
            }
            for item in sorted(policies, key=lambda row: row.policy_id)
        ],
        "policy_sets": [
            {
                "set_id": item.set_id,
                "set_version": item.set_version,
                "strategy_identifier": item.strategy_identifier,
                "conflict_mode": item.conflict_mode,
            }
            for item in sorted(policy_sets, key=lambda row: (row.set_id, row.set_version))
        ],
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()
