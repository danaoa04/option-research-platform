"""Dataset manifest models for versioning and reproducibility."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any


@dataclass(slots=True, frozen=True)
class DatasetDateRange:
    """Date range covered by a dataset snapshot."""

    start_date: date
    end_date: date

    def to_dict(self) -> dict[str, str]:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }


@dataclass(slots=True, frozen=True)
class DatasetManifest:
    """Serializable manifest describing a concrete dataset version."""

    provider: str
    dataset_name: str
    dataset_version: str
    schema_version: str
    symbol_scope: tuple[str, ...]
    date_range: DatasetDateRange
    created_timestamp: str
    checksum: str
    row_count: int
    source_metadata: Mapping[str, Any]

    def to_canonical_dict(self) -> dict[str, Any]:
        """Return a deterministic dictionary representation suitable for stable hashing."""
        return {
            "provider": self.provider,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "schema_version": self.schema_version,
            "symbol_scope": sorted(self.symbol_scope),
            "date_range": self.date_range.to_dict(),
            "created_timestamp": self.created_timestamp,
            "checksum": self.checksum,
            "row_count": self.row_count,
            "source_metadata": _canonicalize(self.source_metadata),
        }

    def to_json(self) -> str:
        """Return deterministic JSON output for manifest persistence."""
        return json.dumps(self.to_canonical_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DatasetManifest:
        """Reconstruct a manifest from a dictionary."""
        date_range = payload.get("date_range", {})
        if not isinstance(date_range, Mapping):
            raise ValueError("date_range must be a mapping")

        source_metadata = payload.get("source_metadata", {})
        if not isinstance(source_metadata, Mapping):
            raise ValueError("source_metadata must be a mapping")

        symbol_scope_raw = payload.get("symbol_scope", ())
        if not isinstance(symbol_scope_raw, list | tuple):
            raise ValueError("symbol_scope must be a list or tuple")

        return cls(
            provider=str(payload["provider"]),
            dataset_name=str(payload["dataset_name"]),
            dataset_version=str(payload["dataset_version"]),
            schema_version=str(payload["schema_version"]),
            symbol_scope=tuple(str(symbol) for symbol in symbol_scope_raw),
            date_range=DatasetDateRange(
                start_date=date.fromisoformat(str(date_range["start_date"])),
                end_date=date.fromisoformat(str(date_range["end_date"])),
            ),
            created_timestamp=str(payload["created_timestamp"]),
            checksum=str(payload["checksum"]),
            row_count=int(payload["row_count"]),
            source_metadata=source_metadata,
        )


def build_dataset_manifest(
    *,
    provider: str,
    dataset_name: str,
    dataset_version: str,
    schema_version: str,
    symbol_scope: list[str] | tuple[str, ...],
    start_date: date,
    end_date: date,
    row_count: int,
    source_metadata: Mapping[str, Any] | None = None,
    created_timestamp: datetime | None = None,
    payload_for_checksum: Any | None = None,
) -> DatasetManifest:
    """Build a deterministic manifest and compute its checksum."""
    if row_count < 0:
        raise ValueError("row_count must be non-negative")

    timestamp = (created_timestamp or datetime.now(tz=UTC)).isoformat()
    metadata = dict(source_metadata or {})
    canonical_source = _canonicalize(metadata)

    checksum_payload: dict[str, Any] = {
        "provider": provider,
        "dataset_name": dataset_name,
        "dataset_version": dataset_version,
        "schema_version": schema_version,
        "symbol_scope": sorted(str(symbol) for symbol in symbol_scope),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "row_count": row_count,
        "source_metadata": canonical_source,
    }
    if payload_for_checksum is not None:
        checksum_payload["payload"] = _canonicalize(payload_for_checksum)

    checksum = hashlib.sha256(
        json.dumps(checksum_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return DatasetManifest(
        provider=provider,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        schema_version=schema_version,
        symbol_scope=tuple(sorted(str(symbol) for symbol in symbol_scope)),
        date_range=DatasetDateRange(start_date=start_date, end_date=end_date),
        created_timestamp=timestamp,
        checksum=checksum,
        row_count=row_count,
        source_metadata=canonical_source,
    )


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, list | tuple):
        return [_canonicalize(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    return value
