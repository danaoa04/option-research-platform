"""Validation engine for historical-market-data quality checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ValidationIssue:
    """Represents a single validation failure."""

    code: str
    message: str
    record_id: str | None = None


@dataclass(slots=True)
class ValidationReport:
    """Structured report containing all detected validation issues."""

    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)


class ValidationEngine:
    """Apply a set of quality checks to a collection of records."""

    def validate_records(self, records: list[dict[str, Any]]) -> ValidationReport:
        """Validate a collection of record dictionaries and return a report."""
        issues: list[ValidationIssue] = []
        seen_ids: set[str] = set()

        for record in records:
            record_id = str(record.get("id", ""))
            if record_id in seen_ids:
                issues.append(
                    ValidationIssue(
                        code="duplicate_record",
                        message="Duplicate record detected",
                        record_id=record_id,
                    )
                )
            else:
                seen_ids.add(record_id)

            chain = record.get("option_chain")
            if not chain:
                issues.append(
                    ValidationIssue(
                        code="missing_option_chain",
                        message="Option chain is missing",
                        record_id=record_id,
                    )
                )
            else:
                for item in chain:
                    strike = item.get("strike")
                    if isinstance(strike, (int, float)) and strike <= 0:
                        issues.append(
                            ValidationIssue(
                                code="invalid_strike",
                                message="Strike must be positive",
                                record_id=record_id,
                            )
                        )
                    expiration = item.get("expiration")
                    if not isinstance(expiration, str) or not expiration:
                        issues.append(
                            ValidationIssue(
                                code="invalid_expiration",
                                message="Expiration is missing",
                                record_id=record_id,
                            )
                        )

            timestamp = record.get("timestamp")
            if not isinstance(timestamp, str):
                issues.append(
                    ValidationIssue(
                        code="malformed_timestamp",
                        message="Timestamp must be a string",
                        record_id=record_id,
                    )
                )
            else:
                try:
                    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    issues.append(
                        ValidationIssue(
                            code="malformed_timestamp",
                            message="Timestamp is not parsable",
                            record_id=record_id,
                        )
                    )

            iv = record.get("implied_volatility")
            if isinstance(iv, (int, float)) and not 0 <= iv <= 1:
                issues.append(
                    ValidationIssue(
                        code="invalid_implied_volatility",
                        message="Implied volatility is outside the expected range",
                        record_id=record_id,
                    )
                )

            for greek_name in ("delta", "gamma", "theta", "vega", "rho"):
                value = record.get(greek_name)
                if isinstance(value, (int, float)) and not (
                    -1 <= value <= 1 or greek_name == "theta"
                ):
                    issues.append(
                        ValidationIssue(
                            code="invalid_greeks",
                            message=f"{greek_name} is outside the expected range",
                            record_id=record_id,
                        )
                    )

            underlying_price = record.get("underlying_price")
            if isinstance(underlying_price, (int, float)) and underlying_price <= 0:
                issues.append(
                    ValidationIssue(
                        code="missing_underlying_price",
                        message="Underlying price must be positive",
                        record_id=record_id,
                    )
                )

        return ValidationReport(valid=not issues, issues=issues)
