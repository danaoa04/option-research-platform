"""Durable SQLAlchemy models and repository for shared provider operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from .models.base import Base


class ProviderJobEntity(Base):
    __tablename__ = "provider_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    request_checksum: Mapped[str] = mapped_column(String(64), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ProviderJobEventEntity(Base):
    __tablename__ = "provider_job_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("provider_jobs.job_id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    __table_args__ = (UniqueConstraint("job_id", "sequence"),)


class ProviderCheckpointEntity(Base):
    __tablename__ = "provider_checkpoints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("provider_jobs.job_id", ondelete="CASCADE"), index=True
    )
    checkpoint_id: Mapped[str] = mapped_column(String(128))
    ordinal: Mapped[int] = mapped_column(Integer)
    continuation: Mapped[str | None] = mapped_column(String(512))
    response_checksum: Mapped[str] = mapped_column(String(64), index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("job_id", "checkpoint_id"),)


class ProviderFailureEntity(Base):
    __tablename__ = "provider_failures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("provider_jobs.job_id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(String(2048))
    retryable: Mapped[bool] = mapped_column(Boolean)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class ProviderArtifactEntity(Base):
    """Immutable typed operational artifact (catalogue, certification, merge, monitoring, etc.)."""

    __tablename__ = "provider_operational_artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    job_id: Mapped[str | None] = mapped_column(
        ForeignKey("provider_jobs.job_id", ondelete="CASCADE"), index=True
    )
    artifact_kind: Mapped[str] = mapped_column(String(64), index=True)
    schema_version: Mapped[str] = mapped_column(String(32))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ProviderOperationsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_job(
        self, job_id: str, provider: str, checksum: str, metadata: dict[str, Any]
    ) -> ProviderJobEntity:
        existing = self.session.scalar(
            select(ProviderJobEntity).where(ProviderJobEntity.job_id == job_id)
        )
        if existing:
            if existing.request_checksum != checksum:
                raise ValueError("Job checksum conflict")
            return existing
        entity = ProviderJobEntity(
            job_id=job_id,
            provider=provider,
            status="planned",
            request_checksum=checksum,
            metadata_json=metadata,
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def append_event(
        self, job_id: str, status: str, metadata: dict[str, Any] | None = None
    ) -> ProviderJobEventEntity:
        sequence = len(self.events(job_id)) + 1
        event = ProviderJobEventEntity(
            job_id=job_id, sequence=sequence, status=status, metadata_json=metadata or {}
        )
        self.session.add(event)
        job = self.session.scalar(
            select(ProviderJobEntity).where(ProviderJobEntity.job_id == job_id)
        )
        if job is None:
            raise KeyError(job_id)
        job.status = status
        job.cancelled = status == "cancelled"
        self.session.flush()
        return event

    def events(self, job_id: str) -> list[ProviderJobEventEntity]:
        return list(
            self.session.scalars(
                select(ProviderJobEventEntity)
                .where(ProviderJobEventEntity.job_id == job_id)
                .order_by(ProviderJobEventEntity.sequence)
            )
        )

    def unresolved_failures(self, provider: str | None = None) -> list[ProviderFailureEntity]:
        statement = select(ProviderFailureEntity).where(ProviderFailureEntity.resolved.is_(False))
        if provider:
            statement = statement.where(ProviderFailureEntity.provider == provider)
        return list(self.session.scalars(statement.order_by(ProviderFailureEntity.id)))

    def persist_artifact(
        self,
        artifact_id: str,
        provider: str,
        kind: str,
        payload: dict[str, Any],
        checksum: str,
        *,
        job_id: str | None = None,
        schema_version: str = "1.0.0",
    ) -> ProviderArtifactEntity:
        existing = self.session.scalar(
            select(ProviderArtifactEntity).where(ProviderArtifactEntity.artifact_id == artifact_id)
        )
        if existing:
            if existing.checksum != checksum:
                raise ValueError("Immutable provider artifact checksum conflict")
            return existing
        artifact = ProviderArtifactEntity(
            artifact_id=artifact_id,
            provider=provider,
            job_id=job_id,
            artifact_kind=kind,
            schema_version=schema_version,
            payload_json=payload,
            checksum=checksum,
        )
        self.session.add(artifact)
        self.session.flush()
        return artifact

    def artifacts(self, kind: str, provider: str | None = None) -> list[ProviderArtifactEntity]:
        statement = select(ProviderArtifactEntity).where(
            ProviderArtifactEntity.artifact_kind == kind
        )
        if provider:
            statement = statement.where(ProviderArtifactEntity.provider == provider)
        return list(self.session.scalars(statement.order_by(ProviderArtifactEntity.artifact_id)))
