"""Lineage and audit-log models for dataset ingestion workflows."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = ("password", "secret", "token", "api_key", "authorization", "auth")


@dataclass(slots=True, frozen=True)
class AuditEvent:
    """A single auditable lifecycle event for a dataset."""

    event_type: str
    timestamp: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "details": _sanitize_mapping(self.details),
        }


@dataclass(slots=True, frozen=True)
class ValidationOutcome:
    """Validation summary attached to lineage records."""

    valid: bool
    issue_count: int
    severities: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issue_count": self.issue_count,
            "severities": dict(self.severities),
        }


@dataclass(slots=True, frozen=True)
class DatasetLineage:
    """Structured provenance and audit history for a dataset snapshot."""

    provider: str
    dataset_name: str
    dataset_version: str
    source_metadata: Mapping[str, Any]
    imported_at: str
    software_version: str
    transformations: tuple[str, ...] = ()
    validation: ValidationOutcome | None = None
    events: tuple[AuditEvent, ...] = ()

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "source_metadata": _sanitize_mapping(self.source_metadata),
            "imported_at": self.imported_at,
            "software_version": self.software_version,
            "transformations": list(self.transformations),
            "validation": self.validation.to_dict() if self.validation else None,
            "events": [event.to_dict() for event in self.events],
        }

    def to_json(self) -> str:
        """Return stable JSON representation for reproducible logs."""
        return json.dumps(self.to_canonical_dict(), sort_keys=True, separators=(",", ":"))


class LineageAuditLogger:
    """Append-only JSONL audit logger for dataset lineage records."""

    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def record_import(self, lineage: DatasetLineage) -> None:
        """Write a lineage record to the audit log."""
        payload = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "record_type": "dataset_lineage",
            "lineage": lineage.to_canonical_dict(),
        }
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def _sanitize_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in mapping.items():
        key_str = str(key)
        lowered = key_str.lower()
        if any(token in lowered for token in SENSITIVE_KEYS):
            sanitized[key_str] = "<redacted>"
            continue

        if isinstance(value, Mapping):
            sanitized[key_str] = _sanitize_mapping(value)
        elif isinstance(value, list | tuple):
            sanitized[key_str] = [
                _sanitize_mapping(item) if isinstance(item, Mapping) else item for item in value
            ]
        else:
            sanitized[key_str] = value

    return sanitized
