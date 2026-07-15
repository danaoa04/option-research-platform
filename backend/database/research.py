"""Persistence services for calendar and multi-expiry research runs."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256

from backend.database.dtos import ResearchOpportunityDTO, ResearchRunDTO
from backend.database.repositories import ResearchOpportunityRepository, ResearchRunRepository
from backend.database.session import DatabaseSessionManager


class ResearchMutationError(RuntimeError):
    """Raised when research persistence invariants are violated."""


class ResearchPersistenceService:
    """Persist deterministic research runs and opportunity snapshots."""

    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_run(self, run: ResearchRunDTO, opportunities: list[ResearchOpportunityDTO]) -> int:
        with self.session_manager.session_scope() as session:
            run_repo = ResearchRunRepository(session)
            opp_repo = ResearchOpportunityRepository(session)

            run_row_id = run_repo.upsert_run(asdict(run))
            opportunity_rows = [
                {
                    "run_row_id": run_row_id,
                    **asdict(item),
                }
                for item in opportunities
            ]
            opp_repo.upsert_opportunities(opportunity_rows)
            return run_row_id


def deterministic_research_checksum(
    *,
    run: ResearchRunDTO,
    opportunities: list[ResearchOpportunityDTO],
) -> str:
    normalized = {
        "run_id": run.run_id,
        "symbol": run.symbol,
        "strategy_type": run.strategy_type,
        "entry_date": run.entry_date.isoformat(),
        "exit_date": run.exit_date.isoformat(),
        "manifest_id": run.manifest_id,
        "run_timestamp": run.run_timestamp.isoformat(),
        "summary_metrics": dict(sorted(run.summary_metrics.items())),
        "opportunities": sorted(
            (
                item.as_of_timestamp.isoformat(),
                str(Decimal(str(item.opportunity_score))),
                str(Decimal(str(item.confidence))),
                item.term_structure_regime or "",
            )
            for item in opportunities
        ),
    }
    return sha256(repr(normalized).encode("utf-8")).hexdigest()


__all__ = [
    "ResearchMutationError",
    "ResearchPersistenceService",
    "deterministic_research_checksum",
]
