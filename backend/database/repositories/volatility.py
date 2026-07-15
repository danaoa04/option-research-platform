"""Repositories for volatility observations and persisted time slices."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import (
    VolatilityObservation,
    VolatilityTimeSlice,
    VolatilityTimeSliceNode,
)

from .base import RepositoryBase


class VolatilityObservationRepository(RepositoryBase[VolatilityObservation]):
    def upsert_observations(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        stmt = sqlite_insert(VolatilityObservation).values(list(rows))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    VolatilityObservation.symbol,
                    VolatilityObservation.valuation_timestamp,
                    VolatilityObservation.expiration,
                    VolatilityObservation.strike,
                    VolatilityObservation.option_type,
                    VolatilityObservation.quote_source,
                    VolatilityObservation.pricing_model,
                    VolatilityObservation.manifest_id,
                ],
                set_={
                    "solver_method": stmt.excluded.solver_method,
                    "solver_status": stmt.excluded.solver_status,
                    "pricing_error": stmt.excluded.pricing_error,
                    "bid": stmt.excluded.bid,
                    "ask": stmt.excluded.ask,
                    "midpoint": stmt.excluded.midpoint,
                    "spread_width": stmt.excluded.spread_width,
                    "volume": stmt.excluded.volume,
                    "open_interest": stmt.excluded.open_interest,
                    "stale_age_seconds": stmt.excluded.stale_age_seconds,
                    "quality_score": stmt.excluded.quality_score,
                    "quality_flags": stmt.excluded.quality_flags,
                    "solver_metadata": stmt.excluded.solver_metadata,
                },
            )
        )

    def query_observations(
        self,
        *,
        symbol: str,
        start_ts: datetime,
        end_ts: datetime,
        min_quality_score: float | None = None,
    ) -> list[VolatilityObservation]:
        stmt: Select[tuple[VolatilityObservation]] = select(VolatilityObservation).where(
            VolatilityObservation.symbol == symbol,
            VolatilityObservation.valuation_timestamp >= start_ts,
            VolatilityObservation.valuation_timestamp <= end_ts,
        )
        if min_quality_score is not None:
            stmt = stmt.where(VolatilityObservation.quality_score >= min_quality_score)
        stmt = stmt.order_by(VolatilityObservation.valuation_timestamp.asc())
        return list(self.session.execute(stmt).scalars())


class VolatilitySliceRepository(RepositoryBase[VolatilityTimeSlice]):
    def create_slice(self, payload: dict[str, object]) -> int:
        stmt = sqlite_insert(VolatilityTimeSlice).values(payload)
        self.session.execute(stmt)
        slice_id = payload.get("slice_id")
        assert isinstance(slice_id, str)
        row = self.get_slice(slice_id)
        assert row is not None
        return row.id

    def add_nodes(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        stmt = sqlite_insert(VolatilityTimeSliceNode).values(list(rows))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    VolatilityTimeSliceNode.slice_id,
                    VolatilityTimeSliceNode.tenor_days,
                    VolatilityTimeSliceNode.x,
                    VolatilityTimeSliceNode.node_kind,
                ],
                set_={
                    "implied_volatility": stmt.excluded.implied_volatility,
                    "confidence_score": stmt.excluded.confidence_score,
                    "provenance": stmt.excluded.provenance,
                },
            )
        )

    def get_slice(self, slice_id: str) -> VolatilityTimeSlice | None:
        stmt: Select[tuple[VolatilityTimeSlice]] = select(VolatilityTimeSlice).where(
            VolatilityTimeSlice.slice_id == slice_id
        )
        return self.session.execute(stmt).scalars().first()

    def list_nodes(self, slice_row_id: int) -> list[VolatilityTimeSliceNode]:
        stmt: Select[tuple[VolatilityTimeSliceNode]] = (
            select(VolatilityTimeSliceNode)
            .where(VolatilityTimeSliceNode.slice_id == slice_row_id)
            .order_by(VolatilityTimeSliceNode.tenor_days.asc(), VolatilityTimeSliceNode.x.asc())
        )
        return list(self.session.execute(stmt).scalars())

    def finalize_slice(self, slice_id: str) -> None:
        stmt = (
            update(VolatilityTimeSlice)
            .where(VolatilityTimeSlice.slice_id == slice_id)
            .values(status="finalized")
        )
        self.session.execute(stmt)

    def find_nearest_prior_slice(
        self,
        *,
        symbol: str,
        as_of: datetime,
        slice_kind: str,
    ) -> VolatilityTimeSlice | None:
        stmt: Select[tuple[VolatilityTimeSlice]] = (
            select(VolatilityTimeSlice)
            .where(
                VolatilityTimeSlice.symbol == symbol,
                VolatilityTimeSlice.slice_kind == slice_kind,
                VolatilityTimeSlice.valuation_timestamp <= as_of,
                VolatilityTimeSlice.status == "finalized",
            )
            .order_by(VolatilityTimeSlice.valuation_timestamp.desc())
        )
        return self.session.execute(stmt).scalars().first()
