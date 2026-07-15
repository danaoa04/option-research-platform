"""Repositories for calendar and multi-expiry research persistence/query."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import ResearchOpportunity, ResearchRun

from .base import RepositoryBase


class ResearchRunRepository(RepositoryBase[ResearchRun]):
    def upsert_run(self, payload: dict[str, object]) -> int:
        stmt = sqlite_insert(ResearchRun).values(payload)
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[ResearchRun.run_id],
                set_={
                    "configuration": stmt.excluded.configuration,
                    "parameters": stmt.excluded.parameters,
                    "checksums": stmt.excluded.checksums,
                    "quality_score": stmt.excluded.quality_score,
                    "summary_metrics": stmt.excluded.summary_metrics,
                    "metadata_json": stmt.excluded.metadata_json,
                },
            )
        )
        run_id = payload.get("run_id")
        assert isinstance(run_id, str)
        row = self.get_run_by_id(run_id)
        assert row is not None
        return row.id

    def get_run_by_id(self, run_id: str) -> ResearchRun | None:
        stmt: Select[tuple[ResearchRun]] = select(ResearchRun).where(ResearchRun.run_id == run_id)
        return self.session.execute(stmt).scalars().first()


class ResearchOpportunityRepository(RepositoryBase[ResearchOpportunity]):
    def upsert_opportunities(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        stmt = sqlite_insert(ResearchOpportunity).values(list(rows))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    ResearchOpportunity.run_row_id,
                    ResearchOpportunity.as_of_timestamp,
                ],
                set_={
                    "opportunity_score": stmt.excluded.opportunity_score,
                    "confidence": stmt.excluded.confidence,
                    "historical_pop": stmt.excluded.historical_pop,
                    "expected_value": stmt.excluded.expected_value,
                    "theta_capture": stmt.excluded.theta_capture,
                    "quality_score": stmt.excluded.quality_score,
                    "term_structure_regime": stmt.excluded.term_structure_regime,
                    "diagnostics": stmt.excluded.diagnostics,
                    "warnings": stmt.excluded.warnings,
                },
            )
        )

    def top_opportunities(
        self,
        *,
        as_of: datetime,
        limit: int,
    ) -> list[ResearchOpportunity]:
        stmt: Select[tuple[ResearchOpportunity]] = (
            select(ResearchOpportunity)
            .where(ResearchOpportunity.as_of_timestamp <= as_of)
            .order_by(ResearchOpportunity.opportunity_score.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars())
