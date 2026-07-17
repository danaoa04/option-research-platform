"""Offline provider validation, licensing, and certification boundaries."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

PROVIDER_IDS = ("orats", "databento", "cboe", "polygon")
SECRET_NAMES = ("api_key", "apikey", "token", "secret", "password", "credential")
SAFE_IMPORT_SUFFIXES = (".csv", ".csv.gz", ".parquet", ".pq")
OCC_PATTERN = re.compile(r"^(?P<root>[A-Z0-9]{1,6})(?P<date>\d{6})(?P<type>[CP])(?P<strike>\d{8})$")


class CapabilityStatus(StrEnum):
    SUPPORTED = "supported"
    SUPPORTED_WITH_LIMITATIONS = "supported_with_limitations"
    METADATA_ONLY = "metadata_only"
    IMPORT_ONLY = "import_only"
    UNAVAILABLE = "unavailable"
    UNVALIDATED = "unvalidated"
    LICENCE_REQUIRED = "licence_required"


class DataClassification(StrEnum):
    SYNTHETIC = "synthetic"
    PUBLIC = "public"
    USER_SUPPLIED = "user_supplied"
    PROVIDER_DERIVED = "provider_derived"
    LICENSED = "licensed"
    RESTRICTED = "restricted"
    EXPORT_PROHIBITED = "export_prohibited"
    DERIVED_ONLY = "derived_only"
    UNKNOWN = "unknown"


class ExportDecision(StrEnum):
    ALLOW = "allow"
    REDACT = "redact"
    BLOCK = "block"


class CredentialValidationStatus(StrEnum):
    AUTHENTICATED = "authenticated"
    REJECTED = "rejected"
    EXPIRED = "expired"
    RATE_LIMITED = "rate_limited"
    INSUFFICIENT_ENTITLEMENT = "insufficient_entitlement"
    NETWORK_UNAVAILABLE = "network_unavailable"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INVALID_CONFIG = "invalid_config"
    UNSUPPORTED_ACCOUNT = "unsupported_account"
    UNKNOWN_FAILURE = "unknown_failure"
    NOT_CONFIGURED = "not_configured"


class ReadinessStatus(StrEnum):
    READY = "ready"
    READY_WITH_WARNINGS = "ready_with_warnings"
    INCOMPLETE = "incomplete"
    BLOCKED = "blocked"
    UNVALIDATED = "unvalidated"


class CertificationLevel(StrEnum):
    REJECTED = "rejected"
    FIXTURE_ONLY = "fixture_only"
    IMPORT_CERTIFIED = "import_certified"
    LIVE_VALIDATED = "live_validated"


class ProviderIssueCode(StrEnum):
    MALFORMED_IDENTIFIER = "malformed_identifier"
    INVALID_EXPIRATION = "invalid_expiration"
    INVALID_STRIKE = "invalid_strike"
    INVALID_OPTION_TYPE = "invalid_option_type"
    CROSSED_MARKET = "crossed_market"
    NEGATIVE_PRICE = "negative_price"
    DUPLICATE_CONTRACT = "duplicate_contract"
    DUPLICATE_TIMESTAMP = "duplicate_timestamp"
    MISSING_MULTIPLIER = "missing_multiplier"
    UNSUPPORTED_SETTLEMENT_STYLE = "unsupported_settlement_style"
    AMBIGUOUS_ADJUSTED_CONTRACT = "ambiguous_adjusted_contract"
    UNRESOLVED_UNDERLYING = "unresolved_underlying"
    SCHEMA_MISMATCH = "schema_mismatch"
    INCONSISTENT_OPEN_INTEREST = "inconsistent_open_interest"
    SPREADSHEET_FORMULA = "spreadsheet_formula"
    UNSAFE_PATH = "unsafe_path"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"


@dataclass(slots=True, frozen=True)
class ProviderCapability:
    provider: str
    capability: str
    status: CapabilityStatus
    evidence: str
    limitations: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class ProviderConfiguration:
    provider: str
    environment: str
    dataset: str
    schema: str
    date_range: tuple[str, str] | None = None
    symbols: tuple[str, ...] = ()
    base_url: str | None = None
    rate_limit_per_minute: int | None = None
    max_retries: int = 3
    timeout_seconds: float = 30.0
    cache_enabled: bool = False
    import_only: bool = True
    licensing: DataClassification = DataClassification.UNKNOWN
    export_policy: ExportDecision = ExportDecision.BLOCK
    credential_reference: str | None = None

    def validate(self) -> tuple[str, ...]:
        issues: list[str] = []
        if self.provider not in PROVIDER_IDS and self.provider not in {
            "local-csv",
            "local-parquet",
        }:
            issues.append(f"unsupported provider: {self.provider}")
        if self.timeout_seconds <= 0:
            issues.append("timeout_seconds must be positive")
        if self.max_retries < 0:
            issues.append("max_retries must be non-negative")
        if self.rate_limit_per_minute is not None and self.rate_limit_per_minute <= 0:
            issues.append("rate_limit_per_minute must be positive when set")
        if (
            self.licensing
            in {
                DataClassification.LICENSED,
                DataClassification.RESTRICTED,
                DataClassification.EXPORT_PROHIBITED,
            }
            and self.export_policy is ExportDecision.ALLOW
        ):
            issues.append("restricted or licensed inputs cannot use unrestricted export")
        if self.credential_reference:
            lowered = self.credential_reference.lower()
            if any(name in lowered for name in SECRET_NAMES) and "=" in lowered:
                issues.append("credential_reference must not contain credential values")
        return tuple(issues)


@dataclass(slots=True, frozen=True)
class CredentialStatusReport:
    provider: str
    status: CredentialValidationStatus
    configured: bool
    storage: str
    details: tuple[str, ...] = ()

    def redacted(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class DatasetManifest:
    dataset_id: str
    provider: str
    dataset: str
    schema_version: str
    dataset_version: str
    classification: DataClassification
    source_checksum: str
    generated_at: datetime
    row_count: int
    fields: tuple[str, ...]
    licence: str
    retention_policy: str
    export_policy: ExportDecision
    limitations: tuple[str, ...] = ()

    @property
    def checksum(self) -> str:
        payload = json.dumps(asdict(self), default=str, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(slots=True, frozen=True)
class LineageEvent:
    event_id: str
    dataset_id: str
    provider: str
    stage: str
    input_checksum: str | None
    output_checksum: str
    occurred_at: datetime
    classification: DataClassification


@dataclass(slots=True, frozen=True)
class ImportSafetyReport:
    accepted: bool
    path: str
    checksum: str | None
    issues: tuple[ProviderIssueCode, ...]
    details: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class NormalizedOptionRecord:
    underlying: str
    option_root: str
    option_identifier: str
    expiration: str
    strike: float
    option_type: str
    bid: float | None
    ask: float | None
    last: float | None
    volume: int | None
    open_interest: int | None
    timestamp: str
    multiplier: float | None
    exercise_style: str | None
    settlement_style: str | None
    exchange: str | None
    adjusted_contract: bool
    raw_record: Mapping[str, Any]
    source_checksum: str


@dataclass(slots=True, frozen=True)
class ValidationIssue:
    code: ProviderIssueCode
    detail: str
    identifier: str | None = None


@dataclass(slots=True, frozen=True)
class ValidationSummary:
    records_seen: int
    records_accepted: int
    records_quarantined: int
    issues: tuple[ValidationIssue, ...]
    source_checksum: str


@dataclass(slots=True, frozen=True)
class CertificationReport:
    provider: str
    dataset_id: str
    level: CertificationLevel
    metrics: Mapping[str, float]
    exclusions: tuple[str, ...]
    warnings: tuple[str, ...]
    reproducibility_checksum: str


@dataclass(slots=True, frozen=True)
class ProviderComparisonReport:
    providers: tuple[str, ...]
    matched_identities: int
    unmatched_identities: Mapping[str, tuple[str, ...]]
    field_divergences: tuple[ValidationIssue, ...]
    severity: str
    limitations: tuple[str, ...]
    checksum: str


@dataclass(slots=True, frozen=True)
class ProviderReadinessReport:
    provider: str
    status: ReadinessStatus
    sections: Mapping[str, ReadinessStatus]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence: tuple[str, ...]


def provider_audit() -> tuple[ProviderCapability, ...]:
    rows = [
        ("orats", "historical_options", CapabilityStatus.UNVALIDATED, "offline adapter present"),
        (
            "databento",
            "historical_options",
            CapabilityStatus.UNVALIDATED,
            "offline adapter present",
        ),
        (
            "cboe",
            "fixture_options",
            CapabilityStatus.SUPPORTED_WITH_LIMITATIONS,
            "fixture transport",
        ),
        (
            "polygon",
            "fixture_options",
            CapabilityStatus.SUPPORTED_WITH_LIMITATIONS,
            "fixture transport",
        ),
        ("orats", "live_download", CapabilityStatus.LICENCE_REQUIRED, "no credentials in tests"),
        (
            "databento",
            "live_download",
            CapabilityStatus.LICENCE_REQUIRED,
            "no credentials in tests",
        ),
        ("cboe", "live_download", CapabilityStatus.LICENCE_REQUIRED, "no credentials in tests"),
        ("polygon", "live_download", CapabilityStatus.LICENCE_REQUIRED, "no credentials in tests"),
    ]
    return tuple(
        ProviderCapability(provider, capability, status, evidence, ("not live validated",))
        for provider, capability, status, evidence in rows
    )


def credential_status(
    provider: str,
    credential_reference: str | None,
    *,
    keychain_available: bool = False,
) -> CredentialStatusReport:
    storage = "macos_keychain" if keychain_available else "environment"
    if not credential_reference:
        return CredentialStatusReport(
            provider,
            CredentialValidationStatus.NOT_CONFIGURED,
            False,
            storage,
            ("credential presence only; value is never returned",),
        )
    if "=" in credential_reference:
        return CredentialStatusReport(
            provider,
            CredentialValidationStatus.INVALID_CONFIG,
            False,
            storage,
            ("credential reference contains an inline value",),
        )
    return CredentialStatusReport(
        provider,
        CredentialValidationStatus.AUTHENTICATED,
        True,
        storage,
        ("offline presence validation only",),
    )


def export_decision(classification: DataClassification, requested: str) -> ExportDecision:
    if classification in {DataClassification.RESTRICTED, DataClassification.EXPORT_PROHIBITED}:
        return ExportDecision.BLOCK
    if classification in {DataClassification.LICENSED, DataClassification.PROVIDER_DERIVED}:
        return (
            ExportDecision.REDACT if requested in {"json", "csv", "html"} else ExportDecision.BLOCK
        )
    if classification is DataClassification.UNKNOWN:
        return ExportDecision.BLOCK
    return ExportDecision.ALLOW


def enforce_export_policy(classification: DataClassification, requested: str) -> None:
    if export_decision(classification, requested) is ExportDecision.BLOCK:
        raise PermissionError(f"{classification.value} data cannot be exported as {requested}")


def inspect_import_path(path: Path, *, allowed_root: Path) -> ImportSafetyReport:
    issues: list[ProviderIssueCode] = []
    details: list[str] = []
    checksum: str | None = None
    try:
        resolved = path.resolve(strict=True)
        root = allowed_root.resolve(strict=True)
        if not resolved.is_relative_to(root) or path.is_symlink():
            issues.append(ProviderIssueCode.UNSAFE_PATH)
            details.append("path must remain inside the selected import root")
        if not any(path.name.lower().endswith(suffix) for suffix in SAFE_IMPORT_SUFFIXES):
            issues.append(ProviderIssueCode.UNSUPPORTED_FILE_TYPE)
            details.append("only CSV, CSV.GZ, and Parquet imports are accepted")
        if path.is_file():
            checksum = _file_checksum(path)
            if _contains_formula(path):
                issues.append(ProviderIssueCode.SPREADSHEET_FORMULA)
                details.append("spreadsheet formula-like values are blocked")
    except OSError as exc:
        issues.append(ProviderIssueCode.UNSAFE_PATH)
        details.append(str(exc))
    return ImportSafetyReport(not issues, str(path), checksum, tuple(issues), tuple(details))


def build_manifest(
    provider: str,
    dataset: str,
    rows: Iterable[Mapping[str, Any]],
    *,
    classification: DataClassification,
    schema_version: str = "1.0.0",
    dataset_version: str = "fixture-1",
) -> DatasetManifest:
    materialized = tuple(dict(row) for row in rows)
    fields = tuple(sorted({field for row in materialized for field in row}))
    source_checksum = _stable_checksum(materialized)
    return DatasetManifest(
        f"{provider}-{dataset}-{source_checksum[:12]}",
        provider,
        dataset,
        schema_version,
        dataset_version,
        classification,
        source_checksum,
        datetime.now(UTC),
        len(materialized),
        fields,
        "synthetic/offline"
        if classification is DataClassification.SYNTHETIC
        else "review-required",
        "delete_after_certification"
        if classification in {DataClassification.LICENSED, DataClassification.RESTRICTED}
        else "keep_with_repository",
        export_decision(classification, "json"),
        ("fixture coverage is not live provider validation",),
    )


def lineage_event(manifest: DatasetManifest, stage: str, output: Mapping[str, Any]) -> LineageEvent:
    output_checksum = _stable_checksum(output)
    return LineageEvent(
        hashlib.sha256(f"{manifest.dataset_id}:{stage}:{output_checksum}".encode()).hexdigest(),
        manifest.dataset_id,
        manifest.provider,
        stage,
        manifest.source_checksum,
        output_checksum,
        datetime.now(UTC),
        manifest.classification,
    )


def normalize_option_record(
    provider: str,
    raw: Mapping[str, Any],
    *,
    source_checksum: str | None = None,
) -> NormalizedOptionRecord:
    del provider
    identifier = str(raw.get("option_identifier") or raw.get("occ_symbol") or "").upper()
    match = OCC_PATTERN.match(identifier)
    if not match:
        raise ValueError(ProviderIssueCode.MALFORMED_IDENTIFIER.value)
    timestamp = _timestamp(str(raw.get("timestamp") or raw.get("quote_timestamp") or ""))
    return NormalizedOptionRecord(
        str(raw.get("underlying") or match.group("root")).upper(),
        str(raw.get("option_root") or match.group("root")).upper(),
        identifier,
        str(raw.get("expiration") or _occ_expiration(match.group("date"))),
        float(raw.get("strike") or int(match.group("strike")) / 1000),
        str(raw.get("option_type") or match.group("type")).upper(),
        _float_or_none(raw.get("bid")),
        _float_or_none(raw.get("ask")),
        _float_or_none(raw.get("last")),
        _int_or_none(raw.get("volume")),
        _int_or_none(raw.get("open_interest")),
        timestamp,
        _float_or_none(raw.get("multiplier")),
        _str_or_none(raw.get("exercise_style")),
        _str_or_none(raw.get("settlement_style")),
        _str_or_none(raw.get("exchange")),
        str(raw.get("adjusted_contract", "false")).lower() == "true",
        dict(raw),
        source_checksum or _stable_checksum(raw),
    )


def validate_options(records: Iterable[NormalizedOptionRecord]) -> ValidationSummary:
    accepted = 0
    issues: list[ValidationIssue] = []
    seen_contracts: set[str] = set()
    seen_timestamps: set[tuple[str, str]] = set()
    materialized = tuple(records)
    for record in materialized:
        record_issues = _record_issues(record, seen_contracts, seen_timestamps)
        if record_issues:
            issues.extend(record_issues)
        else:
            accepted += 1
    return ValidationSummary(
        len(materialized),
        accepted,
        len(materialized) - accepted,
        tuple(issues),
        _stable_checksum(tuple(asdict(row) for row in materialized)),
    )


def certify_dataset(
    provider: str,
    manifest: DatasetManifest,
    summary: ValidationSummary,
    *,
    live_validated: bool = False,
) -> CertificationReport:
    total = max(summary.records_seen, 1)
    metrics = {
        "contract_completeness": summary.records_accepted / total,
        "quote_completeness": summary.records_accepted / total,
        "quarantine_rate": summary.records_quarantined / total,
        "crossed_market_rate": _issue_rate(summary, ProviderIssueCode.CROSSED_MARKET),
        "multiplier_coverage": 1.0 - _issue_rate(summary, ProviderIssueCode.MISSING_MULTIPLIER),
    }
    warnings = ["fixture coverage is not licensed live validation"]
    if manifest.classification is not DataClassification.SYNTHETIC:
        warnings.append("licence review required before public release claims")
    level = CertificationLevel.REJECTED
    if metrics["quarantine_rate"] == 0:
        level = (
            CertificationLevel.LIVE_VALIDATED if live_validated else CertificationLevel.FIXTURE_ONLY
        )
    elif metrics["quarantine_rate"] <= 0.05:
        level = CertificationLevel.IMPORT_CERTIFIED
    checksum = _stable_checksum({"metrics": metrics, "manifest": manifest.checksum})
    return CertificationReport(
        provider, manifest.dataset_id, level, metrics, (), tuple(warnings), checksum
    )


def compare_provider_records(
    grouped_records: Mapping[str, Iterable[NormalizedOptionRecord]],
) -> ProviderComparisonReport:
    providers = tuple(sorted(grouped_records))
    identities: dict[str, dict[str, NormalizedOptionRecord]] = {}
    for provider, records in sorted(grouped_records.items()):
        for record in records:
            identities.setdefault(record.option_identifier, {})[provider] = record
    matched = sum(1 for values in identities.values() if set(values) == set(providers))
    unmatched = {
        provider: tuple(
            sorted(
                identifier for identifier, values in identities.items() if provider not in values
            )
        )
        for provider in providers
    }
    divergences: list[ValidationIssue] = []
    for identifier, values in sorted(identities.items()):
        bids = {provider: record.bid for provider, record in values.items()}
        if len(set(bids.values())) > 1:
            divergences.append(
                ValidationIssue(
                    ProviderIssueCode.SCHEMA_MISMATCH,
                    f"bid divergence: {json.dumps(bids, sort_keys=True)}",
                    identifier,
                )
            )
    checksum = _stable_checksum(
        {
            "providers": providers,
            "matched": matched,
            "unmatched": unmatched,
            "divergences": tuple(asdict(item) for item in divergences),
        }
    )
    return ProviderComparisonReport(
        providers,
        matched,
        unmatched,
        tuple(divergences),
        "moderate" if divergences else "informational",
        ("synthetic comparison; does not validate licensed coverage",),
        checksum,
    )


def readiness_report(
    provider: str,
    *,
    configuration_valid: bool,
    credentials: CredentialStatusReport,
    certification: CertificationReport | None,
    export_enforced: bool,
    gui_available: bool,
    live_validated: bool,
) -> ProviderReadinessReport:
    sections = {
        "configuration": ReadinessStatus.READY if configuration_valid else ReadinessStatus.BLOCKED,
        "credentials": ReadinessStatus.READY
        if credentials.configured
        else ReadinessStatus.INCOMPLETE,
        "certification": ReadinessStatus.READY_WITH_WARNINGS
        if certification and certification.level is not CertificationLevel.REJECTED
        else ReadinessStatus.INCOMPLETE,
        "licensing": ReadinessStatus.READY if export_enforced else ReadinessStatus.BLOCKED,
        "gui": ReadinessStatus.READY_WITH_WARNINGS if gui_available else ReadinessStatus.INCOMPLETE,
        "live_validation": ReadinessStatus.READY if live_validated else ReadinessStatus.UNVALIDATED,
    }
    blockers = tuple(name for name, status in sections.items() if status is ReadinessStatus.BLOCKED)
    warnings = tuple(
        name
        for name, status in sections.items()
        if status in {ReadinessStatus.INCOMPLETE, ReadinessStatus.UNVALIDATED}
    )
    status = (
        ReadinessStatus.BLOCKED
        if blockers
        else ReadinessStatus.UNVALIDATED
        if warnings
        else ReadinessStatus.READY
    )
    return ProviderReadinessReport(
        provider,
        status,
        sections,
        blockers,
        warnings,
        ("standard tests are offline and credential-free",),
    )


def performance_measurements(
    sample_size: int, started: datetime, finished: datetime
) -> dict[str, Any]:
    elapsed = max((finished - started).total_seconds(), 0.000001)
    return {
        "sample_size": sample_size,
        "duration_seconds": round(elapsed, 6),
        "records_per_second": round(sample_size / elapsed, 6),
        "hardware": "local development machine",
        "scope": "targeted Sprint 12C synthetic provider validation",
    }


def _record_issues(
    record: NormalizedOptionRecord,
    seen_contracts: set[str],
    seen_timestamps: set[tuple[str, str]],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    identifier = record.option_identifier
    if record.strike <= 0:
        issues.append(
            ValidationIssue(ProviderIssueCode.INVALID_STRIKE, "strike must be positive", identifier)
        )
    if record.option_type not in {"C", "P"}:
        issues.append(
            ValidationIssue(
                ProviderIssueCode.INVALID_OPTION_TYPE, "option type must be C or P", identifier
            )
        )
    if (record.bid is not None and record.bid < 0) or (record.ask is not None and record.ask < 0):
        issues.append(
            ValidationIssue(
                ProviderIssueCode.NEGATIVE_PRICE, "prices must be non-negative", identifier
            )
        )
    if record.bid is not None and record.ask is not None and record.bid > record.ask:
        issues.append(
            ValidationIssue(ProviderIssueCode.CROSSED_MARKET, "bid exceeds ask", identifier)
        )
    if record.multiplier is None:
        issues.append(
            ValidationIssue(
                ProviderIssueCode.MISSING_MULTIPLIER, "multiplier is required", identifier
            )
        )
    if record.settlement_style and record.settlement_style not in {"physical", "cash"}:
        issues.append(
            ValidationIssue(
                ProviderIssueCode.UNSUPPORTED_SETTLEMENT_STYLE, record.settlement_style, identifier
            )
        )
    if record.adjusted_contract and not record.raw_record.get("deliverable"):
        issues.append(
            ValidationIssue(
                ProviderIssueCode.AMBIGUOUS_ADJUSTED_CONTRACT, "missing deliverable", identifier
            )
        )
    if not record.underlying:
        issues.append(
            ValidationIssue(
                ProviderIssueCode.UNRESOLVED_UNDERLYING, "underlying missing", identifier
            )
        )
    if identifier in seen_contracts:
        issues.append(
            ValidationIssue(ProviderIssueCode.DUPLICATE_CONTRACT, "duplicate contract", identifier)
        )
    seen_contracts.add(identifier)
    timestamp_key = (identifier, record.timestamp)
    if timestamp_key in seen_timestamps:
        issues.append(
            ValidationIssue(
                ProviderIssueCode.DUPLICATE_TIMESTAMP, "duplicate timestamp", identifier
            )
        )
    seen_timestamps.add(timestamp_key)
    if record.open_interest is not None and record.open_interest < 0:
        issues.append(
            ValidationIssue(
                ProviderIssueCode.INCONSISTENT_OPEN_INTEREST,
                "open interest is negative",
                identifier,
            )
        )
    return tuple(issues)


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def _occ_expiration(value: str) -> str:
    year = int(value[:2]) + 2000
    return f"{year:04d}-{value[2:4]}-{value[4:6]}"


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _str_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _issue_rate(summary: ValidationSummary, code: ProviderIssueCode) -> float:
    return sum(issue.code is code for issue in summary.issues) / max(summary.records_seen, 1)


def _contains_formula(path: Path) -> bool:
    if not path.name.lower().endswith(".csv"):
        return False
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.reader(handle):
                if any(cell.startswith(("=", "+", "-", "@")) for cell in row):
                    return True
    except UnicodeError:
        return True
    return False


def _file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_checksum(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
