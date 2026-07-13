"""Validation engine for historical-market-data quality checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ValidationSeverity(StrEnum):
    """Severity levels used to classify validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationMode(StrEnum):
    """Validation execution modes."""

    FAIL_FAST = "fail-fast"
    COLLECT_ALL = "collect-all"


@dataclass(slots=True)
class ValidationIssue:
    """Represents a single validation failure."""

    code: str
    message: str
    record_id: str | None = None
    severity: ValidationSeverity = ValidationSeverity.ERROR


@dataclass(slots=True)
class ValidationSummary:
    """Aggregated counts for validation results."""

    total_records: int
    total_issues: int
    by_severity: dict[str, int] = field(default_factory=dict)
    by_code: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationPolicy:
    """Controls severity overrides and termination behavior."""

    mode: ValidationMode = ValidationMode.COLLECT_ALL
    fail_on_severities: set[ValidationSeverity] = field(
        default_factory=lambda: {ValidationSeverity.ERROR, ValidationSeverity.CRITICAL}
    )
    severity_overrides: dict[str, ValidationSeverity] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationReport:
    """Structured report containing all detected validation issues."""

    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    summary: ValidationSummary = field(default_factory=lambda: ValidationSummary(0, 0))
    mode: ValidationMode = ValidationMode.COLLECT_ALL


class ValidationEngine:
    """Apply a set of quality checks to a collection of records."""

    def validate_records(
        self,
        records: list[dict[str, Any]],
        policy: ValidationPolicy | None = None,
    ) -> ValidationReport:
        """Validate a collection of record dictionaries and return a report."""
        active_policy = policy or ValidationPolicy()
        issues: list[ValidationIssue] = []
        seen_ids: set[str] = set()

        def add_issue(code: str, message: str, record_id: str | None = None) -> bool:
            severity = active_policy.severity_overrides.get(code, ValidationSeverity.ERROR)
            issues.append(
                ValidationIssue(
                    code=code,
                    message=message,
                    record_id=record_id,
                    severity=severity,
                )
            )
            return (
                active_policy.mode == ValidationMode.FAIL_FAST
                and severity in active_policy.fail_on_severities
            )

        for record in records:
            record_id = str(record.get("id", ""))
            if record_id in seen_ids:
                if add_issue("duplicate_record", "Duplicate record detected", record_id):
                    break
            else:
                seen_ids.add(record_id)

            chain = record.get("option_chain")
            if not chain:
                if add_issue("missing_option_chain", "Option chain is missing", record_id):
                    break
            else:
                for item in chain:
                    strike = item.get("strike")
                    if isinstance(strike, (int, float)) and strike <= 0:
                        if add_issue("invalid_strike", "Strike must be positive", record_id):
                            break
                    expiration = item.get("expiration")
                    if not isinstance(expiration, str) or not expiration:
                        if add_issue("invalid_expiration", "Expiration is missing", record_id):
                            break

                if (
                    active_policy.mode == ValidationMode.FAIL_FAST
                    and issues
                    and issues[-1].severity in active_policy.fail_on_severities
                ):
                    break

            timestamp = record.get("timestamp")
            if not isinstance(timestamp, str):
                if add_issue("malformed_timestamp", "Timestamp must be a string", record_id):
                    break
            else:
                try:
                    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    if add_issue("malformed_timestamp", "Timestamp is not parsable", record_id):
                        break

            iv = record.get("implied_volatility")
            if isinstance(iv, (int, float)) and not 0 <= iv <= 1:
                if add_issue(
                    "invalid_implied_volatility",
                    "Implied volatility is outside the expected range",
                    record_id,
                ):
                    break

            for greek_name in ("delta", "gamma", "theta", "vega", "rho"):
                value = record.get(greek_name)
                if isinstance(value, (int, float)) and not (
                    -1 <= value <= 1 or greek_name == "theta"
                ):
                    if add_issue(
                        "invalid_greeks",
                        f"{greek_name} is outside the expected range",
                        record_id,
                    ):
                        break

            if (
                active_policy.mode == ValidationMode.FAIL_FAST
                and issues
                and issues[-1].severity in active_policy.fail_on_severities
            ):
                break

            underlying_price = record.get("underlying_price")
            if isinstance(underlying_price, (int, float)) and underlying_price <= 0:
                if add_issue(
                    "missing_underlying_price",
                    "Underlying price must be positive",
                    record_id,
                ):
                    break

        return ValidationReport(
            valid=not any(issue.severity in active_policy.fail_on_severities for issue in issues),
            issues=issues,
            summary=self._build_summary(records=records, issues=issues),
            mode=active_policy.mode,
        )

    def _build_summary(
        self,
        *,
        records: list[dict[str, Any]],
        issues: list[ValidationIssue],
    ) -> ValidationSummary:
        by_code: dict[str, int] = {}
        by_severity: dict[str, int] = {}

        for issue in issues:
            by_code[issue.code] = by_code.get(issue.code, 0) + 1
            severity_name = issue.severity.value
            by_severity[severity_name] = by_severity.get(severity_name, 0) + 1

        return ValidationSummary(
            total_records=len(records),
            total_issues=len(issues),
            by_severity=by_severity,
            by_code=by_code,
        )
