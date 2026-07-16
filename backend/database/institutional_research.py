"""Persistence for versioned Sprint 9C research artifacts."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC

from sqlalchemy import select

from backend.database.dtos import InstitutionalResearchArtifactDTO
from backend.database.models.entities import InstitutionalResearchArtifactRecord
from backend.database.session import DatabaseSessionManager


class InstitutionalResearchPersistenceService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store(self, artifact: InstitutionalResearchArtifactDTO) -> None:
        with self.session_manager.session_scope() as session:
            row = session.scalar(
                select(InstitutionalResearchArtifactRecord).where(
                    InstitutionalResearchArtifactRecord.artifact_id == artifact.artifact_id
                )
            )
            values = asdict(artifact)
            if row is None:
                session.add(InstitutionalResearchArtifactRecord(**values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)

    def by_experiment(self, experiment_id: str) -> list[InstitutionalResearchArtifactDTO]:
        with self.session_manager.session_scope() as session:
            rows = session.scalars(
                select(InstitutionalResearchArtifactRecord)
                .where(InstitutionalResearchArtifactRecord.experiment_id == experiment_id)
                .order_by(InstitutionalResearchArtifactRecord.created_at)
            ).all()
            return [
                InstitutionalResearchArtifactDTO(
                    artifact_id=row.artifact_id,
                    experiment_id=row.experiment_id,
                    artifact_kind=row.artifact_kind,
                    schema_version=row.schema_version,
                    payload_json=row.payload_json,
                    metadata_json=row.metadata_json,
                    replay_links=row.replay_links,
                    created_at=row.created_at.replace(tzinfo=UTC)
                    if row.created_at.tzinfo is None
                    else row.created_at,
                )
                for row in rows
            ]
