"""Volatility persistence and no-look-ahead query services."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from typing import cast

from backend.database.dtos import (
    VolatilityObservationDTO,
    VolatilityTimeSliceDTO,
)
from backend.database.repositories import (
    VolatilityObservationRepository,
    VolatilitySliceRepository,
)
from backend.database.session import DatabaseSessionManager


class VolatilitySliceMutationError(RuntimeError):
    """Raised when mutating finalized volatility slices."""


class VolatilityPersistenceService:
    """Store raw IV observations and immutable volatility analytics slices."""

    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_observations(self, observations: list[VolatilityObservationDTO]) -> None:
        rows = [asdict(item) for item in observations]
        with self.session_manager.session_scope() as session:
            repo = VolatilityObservationRepository(session)
            repo.upsert_observations(rows)

    def create_slice(self, payload: VolatilityTimeSliceDTO, nodes: list[dict[str, object]]) -> int:
        with self.session_manager.session_scope() as session:
            repo = VolatilitySliceRepository(session)
            row = asdict(payload)
            slice_row_id = repo.create_slice(row)
            node_rows = [dict(node, slice_id=slice_row_id) for node in nodes]
            repo.add_nodes(node_rows)
            return slice_row_id

    def finalize_slice(self, slice_id: str) -> None:
        with self.session_manager.session_scope() as session:
            repo = VolatilitySliceRepository(session)
            existing = repo.get_slice(slice_id)
            if existing is None:
                raise VolatilitySliceMutationError("slice not found")
            if existing.status == "finalized":
                raise VolatilitySliceMutationError("slice is already finalized")
            repo.finalize_slice(slice_id)

    def get_slice(
        self,
        slice_id: str,
    ) -> tuple[VolatilityTimeSliceDTO, list[dict[str, object]]] | None:
        with self.session_manager.session_scope() as session:
            repo = VolatilitySliceRepository(session)
            row = repo.get_slice(slice_id)
            if row is None:
                return None
            nodes = repo.list_nodes(row.id)
            dto = VolatilityTimeSliceDTO(
                slice_id=row.slice_id,
                symbol=row.symbol,
                valuation_timestamp=row.valuation_timestamp,
                slice_kind=row.slice_kind,
                status=row.status,
                input_manifests=list(row.input_manifests),
                solver_metadata=dict(row.solver_metadata),
                filtering_policy=dict(row.filtering_policy),
                interpolation_policy=dict(row.interpolation_policy),
                tree_step_policy=dict(row.tree_step_policy),
                quality_thresholds=dict(row.quality_thresholds),
                node_count=row.node_count,
                excluded_observation_count=row.excluded_observation_count,
                checksums=dict(row.checksums),
                git_commit=row.git_commit,
                created_at=row.created_at,
                parent_snapshot_id=row.parent_snapshot_id,
            )
            mapped_nodes = [
                {
                    "id": node.id,
                    "tenor_days": node.tenor_days,
                    "x": float(node.x),
                    "implied_volatility": float(node.implied_volatility),
                    "node_kind": node.node_kind,
                    "confidence_score": float(node.confidence_score),
                    "provenance": dict(node.provenance),
                }
                for node in nodes
            ]
            return dto, mapped_nodes

    def nearest_prior_slice(
        self,
        *,
        symbol: str,
        as_of: datetime,
        slice_kind: str,
    ) -> VolatilityTimeSliceDTO | None:
        with self.session_manager.session_scope() as session:
            repo = VolatilitySliceRepository(session)
            row = repo.find_nearest_prior_slice(symbol=symbol, as_of=as_of, slice_kind=slice_kind)
            if row is None:
                return None
            return VolatilityTimeSliceDTO(
                slice_id=row.slice_id,
                symbol=row.symbol,
                valuation_timestamp=row.valuation_timestamp,
                slice_kind=row.slice_kind,
                status=row.status,
                input_manifests=list(row.input_manifests),
                solver_metadata=dict(row.solver_metadata),
                filtering_policy=dict(row.filtering_policy),
                interpolation_policy=dict(row.interpolation_policy),
                tree_step_policy=dict(row.tree_step_policy),
                quality_thresholds=dict(row.quality_thresholds),
                node_count=row.node_count,
                excluded_observation_count=row.excluded_observation_count,
                checksums=dict(row.checksums),
                git_commit=row.git_commit,
                created_at=row.created_at,
                parent_snapshot_id=row.parent_snapshot_id,
            )


def deterministic_slice_checksum(
    *,
    payload: VolatilityTimeSliceDTO,
    nodes: list[dict[str, object]],
) -> str:
    def _node_key(item: dict[str, object]) -> tuple[int, str, str, str]:
        return (
            int(cast(int | str | float, item["tenor_days"])),
            str(Decimal(str(cast(object, item["x"])))),
            str(Decimal(str(cast(object, item["implied_volatility"])))),
            str(cast(object, item["node_kind"])),
        )

    material = {
        "slice_id": payload.slice_id,
        "symbol": payload.symbol,
        "valuation_timestamp": payload.valuation_timestamp.isoformat(),
        "slice_kind": payload.slice_kind,
        "input_manifests": sorted(payload.input_manifests),
        "node_count": payload.node_count,
        "nodes": sorted(_node_key(item) for item in nodes),
    }
    return sha256(repr(material).encode("utf-8")).hexdigest()
