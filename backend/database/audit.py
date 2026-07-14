"""Audit and lineage event service for historical data workflows."""

from __future__ import annotations

from dataclasses import asdict

from backend.database.dtos import AuditEventDTO
from backend.database.models import AuditEvent
from backend.database.repositories import AuditRepository
from backend.database.session import DatabaseSessionManager


class AuditEventService:
    """Record and query immutable audit events."""

    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def record(self, event: AuditEventDTO) -> None:
        self.record_many([event])

    def record_many(self, events: list[AuditEventDTO]) -> None:
        if not events:
            return

        with self.session_manager.session_scope() as session:
            repo = AuditRepository(session)
            repo.record_events([asdict(event) for event in events])

    def list_events(
        self,
        *,
        event_type: str | None = None,
        snapshot_id: str | None = None,
    ) -> list[AuditEvent]:
        with self.session_manager.session_scope() as session:
            repo = AuditRepository(session)
            return repo.query_events(event_type=event_type, snapshot_id=snapshot_id)
