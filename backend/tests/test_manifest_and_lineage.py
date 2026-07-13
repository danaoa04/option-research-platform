from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from backend.data.lineage.audit import (
    AuditEvent,
    DatasetLineage,
    LineageAuditLogger,
    ValidationOutcome,
)
from backend.data.models.manifest import DatasetManifest, build_dataset_manifest


def test_manifest_is_reproducible_and_round_trips() -> None:
    created = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    manifest_a = build_dataset_manifest(
        provider="csv",
        dataset_name="spy_options",
        dataset_version="v1",
        schema_version="1.0",
        symbol_scope=["QQQ", "SPY"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        row_count=12,
        source_metadata={"file": "a.csv", "source": "fixture"},
        created_timestamp=created,
        payload_for_checksum=[{"id": 1}],
    )
    manifest_b = build_dataset_manifest(
        provider="csv",
        dataset_name="spy_options",
        dataset_version="v1",
        schema_version="1.0",
        symbol_scope=["SPY", "QQQ"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        row_count=12,
        source_metadata={"source": "fixture", "file": "a.csv"},
        created_timestamp=created,
        payload_for_checksum=[{"id": 1}],
    )

    assert manifest_a.checksum == manifest_b.checksum
    assert manifest_a.to_json() == manifest_b.to_json()

    reconstructed = DatasetManifest.from_dict(manifest_a.to_canonical_dict())
    assert reconstructed.to_json() == manifest_a.to_json()


def test_lineage_redacts_secrets_and_writes_jsonl(tmp_path: Path) -> None:
    lineage = DatasetLineage(
        provider="polygon",
        dataset_name="options",
        dataset_version="2026.01",
        source_metadata={"api_key": "secret", "nested": {"token": "123"}},
        imported_at="2026-01-10T00:00:00+00:00",
        software_version="0.1.0",
        transformations=("normalize_schema", "drop_duplicates"),
        validation=ValidationOutcome(valid=True, issue_count=0, severities={}),
        events=(
            AuditEvent(
                event_type="import",
                timestamp="2026-01-10T00:00:00+00:00",
                details={"authorization": "Bearer secret"},
            ),
        ),
    )

    payload = lineage.to_canonical_dict()
    assert payload["source_metadata"]["api_key"] == "<redacted>"
    assert payload["source_metadata"]["nested"]["token"] == "<redacted>"

    output_file = tmp_path / "lineage.jsonl"
    logger = LineageAuditLogger(output_file)
    logger.record_import(lineage)

    raw = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(raw) == 1

    parsed = json.loads(raw[0])
    event_details = parsed["lineage"]["events"][0]["details"]
    assert event_details["authorization"] == "<redacted>"
