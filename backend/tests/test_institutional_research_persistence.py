from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine

from backend.database import (
    InstitutionalResearchArtifactDTO,
    InstitutionalResearchPersistenceService,
)
from backend.database.models import Base
from backend.database.session import DatabaseSessionManager


def test_institutional_artifact_round_trip_links_reports_to_replay() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    service = InstitutionalResearchPersistenceService(DatabaseSessionManager(engine))
    artifact = InstitutionalResearchArtifactDTO(
        artifact_id="report-1",
        experiment_id="experiment-1",
        artifact_kind="portfolio_report",
        schema_version="v1",
        payload_json={"executive_summary": "offline"},
        metadata_json={"format": "json"},
        replay_links=[{"kind": "decision", "id": "decision-1"}],
        created_at=datetime(2026, 7, 16, tzinfo=UTC),
    )
    service.store(artifact)
    assert service.by_experiment("experiment-1") == [artifact]
