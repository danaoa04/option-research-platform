"""Repositories for corporate-action processing, snapshots, and audit lineage."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import Select, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import (
    AdjustedOptionContractView,
    AdjustedUnderlyingPriceView,
    AuditEvent,
    DatasetSnapshot,
    NormalizedCorporateAction,
    RawVendorRecord,
    SnapshotSourceManifest,
    SymbolHistory,
)

from .base import RepositoryBase


class CorporateActionNormalizationRepository(RepositoryBase[NormalizedCorporateAction]):
    """Persistence access for raw and normalized corporate-action records."""

    def insert_raw_records(self, records: Sequence[dict[str, object]]) -> None:
        if not records:
            return
        stmt = sqlite_insert(RawVendorRecord).values(list(records))
        self.session.execute(
            stmt.on_conflict_do_nothing(
                index_elements=[
                    RawVendorRecord.provider_id,
                    RawVendorRecord.entity_type,
                    RawVendorRecord.provider_record_id,
                    RawVendorRecord.checksum,
                ]
            )
        )

    def upsert_normalized_actions(self, records: Sequence[dict[str, object]]) -> None:
        if not records:
            return
        stmt = sqlite_insert(NormalizedCorporateAction).values(list(records))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    NormalizedCorporateAction.provider_id,
                    NormalizedCorporateAction.provider_action_id,
                ],
                set_={
                    "action_type": stmt.excluded.action_type,
                    "effective_date": stmt.excluded.effective_date,
                    "announcement_timestamp": stmt.excluded.announcement_timestamp,
                    "ratio": stmt.excluded.ratio,
                    "cash_amount": stmt.excluded.cash_amount,
                    "multiplier_after": stmt.excluded.multiplier_after,
                    "deliverable_after": stmt.excluded.deliverable_after,
                    "terms": stmt.excluded.terms,
                    "source_metadata": stmt.excluded.source_metadata,
                    "normalized_at": stmt.excluded.normalized_at,
                    "manifest_id": stmt.excluded.manifest_id,
                },
            )
        )

    def upsert_symbol_history(self, records: Sequence[dict[str, object]]) -> None:
        if not records:
            return
        stmt = sqlite_insert(SymbolHistory).values(list(records))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    SymbolHistory.underlying_id,
                    SymbolHistory.old_symbol,
                    SymbolHistory.new_symbol,
                    SymbolHistory.effective_date,
                ],
                set_={
                    "announcement_timestamp": stmt.excluded.announcement_timestamp,
                    "source_action_id": stmt.excluded.source_action_id,
                    "source_metadata": stmt.excluded.source_metadata,
                },
            )
        )

    def upsert_adjusted_underlying_views(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        stmt = sqlite_insert(AdjustedUnderlyingPriceView).values(list(rows))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    AdjustedUnderlyingPriceView.underlying_id,
                    AdjustedUnderlyingPriceView.price_timestamp,
                    AdjustedUnderlyingPriceView.view_name,
                    AdjustedUnderlyingPriceView.policy_name,
                ],
                set_={
                    "base_price": stmt.excluded.base_price,
                    "adjusted_price": stmt.excluded.adjusted_price,
                    "source_action_id": stmt.excluded.source_action_id,
                    "adjustment_details": stmt.excluded.adjustment_details,
                    "source_price_id": stmt.excluded.source_price_id,
                },
            )
        )

    def upsert_adjusted_option_views(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        stmt = sqlite_insert(AdjustedOptionContractView).values(list(rows))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    AdjustedOptionContractView.contract_id,
                    AdjustedOptionContractView.as_of_date,
                    AdjustedOptionContractView.view_name,
                    AdjustedOptionContractView.policy_name,
                ],
                set_={
                    "adjusted_strike": stmt.excluded.adjusted_strike,
                    "adjusted_multiplier": stmt.excluded.adjusted_multiplier,
                    "deliverable_after": stmt.excluded.deliverable_after,
                    "source_action_id": stmt.excluded.source_action_id,
                    "adjustment_details": stmt.excluded.adjustment_details,
                },
            )
        )

    def actions_for_underlying(self, underlying_id: int) -> list[NormalizedCorporateAction]:
        stmt: Select[tuple[NormalizedCorporateAction]] = select(NormalizedCorporateAction).where(
            NormalizedCorporateAction.underlying_id == underlying_id
        )
        return list(self.session.execute(stmt).scalars())

    def resolve_symbol(self, symbol: str, as_of_date: date) -> str:
        stmt: Select[tuple[SymbolHistory]] = (
            select(SymbolHistory)
            .where(
                SymbolHistory.old_symbol == symbol,
                SymbolHistory.effective_date <= as_of_date,
            )
            .order_by(SymbolHistory.effective_date.desc())
        )
        row = self.session.execute(stmt).scalars().first()
        return row.new_symbol if row else symbol


class SnapshotRepository(RepositoryBase[DatasetSnapshot]):
    """Persistence access for immutable dataset snapshots and verification."""

    def create_snapshot(self, payload: dict[str, object]) -> None:
        stmt = sqlite_insert(DatasetSnapshot).values(payload)
        self.session.execute(stmt)

    def add_source_manifests(self, snapshot_id: str, source_manifest_ids: Sequence[int]) -> None:
        if not source_manifest_ids:
            return
        values = [
            {"snapshot_id": snapshot_id, "source_manifest_id": source_manifest_id}
            for source_manifest_id in source_manifest_ids
        ]
        stmt = sqlite_insert(SnapshotSourceManifest).values(values)
        self.session.execute(
            stmt.on_conflict_do_nothing(
                index_elements=[
                    SnapshotSourceManifest.snapshot_id,
                    SnapshotSourceManifest.source_manifest_id,
                ]
            )
        )

    def get_snapshot(self, snapshot_id: str) -> DatasetSnapshot | None:
        return self.session.get(DatasetSnapshot, snapshot_id)

    def list_source_manifests(self, snapshot_id: str) -> list[int]:
        stmt: Select[tuple[int]] = select(SnapshotSourceManifest.source_manifest_id).where(
            SnapshotSourceManifest.snapshot_id == snapshot_id
        )
        return list(self.session.execute(stmt).scalars())

    def set_snapshot_status(self, snapshot_id: str, status: str) -> None:
        stmt = (
            update(DatasetSnapshot).where(DatasetSnapshot.id == snapshot_id).values(status=status)
        )
        self.session.execute(stmt)


class AuditRepository(RepositoryBase[AuditEvent]):
    """Append-only audit event repository."""

    def record_events(self, events: Sequence[dict[str, object]]) -> None:
        if not events:
            return
        stmt = sqlite_insert(AuditEvent).values(list(events))
        self.session.execute(stmt)

    def query_events(
        self,
        *,
        event_type: str | None = None,
        snapshot_id: str | None = None,
    ) -> list[AuditEvent]:
        stmt: Select[tuple[AuditEvent]] = select(AuditEvent)
        if event_type is not None:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if snapshot_id is not None:
            stmt = stmt.where(AuditEvent.snapshot_id == snapshot_id)
        stmt = stmt.order_by(AuditEvent.event_timestamp.asc())
        return list(self.session.execute(stmt).scalars())
