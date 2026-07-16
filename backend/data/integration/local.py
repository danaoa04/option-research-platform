"""CSV and optional PyArrow Parquet discovery and bounded ingestion."""

from __future__ import annotations

import csv
import gzip
import hashlib
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from .models import (
    DatasetDiscovery,
    DatasetType,
    DiscoveredFile,
    IngestionResult,
    QuarantineReason,
    QuarantineRecord,
    RepairRecord,
    SourceMetadata,
    file_format,
)
from .profiles import get_schema_profile, resolve_mapping


class LocalDatasetProvider:
    """Provider-neutral local files adapter; it performs no network operations."""

    def __init__(
        self, *, delimiter: str = ",", encoding: str = "utf-8", chunk_size: int = 10_000
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.delimiter, self.encoding, self.chunk_size = delimiter, encoding, chunk_size

    def discover(
        self,
        source: str | Path,
        *,
        pattern: str = "**/*",
        dataset_type: DatasetType = DatasetType.OPTION_QUOTES,
        profile: str | None = None,
    ) -> DatasetDiscovery:
        root = Path(source)
        candidates = [root] if root.is_file() else list(root.glob(pattern))
        files = []
        for path in sorted(
            p for p in candidates if p.is_file() and file_format(p) in {"csv", "parquet", "archive"}
        ):
            files.append(
                DiscoveredFile(
                    str(path),
                    path.stat().st_size,
                    _checksum(path),
                    file_format(path),
                    _estimate_csv_rows(path) if file_format(path) == "csv" else None,
                )
            )
        formats = {item.format for item in files if item.format != "archive"}
        profile_name = profile or ("generic_parquet" if formats == {"parquet"} else "generic_csv")
        warnings = () if files else ("No supported files discovered",)
        return DatasetDiscovery(str(root), tuple(files), dataset_type, profile_name, warnings)

    def ingest(
        self,
        discovery: DatasetDiscovery,
        *,
        mapping: dict[str, str] | None = None,
        progress: Callable[[IngestionResult], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> IngestionResult:
        result, seen = IngestionResult(), set()
        profile = get_schema_profile(discovery.schema_profile)
        for discovered in discovery.files:
            if cancelled and cancelled():
                result.cancelled = True
                break
            if discovered.format == "archive":
                continue
            for row_number, raw in self._rows(Path(discovered.path)):
                result.rows_processed += 1
                source = SourceMetadata(
                    discovered.path, discovered.checksum, row_number, profile.identifier
                )
                try:
                    resolved = resolve_mapping(list(raw), profile, mapping)
                    record, repairs = _normalize(raw, resolved, source)
                    reason = _validate(record)
                    if reason:
                        raise ValueError(reason.value)
                    identity = tuple(
                        record.get(key)
                        for key in (
                            "symbol",
                            "expiration",
                            "strike",
                            "option_type",
                            "quote_timestamp",
                        )
                    )
                    if identity in seen:
                        result.duplicates += 1
                        continue
                    seen.add(identity)
                    record["_source"] = source
                    result.records.append(record)
                    result.repairs.extend(repairs)
                except (ValueError, TypeError) as exc:
                    reason = next(
                        (r for r in QuarantineReason if r.value == str(exc)),
                        QuarantineReason.SCHEMA_MISMATCH,
                    )
                    result.quarantine.append(QuarantineRecord(reason, str(exc), raw, source))
                if progress and result.rows_processed % self.chunk_size == 0:
                    progress(result)
            result.files_processed += 1
        if progress:
            progress(result)
        return result

    def _rows(self, path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
        if file_format(path) == "csv":
            opener = gzip.open if path.name.lower().endswith(".gz") else open
            with opener(path, "rt", encoding=self.encoding, newline="") as handle:
                yield from enumerate(csv.DictReader(handle, delimiter=self.delimiter), start=2)
            return
        try:
            import pyarrow.parquet as pq  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("Parquet ingestion requires the optional 'pyarrow' package") from exc
        row = 1
        for batch in pq.ParquetFile(path).iter_batches(batch_size=self.chunk_size):
            for record in batch.to_pylist():
                row += 1
                yield row, record


def _normalize(
    raw: dict[str, Any], mapping: dict[str, str], source: SourceMetadata
) -> tuple[dict[str, Any], list[RepairRecord]]:
    output: dict[str, Any] = {}
    repairs: list[RepairRecord] = []
    for source_field, canonical in mapping.items():
        value = raw.get(source_field)
        if isinstance(value, str) and value != value.strip():
            repairs.append(
                RepairRecord(canonical, value, value.strip(), "whitespace_cleanup", source)
            )
            value = value.strip()
        if value in ("", "null", "NULL", "NA", "N/A"):
            value = None
        output[canonical] = value
    output["symbol"] = str(output.get("symbol") or "").upper()
    option_type = str(output.get("option_type") or "").upper()
    output["option_type"] = {"CALL": "C", "PUT": "P"}.get(option_type, option_type)
    try:
        output["strike"] = float(str(output["strike"]))
        for field in (
            "bid",
            "ask",
            "last",
            "underlying_price",
            "implied_volatility",
            "delta",
            "gamma",
            "theta",
            "vega",
            "rho",
        ):
            if output.get(field) is not None:
                output[field] = float(str(output[field]))
        output["expiration"] = date.fromisoformat(str(output["expiration"])).isoformat()
        timestamp = datetime.fromisoformat(str(output["quote_timestamp"]).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError(QuarantineReason.MALFORMED_TIMESTAMP.value)
        output["quote_timestamp"] = timestamp.astimezone(UTC).isoformat()
    except (KeyError, ValueError, TypeError) as exc:
        if str(exc) in {r.value for r in QuarantineReason}:
            raise
        raise ValueError(QuarantineReason.SCHEMA_MISMATCH.value) from exc
    return output, repairs


def _validate(record: dict[str, Any]) -> QuarantineReason | None:
    if not record.get("symbol") or record.get("option_type") not in {"C", "P"}:
        return QuarantineReason.MISSING_REQUIRED_IDENTIFIER
    if record["strike"] <= 0:
        return QuarantineReason.INVALID_STRIKE
    for field in ("bid", "ask", "last", "underlying_price"):
        if record.get(field) is not None and record[field] < 0:
            return QuarantineReason.IMPOSSIBLE_PRICE
    if (
        record.get("bid") is not None
        and record.get("ask") is not None
        and record["bid"] > record["ask"]
    ):
        return QuarantineReason.CROSSED_MARKET
    return None


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _estimate_csv_rows(path: Path) -> int | None:
    try:
        opener = gzip.open if path.name.lower().endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)
    except OSError, UnicodeError:
        return None
