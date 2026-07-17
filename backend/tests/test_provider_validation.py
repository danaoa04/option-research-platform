from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.api.v1 import provider_credential_status, provider_readiness, provider_validation_demo
from backend.data.provider_cli import main
from backend.data.provider_validation import (
    CertificationLevel,
    CredentialValidationStatus,
    DataClassification,
    ExportDecision,
    ProviderConfiguration,
    ProviderIssueCode,
    ReadinessStatus,
    build_manifest,
    certify_dataset,
    compare_provider_records,
    credential_status,
    enforce_export_policy,
    export_decision,
    inspect_import_path,
    lineage_event,
    normalize_option_record,
    performance_measurements,
    provider_audit,
    readiness_report,
    validate_options,
)


def _raw_option(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "option_identifier": "SPY260116C00450000",
        "timestamp": "2026-01-15T16:00:00Z",
        "bid": "1.10",
        "ask": "1.20",
        "last": "1.15",
        "volume": "100",
        "open_interest": "1000",
        "multiplier": "100",
        "exercise_style": "american",
        "settlement_style": "physical",
        "exchange": "synthetic",
    }
    raw.update(overrides)
    return raw


def test_capability_audit_and_configuration_stay_conservative() -> None:
    audit = provider_audit()
    assert {item.provider for item in audit} == {"orats", "databento", "cboe", "polygon"}
    assert any(item.status.value == "licence_required" for item in audit)

    config = ProviderConfiguration(
        provider="orats",
        environment="release-candidate",
        dataset="options",
        schema="provider-v1",
        licensing=DataClassification.LICENSED,
        export_policy=ExportDecision.ALLOW,
        credential_reference="api_key=secret",
    )

    issues = config.validate()

    assert "restricted or licensed inputs cannot use unrestricted export" in issues
    assert "credential_reference must not contain credential values" in issues


def test_credentials_report_presence_only_and_export_policy_blocks_restricted() -> None:
    missing = credential_status("polygon", None)
    configured = credential_status("polygon", "POLYGON_API_KEY")

    assert missing.status is CredentialValidationStatus.NOT_CONFIGURED
    assert configured.status is CredentialValidationStatus.AUTHENTICATED
    assert "secret" not in json.dumps(configured.redacted()).lower()
    assert export_decision(DataClassification.SYNTHETIC, "json") is ExportDecision.ALLOW
    assert export_decision(DataClassification.LICENSED, "json") is ExportDecision.REDACT
    with pytest.raises(PermissionError):
        enforce_export_policy(DataClassification.RESTRICTED, "html")


def test_import_safety_rejects_path_escape_and_spreadsheet_formula(tmp_path: Path) -> None:
    safe = tmp_path / "safe.csv"
    safe.write_text("symbol,value\nSPY,1\n", encoding="utf-8")
    formula = tmp_path / "formula.csv"
    formula.write_text("symbol,value\nSPY,=cmd|calc\n", encoding="utf-8")
    unsupported = tmp_path / "payload.html"
    unsupported.write_text("<script>alert(1)</script>", encoding="utf-8")

    assert inspect_import_path(safe, allowed_root=tmp_path).accepted
    formula_report = inspect_import_path(formula, allowed_root=tmp_path)
    unsupported_report = inspect_import_path(unsupported, allowed_root=tmp_path)

    assert ProviderIssueCode.SPREADSHEET_FORMULA in formula_report.issues
    assert ProviderIssueCode.UNSUPPORTED_FILE_TYPE in unsupported_report.issues


def test_normalization_validation_certification_lineage_and_readiness() -> None:
    valid = normalize_option_record("cboe", _raw_option())
    crossed = normalize_option_record("cboe", _raw_option(bid="2.00", ask="1.00"))
    missing_multiplier = normalize_option_record("cboe", _raw_option(multiplier=""))
    summary = validate_options((valid, crossed, missing_multiplier))
    manifest = build_manifest(
        "cboe",
        "synthetic_options",
        (valid.raw_record, crossed.raw_record, missing_multiplier.raw_record),
        classification=DataClassification.SYNTHETIC,
    )
    certification = certify_dataset("cboe", manifest, summary)
    lineage = lineage_event(manifest, "certification", certification.metrics)
    ready = readiness_report(
        "cboe",
        configuration_valid=True,
        credentials=credential_status("cboe", None),
        certification=certification,
        export_enforced=True,
        gui_available=True,
        live_validated=False,
    )

    assert summary.records_accepted == 1
    assert {issue.code for issue in summary.issues} >= {
        ProviderIssueCode.CROSSED_MARKET,
        ProviderIssueCode.MISSING_MULTIPLIER,
    }
    assert certification.level in {
        CertificationLevel.REJECTED,
        CertificationLevel.IMPORT_CERTIFIED,
    }
    assert certification.reproducibility_checksum
    assert lineage.input_checksum == manifest.source_checksum
    assert ready.status is ReadinessStatus.UNVALIDATED
    assert "live_validation" in ready.warnings


def test_provider_comparison_reports_matches_unmatched_and_divergence() -> None:
    cboe = normalize_option_record("cboe", _raw_option(bid="1.10"))
    polygon = normalize_option_record("polygon", _raw_option(bid="1.15"))
    orats_only = normalize_option_record(
        "orats",
        _raw_option(option_identifier="SPY260116P00450000", option_type="P"),
    )

    report = compare_provider_records(
        {"cboe": (cboe,), "polygon": (polygon,), "orats": (orats_only,)}
    )

    assert report.matched_identities == 0
    assert report.unmatched_identities["orats"] == ("SPY260116C00450000",)
    assert report.field_divergences
    assert report.checksum


def test_api_and_cli_expose_12c_reports_without_secrets(
    capsys: pytest.CaptureFixture[str],
) -> None:
    demo = provider_validation_demo("cboe")["data"]
    readiness = provider_readiness("cboe")["data"]
    credential = provider_credential_status("cboe")["data"]

    assert demo["manifest"]["classification"] == "synthetic"
    assert readiness["status"] == "unvalidated"
    assert credential["configured"] is False

    assert main(["provider-audit"]) == 0
    assert main(["credential-status", "--provider", "cboe"]) == 0
    assert main(["validation-demo", "--provider", "polygon"]) == 0
    assert main(["readiness", "--provider", "polygon"]) == 0
    assert main(["licensing", "--id", "restricted"]) == 0
    output = capsys.readouterr().out.lower()
    assert "secret" not in output
    assert "restricted" in output


def test_performance_measurement_is_deterministic_shape() -> None:
    started = datetime(2026, 7, 17, 12, tzinfo=UTC)
    result = performance_measurements(10, started, started)

    assert result["sample_size"] == 10
    assert result["records_per_second"] > 0
    assert result["scope"] == "targeted Sprint 12C synthetic provider validation"


@pytest.mark.skipif(
    not os.environ.get("ORP_LIVE_PROVIDER_TESTS"),
    reason="live provider validation is opt-in and requires explicit licence permission",
)
def test_live_provider_validation_is_opt_in() -> None:
    pytest.fail("Set up provider-specific live validation evidence before enabling this test.")
