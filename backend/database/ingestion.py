"""Batch ingestion services with explicit upsert and rollback semantics."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Sequence
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from math import ceil
from typing import Any, cast

from sqlalchemy.orm import Session

from backend.database.dtos import (
    CorporateActionDTO,
    DataLineageRecordDTO,
    DatasetManifestDTO,
    DividendDTO,
    EarningsEventDTO,
    InterestRateCurveDTO,
    OptionContractDTO,
    OptionQuoteDTO,
    UnderlyingPriceDTO,
)
from backend.database.exceptions import DatabaseTransactionError
from backend.database.repositories import (
    ContractsRepository,
    CorporateActionsRepository,
    DividendsRepository,
    EarningsRepository,
    InterestRatesRepository,
    ManifestsLineageRepository,
    QuotesRepository,
    UnderlyingPricesRepository,
)
from backend.database.session import DatabaseSessionManager
from backend.database.validation import RecordValidator, ValidationIssue


class UpsertPolicy(StrEnum):
    UPSERT = "upsert"
    INSERT_ONLY = "insert-only"


@dataclass(slots=True, frozen=True)
class IngestionConfig:
    batch_size: int = 500
    contract_policy: UpsertPolicy = UpsertPolicy.UPSERT
    quote_policy: UpsertPolicy = UpsertPolicy.UPSERT
    manifest_policy: UpsertPolicy = UpsertPolicy.UPSERT


@dataclass(slots=True)
class ImportResult:
    entity_name: str
    requested: int = 0
    processed: int = 0
    inserted_or_updated: int = 0
    duplicates_dropped: int = 0
    failed: int = 0
    validation_issues: list[ValidationIssue] = field(default_factory=list)


class BulkIngestionService:
    """Ingest DTO batches with transaction safety and deterministic duplicate handling."""

    def __init__(
        self,
        session_manager: DatabaseSessionManager,
        config: IngestionConfig | None = None,
        validator: RecordValidator | None = None,
    ) -> None:
        self.session_manager = session_manager
        self.config = config or IngestionConfig()
        self.validator = validator or RecordValidator()

    def ingest_contracts(self, contracts: Sequence[OptionContractDTO]) -> ImportResult:
        result = ImportResult(entity_name="option_contracts", requested=len(contracts))
        deduped = self._dedupe_by_key(
            contracts,
            lambda item: (item.provider_id, item.provider_contract_id),
        )
        result.duplicates_dropped = len(contracts) - len(deduped)

        if result.duplicates_dropped:
            result.validation_issues.append(
                ValidationIssue(
                    code="duplicate_provider_contract_identifier",
                    message="Duplicate provider contract identifiers were deduplicated",
                )
            )

        validation = self.validator.validate_contracts(deduped)
        result.validation_issues.extend(validation.issues)
        if not validation.valid:
            result.failed = len(deduped)
            return result

        with self.session_manager.session_scope() as session:
            repository = ContractsRepository(session)
            for batch in _chunk(deduped, self.config.batch_size):
                payload = [_to_mapping(dto) for dto in batch]
                if self.config.contract_policy == UpsertPolicy.INSERT_ONLY:
                    repository.batch_insert_only(payload)
                else:
                    repository.batch_upsert(payload)
                result.processed += len(batch)
                result.inserted_or_updated += len(batch)

        return result

    def ingest_manifests(self, manifests: Sequence[DatasetManifestDTO]) -> ImportResult:
        result = ImportResult(entity_name="dataset_manifests", requested=len(manifests))
        deduped = self._dedupe_by_key(
            manifests,
            lambda item: (item.provider_id, item.dataset_name, item.dataset_version),
        )
        result.duplicates_dropped = len(manifests) - len(deduped)

        if result.duplicates_dropped:
            result.validation_issues.append(
                ValidationIssue(
                    code="duplicate_manifest_identifier",
                    message="Duplicate manifest identifiers were deduplicated",
                )
            )

        validation = self.validator.validate_manifests(deduped)
        result.validation_issues.extend(validation.issues)
        if not validation.valid:
            result.failed = len(deduped)
            return result

        with self.session_manager.session_scope() as session:
            repository = ManifestsLineageRepository(session)
            for batch in _chunk(deduped, self.config.batch_size):
                payload = [_to_mapping(dto) for dto in batch]
                if self.config.manifest_policy == UpsertPolicy.INSERT_ONLY:
                    repository.batch_insert_only_manifests(payload)
                else:
                    repository.batch_upsert_manifests(payload)
                result.processed += len(batch)
                result.inserted_or_updated += len(batch)

        return result

    def ingest_quotes(self, quotes: Sequence[OptionQuoteDTO]) -> ImportResult:
        result = ImportResult(entity_name="option_quotes", requested=len(quotes))
        deduped = self._dedupe_by_key(
            quotes,
            lambda item: (
                item.contract_id,
                item.quote_timestamp,
                item.provider_id,
                item.manifest_id,
            ),
        )
        result.duplicates_dropped = len(quotes) - len(deduped)

        try:
            with self.session_manager.session_scope() as session:
                validation = self.validator.validate_quotes(session, deduped)
                result.validation_issues.extend(validation.issues)
                if not validation.valid:
                    result.failed = len(deduped)
                    return result

                repository = QuotesRepository(session)
                for batch in _chunk(deduped, self.config.batch_size):
                    payload = [_to_mapping(dto) for dto in batch]
                    if self.config.quote_policy == UpsertPolicy.INSERT_ONLY:
                        repository.batch_insert_only(payload)
                    else:
                        repository.batch_upsert(payload)
                    result.processed += len(batch)
                    result.inserted_or_updated += len(batch)
        except DatabaseTransactionError:
            result.failed = len(deduped)
            raise

        return result

    def ingest_underlying_prices(self, prices: Sequence[UnderlyingPriceDTO]) -> ImportResult:
        return self._generic_ingest(
            entity_name="underlying_prices",
            payload=prices,
            dedupe_key=lambda item: (
                item.underlying_id,
                item.price_timestamp,
                item.provider_id,
                item.manifest_id,
            ),
            write_fn=lambda session, batch: UnderlyingPricesRepository(session).batch_upsert(
                [_to_mapping(dto) for dto in batch]
            ),
        )

    def ingest_dividends(self, dividends: Sequence[DividendDTO]) -> ImportResult:
        return self._generic_ingest(
            entity_name="dividends",
            payload=dividends,
            dedupe_key=lambda item: (
                item.underlying_id,
                item.ex_date,
                item.provider_id,
                item.manifest_id,
            ),
            write_fn=lambda session, batch: DividendsRepository(session).batch_upsert(
                [_to_mapping(dto) for dto in batch]
            ),
        )

    def ingest_earnings(self, earnings: Sequence[EarningsEventDTO]) -> ImportResult:
        return self._generic_ingest(
            entity_name="earnings_events",
            payload=earnings,
            dedupe_key=lambda item: (
                item.underlying_id,
                item.event_date,
                item.provider_id,
                item.manifest_id,
            ),
            write_fn=lambda session, batch: EarningsRepository(session).batch_upsert(
                [_to_mapping(dto) for dto in batch]
            ),
        )

    def ingest_corporate_actions(self, actions: Sequence[CorporateActionDTO]) -> ImportResult:
        return self._generic_ingest(
            entity_name="corporate_actions",
            payload=actions,
            dedupe_key=lambda item: (
                item.underlying_id,
                item.action_date,
                item.action_type,
                item.provider_id,
                item.manifest_id,
            ),
            write_fn=lambda session, batch: CorporateActionsRepository(session).batch_upsert(
                [_to_mapping(dto) for dto in batch]
            ),
        )

    def ingest_interest_rate_curves(self, rates: Sequence[InterestRateCurveDTO]) -> ImportResult:
        return self._generic_ingest(
            entity_name="interest_rate_curves",
            payload=rates,
            dedupe_key=lambda item: (
                item.provider_id,
                item.manifest_id,
                item.as_of_date,
                item.tenor_days,
            ),
            write_fn=lambda session, batch: InterestRatesRepository(session).batch_upsert(
                [_to_mapping(dto) for dto in batch]
            ),
        )

    def ingest_lineage(self, lineage_records: Sequence[DataLineageRecordDTO]) -> ImportResult:
        result = ImportResult(entity_name="data_lineage_records", requested=len(lineage_records))
        with self.session_manager.session_scope() as session:
            repository = ManifestsLineageRepository(session)
            for record in lineage_records:
                check = self.validator.validate_lineage_manifest_match(
                    session=session,
                    provider_id=record.provider_id,
                    manifest_id=record.manifest_id,
                )
                if not check.valid:
                    result.validation_issues.extend(check.issues)
                    result.failed += 1
                    continue
                repository.insert_lineage([_to_mapping(record)])
                result.processed += 1
                result.inserted_or_updated += 1

        return result

    def _generic_ingest[T](
        self,
        *,
        entity_name: str,
        payload: Sequence[T],
        dedupe_key: Callable[[T], Hashable],
        write_fn: Callable[[Session, Sequence[T]], None],
    ) -> ImportResult:
        result = ImportResult(entity_name=entity_name, requested=len(payload))
        deduped = self._dedupe_by_key(payload, dedupe_key)
        result.duplicates_dropped = len(payload) - len(deduped)

        with self.session_manager.session_scope() as session:
            for batch in _chunk(deduped, self.config.batch_size):
                write_fn(session, batch)
                result.processed += len(batch)
                result.inserted_or_updated += len(batch)

        return result

    def _dedupe_by_key[T](
        self,
        values: Sequence[T],
        key_fn: Callable[[T], Hashable],
    ) -> list[T]:
        # Keep the last occurrence for deterministic duplicate resolution.
        index_by_key: dict[Hashable, T] = {}
        for item in values:
            index_by_key[key_fn(item)] = item
        return list(index_by_key.values())


def _chunk[T](values: Sequence[T], chunk_size: int) -> list[Sequence[T]]:
    if chunk_size <= 0:
        raise ValueError("batch_size must be positive")
    total_chunks = ceil(len(values) / chunk_size) if values else 0
    return [values[index * chunk_size : (index + 1) * chunk_size] for index in range(total_chunks)]


def _to_mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], asdict(cast(Any, value)))
