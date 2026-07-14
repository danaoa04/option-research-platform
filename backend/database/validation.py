"""Validation rules for records before persistence."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from backend.database.dtos import DatasetManifestDTO, OptionContractDTO, OptionQuoteDTO
from backend.database.models import DatasetManifest, OptionContract


@dataclass(slots=True, frozen=True)
class ValidationIssue:
    code: str
    message: str


@dataclass(slots=True)
class ValidationSummary:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)


class RecordValidator:
    """Validate ingestion DTOs before repository writes."""

    def validate_contracts(self, contracts: Iterable[OptionContractDTO]) -> ValidationSummary:
        issues: list[ValidationIssue] = []
        seen_keys: set[tuple[int, str]] = set()
        for contract in contracts:
            key = (contract.provider_id, contract.provider_contract_id)
            if key in seen_keys:
                issues.append(
                    ValidationIssue(
                        code="duplicate_provider_contract_identifier",
                        message="Duplicate provider contract identifier detected in payload",
                    )
                )
            seen_keys.add(key)

            if contract.strike <= 0:
                issues.append(
                    ValidationIssue(
                        code="invalid_strike",
                        message="Contract strike must be greater than zero",
                    )
                )
            if contract.first_seen_at > contract.last_seen_at:
                issues.append(
                    ValidationIssue(
                        code="invalid_timestamp_order",
                        message="first_seen_at must be less than or equal to last_seen_at",
                    )
                )

        return ValidationSummary(valid=not issues, issues=issues)

    def validate_quotes(
        self,
        session: Session,
        quotes: Iterable[OptionQuoteDTO],
    ) -> ValidationSummary:
        issues: list[ValidationIssue] = []
        for quote in quotes:
            if quote.bid is not None and quote.ask is not None and quote.bid > quote.ask:
                issues.append(
                    ValidationIssue(
                        code="crossed_market",
                        message="Quote bid must not exceed ask",
                    )
                )
            if quote.quote_timestamp.tzinfo is None:
                issues.append(
                    ValidationIssue(
                        code="invalid_timestamp",
                        message="Quote timestamp must be timezone-aware",
                    )
                )

            contract = session.get(OptionContract, quote.contract_id)
            if contract is None:
                issues.append(
                    ValidationIssue(
                        code="quote_contract_mismatch",
                        message="Quote references unknown contract",
                    )
                )
            elif contract.provider_id != quote.provider_id:
                issues.append(
                    ValidationIssue(
                        code="quote_contract_mismatch",
                        message="Quote provider does not match contract provider",
                    )
                )

            manifest = session.get(DatasetManifest, quote.manifest_id)
            if manifest is None or manifest.provider_id != quote.provider_id:
                issues.append(
                    ValidationIssue(
                        code="dataset_manifest_mismatch",
                        message="Quote provider does not match dataset manifest provider",
                    )
                )

        return ValidationSummary(valid=not issues, issues=issues)

    def validate_manifests(self, manifests: Iterable[DatasetManifestDTO]) -> ValidationSummary:
        issues: list[ValidationIssue] = []
        seen: set[tuple[int, str, str]] = set()

        for manifest in manifests:
            key = (manifest.provider_id, manifest.dataset_name, manifest.dataset_version)
            if key in seen:
                issues.append(
                    ValidationIssue(
                        code="duplicate_manifest_identifier",
                        message="Duplicate manifest identifier detected in payload",
                    )
                )
            seen.add(key)

            if manifest.created_timestamp.tzinfo is None:
                issues.append(
                    ValidationIssue(
                        code="invalid_timestamp",
                        message="Manifest created_timestamp must be timezone-aware",
                    )
                )
            if manifest.row_count < 0:
                issues.append(
                    ValidationIssue(
                        code="invalid_row_count",
                        message="Manifest row_count must be non-negative",
                    )
                )

        return ValidationSummary(valid=not issues, issues=issues)

    def validate_lineage_manifest_match(
        self,
        session: Session,
        provider_id: int,
        manifest_id: int,
    ) -> ValidationSummary:
        manifest = session.get(DatasetManifest, manifest_id)
        if manifest is None or manifest.provider_id != provider_id:
            return ValidationSummary(
                valid=False,
                issues=[
                    ValidationIssue(
                        code="dataset_manifest_mismatch",
                        message="Lineage provider does not match dataset manifest provider",
                    )
                ],
            )
        return ValidationSummary(valid=True)


def is_nearest_prior(candidate_ts: datetime, as_of_ts: datetime) -> bool:
    """Helper for tests: nearest-prior candidate must never be from the future."""
    return candidate_ts <= as_of_ts
