"""Persistence helpers for volatility observations and time-slice artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from backend.database import (
    VolatilityObservationDTO,
    VolatilityPersistenceService,
    VolatilitySliceMutationError,
    VolatilityTimeSliceDTO,
    deterministic_slice_checksum,
)

from .models import (
    SliceKind,
    SurfaceNode,
    VolatilityObservationRecord,
    VolatilitySliceRecord,
    VolatilityTimeSliceMetadata,
)


@dataclass(slots=True)
class InMemoryVolatilitySliceStore:
    """Deterministic in-memory store for volatility slices and observations."""

    observations: list[VolatilityObservationRecord] = field(default_factory=list)
    slices: dict[str, VolatilitySliceRecord] = field(default_factory=dict)

    def store_observations(self, rows: list[VolatilityObservationRecord]) -> None:
        self.observations.extend(rows)

    def store_slice(self, record: VolatilitySliceRecord) -> None:
        self.slices[record.slice_id] = record

    def get_slice(self, slice_id: str) -> VolatilitySliceRecord | None:
        return self.slices.get(slice_id)


@dataclass(slots=True)
class VolatilitySliceAssembler:
    """Assemble immutable slice records and checksums from builder outputs."""

    def build_slice(
        self,
        *,
        slice_id: str,
        symbol: str,
        kind: SliceKind,
        metadata: VolatilityTimeSliceMetadata,
        raw_nodes: list[SurfaceNode],
        cleaned_nodes: list[SurfaceNode],
        interpolated_nodes: list[SurfaceNode],
    ) -> VolatilitySliceRecord:
        return VolatilitySliceRecord(
            slice_id=slice_id,
            symbol=symbol,
            kind=kind,
            metadata=metadata,
            raw_nodes=tuple(raw_nodes),
            cleaned_nodes=tuple(cleaned_nodes),
            interpolated_nodes=tuple(interpolated_nodes),
        )


@dataclass(slots=True)
class DatabaseVolatilityWriter:
    """Write volatility observations and slices via backend database services."""

    persistence: VolatilityPersistenceService

    def persist_observations(
        self,
        rows: list[VolatilityObservationRecord],
        manifest_id: int,
    ) -> None:
        payload = [
            VolatilityObservationDTO(
                symbol=row.symbol,
                valuation_timestamp=row.valuation_timestamp,
                expiration=row.expiration,
                strike=Decimal(str(row.strike)),
                option_type=row.option_type,
                moneyness=Decimal(str(row.moneyness)),
                forward_moneyness=(
                    Decimal(str(row.forward_moneyness))
                    if row.forward_moneyness is not None
                    else None
                ),
                delta=Decimal(str(row.delta)) if row.delta is not None else None,
                implied_volatility=Decimal(str(row.implied_volatility)),
                quote_source=row.quote_source.value,
                pricing_model=row.pricing_model.value,
                solver_method=row.solver_method.value,
                solver_status=row.solver_status.value,
                pricing_error=(
                    Decimal(str(row.pricing_error)) if row.pricing_error is not None else None
                ),
                bid=Decimal(str(row.bid)) if row.bid is not None else None,
                ask=Decimal(str(row.ask)) if row.ask is not None else None,
                midpoint=Decimal(str(row.midpoint)) if row.midpoint is not None else None,
                spread_width=(
                    Decimal(str(row.spread_width)) if row.spread_width is not None else None
                ),
                volume=row.volume,
                open_interest=row.open_interest,
                stale_age_seconds=(
                    Decimal(str(row.stale_age_seconds))
                    if row.stale_age_seconds is not None
                    else None
                ),
                vega=Decimal(str(row.vega)) if row.vega is not None else None,
                tree_sensitivity=(
                    Decimal(str(row.tree_sensitivity)) if row.tree_sensitivity is not None else None
                ),
                quality_score=(
                    Decimal(str(row.confidence_score)) if row.confidence_score is not None else None
                ),
                quality_flags=list(row.quality_flags),
                contract_metadata=dict(row.contract_metadata),
                solver_metadata={
                    "pricing_error": row.pricing_error,
                    "solver_status": row.solver_status.value,
                },
                manifest_id=manifest_id,
            )
            for row in rows
        ]
        self.persistence.store_observations(payload)

    def persist_slice(
        self,
        *,
        slice_id: str,
        symbol: str,
        kind: SliceKind,
        metadata: VolatilityTimeSliceMetadata,
        nodes: list[SurfaceNode],
    ) -> int:
        node_payload: list[dict[str, object]] = [
            {
                "tenor_days": item.tenor_days,
                "x": Decimal(str(item.x)),
                "implied_volatility": Decimal(str(item.implied_volatility)),
                "node_kind": item.node_kind.value,
                "confidence_score": Decimal(str(item.quality_score)),
                "provenance": dict(item.provenance),
            }
            for item in nodes
        ]

        payload = VolatilityTimeSliceDTO(
            slice_id=slice_id,
            symbol=symbol,
            valuation_timestamp=metadata.valuation_timestamp,
            slice_kind=kind.value,
            status=metadata.status.value,
            input_manifests=list(metadata.input_manifests),
            solver_metadata=dict(metadata.solver_metadata),
            filtering_policy=dict(metadata.filtering_policy),
            interpolation_policy=dict(metadata.interpolation_policy),
            tree_step_policy=dict(metadata.tree_step_policy),
            quality_thresholds=dict(metadata.quality_thresholds),
            node_count=metadata.node_count,
            excluded_observation_count=metadata.excluded_observation_count,
            checksums=dict(metadata.checksums),
            git_commit=metadata.git_commit,
            created_at=datetime.now(UTC),
        )

        checksum = deterministic_slice_checksum(payload=payload, nodes=node_payload)
        payload_with_checksum = VolatilityTimeSliceDTO(
            slice_id=payload.slice_id,
            symbol=payload.symbol,
            valuation_timestamp=payload.valuation_timestamp,
            slice_kind=payload.slice_kind,
            status=payload.status,
            input_manifests=payload.input_manifests,
            solver_metadata=payload.solver_metadata,
            filtering_policy=payload.filtering_policy,
            interpolation_policy=payload.interpolation_policy,
            tree_step_policy=payload.tree_step_policy,
            quality_thresholds=payload.quality_thresholds,
            node_count=payload.node_count,
            excluded_observation_count=payload.excluded_observation_count,
            checksums={**payload.checksums, "slice_digest": checksum},
            git_commit=payload.git_commit,
            created_at=payload.created_at,
        )
        return self.persistence.create_slice(payload_with_checksum, node_payload)

    def finalize_slice(self, slice_id: str) -> None:
        self.persistence.finalize_slice(slice_id)


__all__ = [
    "DatabaseVolatilityWriter",
    "InMemoryVolatilitySliceStore",
    "VolatilitySliceAssembler",
    "VolatilitySliceMutationError",
]
