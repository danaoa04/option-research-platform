"""Typed Databento catalogue, requests, and capability states."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum


class CapabilityState(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    DATASET_DEPENDENT = "dataset_dependent"
    SCHEMA_DEPENDENT = "schema_dependent"
    LICENSE_DEPENDENT = "license_dependent"
    NOT_VALIDATED = "not_yet_validated"


class DatabentoSchema(StrEnum):
    DEFINITION = "definition"
    MBP_1 = "mbp-1"
    TRADES = "trades"
    METADATA = "metadata"


class DatabentoRequestKind(StrEnum):
    METADATA = "metadata"
    RANGE = "range"
    SYMBOL_RESOLUTION = "symbol_resolution"
    DEFINITIONS = "definitions"
    HISTORICAL = "historical"
    INCREMENTAL = "incremental"
    FIXTURE = "fixture"
    CACHE_REPLAY = "cache_replay"


@dataclass(slots=True, frozen=True)
class DatabentoRequest:
    kind: DatabentoRequestKind
    dataset: str
    schema: DatabentoSchema
    symbols: tuple[str, ...]
    start: datetime
    end: datetime
    stype_in: str = "raw_symbol"
    stype_out: str = "instrument_id"
    batch_size: int = 1_000
    continuation: str | None = None

    def __post_init__(self) -> None:
        if not self.dataset.strip():
            raise ValueError("dataset is required")
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Databento request timestamps must be timezone-aware")
        if self.start >= self.end:
            raise ValueError("start must be before end")
        symbols = tuple(sorted({item.strip() for item in self.symbols if item.strip()}))
        if not symbols and self.kind not in {
            DatabentoRequestKind.METADATA,
            DatabentoRequestKind.RANGE,
        }:
            raise ValueError("symbols are required for this request kind")
        if self.batch_size < 1 or self.batch_size > 100_000:
            raise ValueError("batch_size must be between 1 and 100000")
        object.__setattr__(self, "symbols", symbols)

    @property
    def checksum(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(slots=True, frozen=True)
class DatabentoDataset:
    identifier: str
    description: str
    asset_class: str
    schemas: tuple[DatabentoSchema, ...]
    symbol_types: tuple[str, ...]
    delivery_modes: tuple[str, ...]
    compression: tuple[str, ...]
    formats: tuple[str, ...]
    fixture_validated: bool
    limitations: tuple[str, ...]


DATABENTO_CATALOGUE = (
    DatabentoDataset(
        "SYNTHETIC.OPRA",
        "Synthetic option definitions and top-of-book fixture family",
        "options",
        (DatabentoSchema.DEFINITION, DatabentoSchema.MBP_1),
        ("raw_symbol", "instrument_id"),
        ("batch", "fixture"),
        ("zstd", "gzip"),
        ("json", "csv", "parquet", "native-optional"),
        True,
        ("Not a licensed dataset", "Availability depends on dataset, schema, and license"),
    ),
)
