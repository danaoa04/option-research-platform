"""Databento synthetic schema normalization and explicit symbology resolution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .models import DatabentoSchema


class DatabentoSchemaError(ValueError):
    pass


@dataclass(slots=True, frozen=True)
class SymbolResolution:
    raw_symbol: str
    instrument_id: int
    canonical_underlying: str
    effective_start: datetime
    effective_end: datetime
    expiration: str | None = None
    strike: float | None = None
    option_type: str | None = None
    multiplier: float | None = None
    adjusted: bool = False
    ambiguous: bool = False


class SymbolResolver:
    def __init__(self, resolutions: tuple[SymbolResolution, ...]) -> None:
        self.resolutions = resolutions

    def resolve(self, instrument_id: int, at: datetime) -> SymbolResolution:
        matches = [
            item
            for item in self.resolutions
            if item.instrument_id == instrument_id
            and item.effective_start <= at < item.effective_end
        ]
        if not matches:
            raise DatabentoSchemaError("unresolved_instrument")
        if len(matches) != 1 or matches[0].ambiguous:
            raise DatabentoSchemaError("ambiguous_symbology")
        return matches[0]


@dataclass(slots=True, frozen=True)
class NormalizedDatabentoRecord:
    canonical: Mapping[str, Any]
    raw_provider: Mapping[str, Any]
    dataset: str
    schema: DatabentoSchema
    source_checksum: str


class DatabentoNormalizer:
    mapping_version = "databento-synthetic-v1"

    def __init__(self, resolver: SymbolResolver) -> None:
        self.resolver = resolver

    def normalize(
        self,
        raw: Mapping[str, Any],
        *,
        dataset: str,
        schema: DatabentoSchema,
        checksum: str,
    ) -> NormalizedDatabentoRecord:
        if schema not in {DatabentoSchema.DEFINITION, DatabentoSchema.MBP_1}:
            raise DatabentoSchemaError(f"unsupported_schema:{schema.value}")
        try:
            event = datetime.fromisoformat(str(raw["ts_event"]).replace("Z", "+00:00"))
            if event.tzinfo is None:
                raise ValueError
            instrument_id = int(raw["instrument_id"])
            resolution = self.resolver.resolve(instrument_id, event)
            canonical: dict[str, Any] = {
                "event_timestamp": event.astimezone(UTC).isoformat(),
                "receive_timestamp": self._receive_timestamp(raw, event),
                "instrument_id": instrument_id,
                "raw_symbol": resolution.raw_symbol,
                "symbol": resolution.canonical_underlying,
                "sequence": int(raw.get("sequence", 0)),
                "publisher_id": raw.get("publisher_id"),
                "raw_flags": raw.get("flags"),
                "dataset": dataset,
                "schema": schema.value,
            }
            if schema is DatabentoSchema.DEFINITION:
                canonical.update(self._definition(raw, resolution))
            else:
                canonical.update(self._quote(raw))
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, DatabentoSchemaError):
                raise
            raise DatabentoSchemaError("invalid_record") from exc
        return NormalizedDatabentoRecord(canonical, dict(raw), dataset, schema, checksum)

    @staticmethod
    def _receive_timestamp(raw: Mapping[str, Any], event: datetime) -> str:
        receive = datetime.fromisoformat(
            str(raw.get("ts_recv", event.isoformat())).replace("Z", "+00:00")
        )
        if receive.tzinfo is None or receive < event:
            raise DatabentoSchemaError("invalid_receive_timestamp")
        return receive.astimezone(UTC).isoformat()

    @staticmethod
    def _definition(raw: Mapping[str, Any], resolution: SymbolResolution) -> dict[str, Any]:
        strike_scale = int(raw.get("strike_scale", 1))
        if strike_scale <= 0:
            raise DatabentoSchemaError("invalid_strike_scaling")
        return {
            "expiration": resolution.expiration,
            "strike": float(raw.get("strike", resolution.strike or 0)) / strike_scale,
            "option_type": resolution.option_type,
            "multiplier": float(raw.get("multiplier", resolution.multiplier or 100)),
            "currency": raw.get("currency"),
            "exercise_style": raw.get("exercise_style"),
            "settlement_style": raw.get("settlement_style"),
            "adjusted": resolution.adjusted,
        }

    @staticmethod
    def _quote(raw: Mapping[str, Any]) -> dict[str, Any]:
        bid, ask = float(raw["bid_px"]), float(raw["ask_px"])
        bid_size, ask_size = int(raw.get("bid_sz", 0)), int(raw.get("ask_sz", 0))
        if min(bid, ask, bid_size, ask_size) < 0:
            raise DatabentoSchemaError("negative_price_or_size")
        if bid > ask:
            raise DatabentoSchemaError("crossed_market")
        return {"bid": bid, "ask": ask, "bid_size": bid_size, "ask_size": ask_size}
