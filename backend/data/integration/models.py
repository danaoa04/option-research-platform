"""Typed, provider-neutral ingestion contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class DatasetType(StrEnum):
    OPTION_QUOTES = "option_quotes"
    OPTION_CONTRACTS = "option_contracts"
    UNDERLYING_PRICES = "underlying_prices"
    DIVIDENDS = "dividends"
    EARNINGS = "earnings"
    CORPORATE_ACTIONS = "corporate_actions"
    RATES = "rates"


class QuarantineReason(StrEnum):
    MALFORMED_TIMESTAMP = "malformed_timestamp"
    INVALID_STRIKE = "invalid_strike"
    INVALID_EXPIRATION = "invalid_expiration"
    CROSSED_MARKET = "crossed_market"
    IMPOSSIBLE_PRICE = "impossible_price"
    MISSING_REQUIRED_IDENTIFIER = "missing_required_identifier"
    SCHEMA_MISMATCH = "schema_mismatch"
    CHECKSUM_FAILURE = "checksum_failure"
    ENCODING_FAILURE = "encoding_failure"
    AMBIGUOUS_COLUMN = "ambiguous_column"


@dataclass(slots=True, frozen=True)
class DiscoveredFile:
    path: str
    size_bytes: int
    checksum: str
    format: str
    estimated_rows: int | None = None


@dataclass(slots=True, frozen=True)
class DatasetDiscovery:
    root: str
    files: tuple[DiscoveredFile, ...]
    dataset_type: DatasetType
    schema_profile: str
    warnings: tuple[str, ...] = ()

    @property
    def estimated_row_count(self) -> int | None:
        values = [item.estimated_rows for item in self.files]
        if not values or any(value is None for value in values):
            return None
        return sum(value for value in values if value is not None)


@dataclass(slots=True, frozen=True)
class SourceMetadata:
    source_file: str
    source_checksum: str
    source_row: int
    mapping_version: str


@dataclass(slots=True)
class QuarantineRecord:
    reason: QuarantineReason
    detail: str
    raw_record: dict[str, Any]
    source: SourceMetadata


@dataclass(slots=True)
class RepairRecord:
    field: str
    before: Any
    after: Any
    policy: str
    source: SourceMetadata


@dataclass(slots=True)
class IngestionResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    quarantine: list[QuarantineRecord] = field(default_factory=list)
    repairs: list[RepairRecord] = field(default_factory=list)
    files_processed: int = 0
    rows_processed: int = 0
    duplicates: int = 0
    cancelled: bool = False

    @property
    def rows_accepted(self) -> int:
        return len(self.records)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def file_format(path: Path) -> str:
    name = path.name.lower()
    if name.endswith((".parquet", ".pq")):
        return "parquet"
    if name.endswith((".csv", ".csv.gz", ".gz")):
        return "csv"
    if name.endswith((".zip", ".tar.gz", ".tgz")):
        return "archive"
    return "unknown"
