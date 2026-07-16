from __future__ import annotations

import gzip
import zipfile

import pytest

from backend.data.integration.archive import UnsafeArchiveError, extract_archive
from backend.data.integration.export import export_html, export_json
from backend.data.integration.local import LocalDatasetProvider
from backend.data.integration.quality import CertificationLevel, certify

CSV = (
    "symbol,expiration,strike,option_type,quote_timestamp,bid,ask\n"
    "spy,2026-01-16,500,call,2025-01-02T15:00:00Z,4,5\n"
    "SPY,2026-01-16,-1,P,2025-01-02T15:01:00Z,4,3\n"
)


def test_csv_gzip_ingestion_quarantine_and_certification(tmp_path):
    path = tmp_path / "quotes.csv.gz"
    with gzip.open(path, "wt") as handle:
        handle.write(CSV)
    provider = LocalDatasetProvider(chunk_size=1)
    result = provider.ingest(provider.discover(path))
    assert result.rows_accepted == 1
    assert result.records[0]["symbol"] == "SPY"
    assert len(result.quarantine) == 1
    assert certify("x", "csv", "1", result).level == CertificationLevel.QUARANTINED


def test_archive_traversal_is_rejected(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../escape.csv", CSV)
    with pytest.raises(UnsafeArchiveError):
        extract_archive(archive, tmp_path / "out")


def test_exports_are_redacted_escaped_and_deterministic():
    first = export_json({"api_key": "secret", "b": 2})
    assert first == export_json({"b": 2, "api_key": "secret"})
    assert "secret" not in first
    rendered = export_html("<report>", {"warning": "<script>"})
    assert "<script>" not in rendered and "&lt;script&gt;" in rendered
