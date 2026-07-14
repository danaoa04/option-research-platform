"""Dataset snapshot and reproducibility services."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from backend.database.dtos import DatasetSnapshotDTO
from backend.database.repositories import SnapshotRepository
from backend.database.session import DatabaseSessionManager


class SnapshotMutationError(RuntimeError):
    """Raised when attempting to mutate immutable snapshot state."""


class SnapshotService:
    """Create, verify, and compare immutable dataset snapshots."""

    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def create_snapshot(self, snapshot: DatasetSnapshotDTO) -> None:
        payload = asdict(snapshot)
        source_manifest_ids = list(payload.pop("source_manifest_ids", []))
        payload["created_at"] = payload.get("created_at") or datetime.now(UTC)

        with self.session_manager.session_scope() as session:
            repo = SnapshotRepository(session)
            repo.create_snapshot(payload)
            repo.add_source_manifests(snapshot.id, source_manifest_ids)

    def get_snapshot(self, snapshot_id: str) -> DatasetSnapshotDTO | None:
        with self.session_manager.session_scope() as session:
            repo = SnapshotRepository(session)
            row = repo.get_snapshot(snapshot_id)
            if row is None:
                return None
            source_manifest_ids = repo.list_source_manifests(snapshot_id)
            return DatasetSnapshotDTO(
                id=row.id,
                manifest_id=row.manifest_id,
                provider_id=row.provider_id,
                schema_version=row.schema_version,
                dataset_version=row.dataset_version,
                git_commit=row.git_commit,
                date_start=row.date_start,
                date_end=row.date_end,
                symbol_scope=list(row.symbol_scope),
                row_counts=dict(row.row_counts),
                checksums=dict(row.checksums),
                transformation_history=list(row.transformation_history),
                validation_summary=dict(row.validation_summary),
                created_at=row.created_at,
                parent_snapshot_id=row.parent_snapshot_id,
                status=row.status,
                source_manifest_ids=source_manifest_ids,
            )

    def verify_snapshot(self, snapshot_id: str) -> tuple[bool, str]:
        snapshot = self.get_snapshot(snapshot_id)
        if snapshot is None:
            return False, "snapshot_not_found"

        digest = self._deterministic_digest(snapshot)
        expected = snapshot.checksums.get("snapshot_digest")
        if expected is None:
            return False, "missing_snapshot_digest"
        return digest == expected, digest

    def compare_snapshots(self, left_snapshot_id: str, right_snapshot_id: str) -> dict[str, Any]:
        left = self.get_snapshot(left_snapshot_id)
        right = self.get_snapshot(right_snapshot_id)
        if left is None or right is None:
            return {
                "comparable": False,
                "reason": "snapshot_not_found",
                "left": left_snapshot_id,
                "right": right_snapshot_id,
            }

        return {
            "comparable": True,
            "left": left_snapshot_id,
            "right": right_snapshot_id,
            "dataset_version_changed": left.dataset_version != right.dataset_version,
            "schema_version_changed": left.schema_version != right.schema_version,
            "row_count_delta": _delta(left.row_counts, right.row_counts),
            "checksum_changes": _checksum_changes(left.checksums, right.checksums),
            "source_manifest_delta": sorted(
                set(right.source_manifest_ids).symmetric_difference(left.source_manifest_ids)
            ),
        }

    def reject_snapshot_mutation(self, snapshot_id: str) -> None:
        snapshot = self.get_snapshot(snapshot_id)
        if snapshot is None:
            raise SnapshotMutationError("snapshot does not exist")
        raise SnapshotMutationError(
            "snapshots are immutable; create a new derived snapshot instead"
        )

    def _deterministic_digest(self, snapshot: DatasetSnapshotDTO) -> str:
        checksum_inputs = {
            key: value
            for key, value in snapshot.checksums.items()
            if key != "snapshot_digest"
        }
        material = {
            "id": snapshot.id,
            "manifest_id": snapshot.manifest_id,
            "provider_id": snapshot.provider_id,
            "schema_version": snapshot.schema_version,
            "dataset_version": snapshot.dataset_version,
            "git_commit": snapshot.git_commit,
            "date_start": snapshot.date_start.isoformat(),
            "date_end": snapshot.date_end.isoformat(),
            "symbol_scope": sorted(snapshot.symbol_scope),
            "row_counts": dict(sorted(snapshot.row_counts.items())),
            "checksums": dict(sorted(checksum_inputs.items())),
            "source_manifest_ids": sorted(snapshot.source_manifest_ids),
        }
        encoded = repr(material).encode("utf-8")
        return sha256(encoded).hexdigest()


def _delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, float]:
    keys = sorted(set(left).union(right))
    changes: dict[str, float] = {}
    for key in keys:
        left_val = float(left.get(key, 0.0))
        right_val = float(right.get(key, 0.0))
        if left_val != right_val:
            changes[key] = right_val - left_val
    return changes


def _checksum_changes(left: dict[str, Any], right: dict[str, Any]) -> dict[str, dict[str, str]]:
    changes: dict[str, dict[str, str]] = {}
    for key in sorted(set(left).union(right)):
        left_val = str(left.get(key, ""))
        right_val = str(right.get(key, ""))
        if left_val != right_val:
            changes[key] = {"left": left_val, "right": right_val}
    return changes
