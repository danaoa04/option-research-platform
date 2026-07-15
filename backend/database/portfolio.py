"""Persistence services for portfolio allocation runs."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256

from backend.database.dtos import (
    PortfolioAllocationDTO,
    PortfolioClusterDTO,
    PortfolioConstraintOutcomeDTO,
    PortfolioCorrelationDTO,
    PortfolioEligibleCandidateDTO,
    PortfolioRebalancePlanDTO,
    PortfolioRejectedCandidateDTO,
    PortfolioRiskContributionDTO,
    PortfolioRunDTO,
    PortfolioScenarioDTO,
)
from backend.database.repositories.portfolio import (
    PortfolioAllocationRepository,
    PortfolioClusterRepository,
    PortfolioConstraintRepository,
    PortfolioCorrelationRepository,
    PortfolioEligibleCandidateRepository,
    PortfolioRebalancePlanRepository,
    PortfolioRejectedCandidateRepository,
    PortfolioRiskContributionRepository,
    PortfolioRunRepository,
    PortfolioScenarioRepository,
)
from backend.database.session import DatabaseSessionManager


class PortfolioMutationError(RuntimeError):
    """Raised when portfolio persistence invariants are violated."""


class PortfolioPersistenceService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_run(
        self,
        run: PortfolioRunDTO,
        *,
        eligible_candidates: list[PortfolioEligibleCandidateDTO],
        rejected_candidates: list[PortfolioRejectedCandidateDTO],
        allocations: list[PortfolioAllocationDTO],
        constraints: list[PortfolioConstraintOutcomeDTO],
        correlations: list[PortfolioCorrelationDTO],
        clusters: list[PortfolioClusterDTO],
        risk_contributions: list[PortfolioRiskContributionDTO],
        scenarios: list[PortfolioScenarioDTO],
        rebalance_plan: list[PortfolioRebalancePlanDTO],
    ) -> int:
        self._validate_run(run)
        run_payload = {
            "run_id": run.run_id,
            "problem_id": run.problem_id,
            "strategy_name": run.strategy_name,
            "allocation_problem": run.allocation_problem,
            "objectives_json": run.objective_definitions,
            "constraints_json": run.constraint_definitions,
            "correlation_policy": run.correlation_policy,
            "sizing_policy": run.sizing_policy,
            "rebalance_policy": run.rebalance_policy,
            "eligible_count": run.eligible_count,
            "rejected_count": run.rejected_count,
            "allocation_count": run.allocation_count,
            "reserve_cash": run.reserve_cash,
            "available_capital": run.available_capital,
            "checksums": run.checksums,
            "software_git_commit": run.software_git_commit,
            "schema_version": run.schema_version,
            "random_seed": run.random_seed,
            "dataset_manifests": run.dataset_manifests,
            "warnings": run.warnings,
            "failures": run.failures,
            "metadata": run.metadata_json,
            "created_at": run.created_at,
        }
        with self.session_manager.session_scope() as session:
            run_repo = PortfolioRunRepository(session)
            run_row_id = run_repo.upsert_run(run_payload)

            PortfolioEligibleCandidateRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in eligible_candidates]
            )
            PortfolioRejectedCandidateRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in rejected_candidates]
            )
            PortfolioAllocationRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in allocations]
            )
            PortfolioConstraintRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in constraints]
            )
            PortfolioCorrelationRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in correlations]
            )
            PortfolioClusterRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in clusters]
            )
            PortfolioRiskContributionRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in risk_contributions]
            )
            PortfolioScenarioRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in scenarios]
            )
            PortfolioRebalancePlanRepository(session).upsert_rows(
                [{"run_row_id": run_row_id, **asdict(item)} for item in rebalance_plan]
            )
            return run_row_id

    def _validate_run(self, run: PortfolioRunDTO) -> None:
        required = {
            "allocation_problem",
            "objective_definitions",
            "constraint_definitions",
            "correlation_policy",
            "sizing_policy",
            "rebalance_policy",
            "dataset_manifests",
        }
        missing = sorted(required.difference(run.metadata_json))
        if missing:
            raise PortfolioMutationError(
                "portfolio run is missing reproducibility metadata: "
                f"missing={missing}"
            )


def deterministic_portfolio_run_checksum(
    *,
    run: PortfolioRunDTO,
    allocations: list[PortfolioAllocationDTO],
) -> str:
    payload = {
        "run_id": run.run_id,
        "problem_id": run.problem_id,
        "eligible_count": run.eligible_count,
        "rejected_count": run.rejected_count,
        "allocation_count": run.allocation_count,
        "checksums": run.checksums,
        "allocations": [
            {
                "candidate_id": item.candidate_id,
                "weight": str(item.weight),
                "capital": str(item.capital),
                "contracts": item.contracts,
            }
            for item in sorted(allocations, key=lambda value: value.candidate_id)
        ],
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()


def decimalize(value: float) -> Decimal:
    return Decimal(str(round(value, 10)))
